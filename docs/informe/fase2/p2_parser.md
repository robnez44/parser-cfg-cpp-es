# Implementación del parser

Sección del informe a cargo de P2. Cubre O1 y la actividad A2: el lexer, el parser y los árboles del subconjunto del español.

## 1. Cómo está armado

El análisis tiene dos etapas, las mismas dos primeras de la Fase 1. El lexer (`spanish/lexer.py`) convierte la oración en una lista de tokens y el parser (`spanish/parser.py`) arma el árbol con esos tokens. `spanish.analyze(sentence)` une las dos: devuelve la raíz del árbol o lanza el primer error que encuentre. No hay tercera etapa, porque la concordancia la revisa la gramática (sección de P1). Si el parser acepta una oración, esa oración ya concuerda.

De la Fase 1 reutilizamos sin cambios `Token`, `Node`, `LexicalError`, `SyntacticError` y el módulo que dibuja los árboles (`minicpp/visualization.py`). Por eso los mensajes de error y los dibujos se ven igual en las dos fases.

## 2. El lexer

En C++ los tokens se reconocían por su forma, con expresiones regulares. En español eso no sirve: `come` es verbo y `casa` es sustantivo, y no hay un patrón de letras que los separe. Por eso el lexer trabaja en dos pasos. Primero corta la oración en palabras con la expresión `[^\s.]+|\.` (cualquier cosa que no sea espacio ni punto, o un punto suelto). Después busca cada palabra en `spanish/lexicon.tsv`, que tiene las 98 palabras del vocabulario y el punto, cada una con su tipo de token, UPOS, lema, género, número y tiempo.

Antes de buscar, la oración se pasa a minúsculas y a la forma Unicode NFC. Esto último hace falta porque una letra con tilde se puede guardar de dos maneras (`ñ` como un solo carácter, o `n` seguida de la tilde) y en pantalla las dos se ven iguales. Sin normalizar, un `niño` copiado de otro lado podía salir como palabra desconocida.

Si una palabra no está en el lexicón, el lexer lanza un error léxico con la columna donde empieza la palabra:

```
Error léxico en línea 1, columna 10: palabra fuera del vocabulario 'que'
```

La línea siempre es 1 porque se analiza una oración a la vez. Al final de la lista se agrega un token `EOF`, igual que en la Fase 1.

## 3. El parser

Es un parser descendente recursivo sin retroceso. Tiene un método por cada uno de los 22 no terminales de `es.gram`, con el mismo nombre en snake_case (`NpMS` es `np_ms`, `AdjListFP` es `adj_list_fp`) y la producción en la primera línea del docstring. Cada método mira el token actual y con eso elige la producción. Los auxiliares `current`, `check`, `consume`, `consume_one_of`, `epsilon` y `error` son los mismos del parser de C++.

La concordancia sale de la forma de la gramática. En `clause`, el determinante del sujeto decide el camino: si es singular (`el`, `la`, `un`, `una`) se llama a `np_sing` y después a `vp_sing`, que exige `VERB_S`; si es plural, se va por `np_plur` y `vp_plur`. Con el género pasa lo mismo, porque después de `DET_MS` el método `np_ms` solo acepta `NOUN_MS` y adjetivos `ADJ_MS`. En `los niño come`, entonces, el parser falla en la segunda palabra:

```
Error sintáctico en línea 1, columna 5: se esperaba NOUN_MP y se encontró NOUN_MS ('niño')
```

El único método que no puede decidir con certeza es `np_tail`. Cuando ve `PREP`, la frase preposicional podría ser del sustantivo o del verbo (el conflicto `M[NpTail, PREP]` que explica P1). El método toma siempre `PrepPhrase NpTail`, de modo que la frase se pega al sustantivo más cercano. Es la misma salida que usamos con el else colgante en `else_part`, y el docstring de `np_tail` lo explica.

Después de `Sentence` solo puede quedar `EOF`. Si sobran palabras, el mensaje depende del punto: si la oración no tenía punto, ahí todavía cabía un `PERIOD`, así que el error dice `se esperaba uno de: PERIOD, EOF`; si ya lo tenía, solo pide `EOF`.

Como nunca retrocede, el parser mira cada token una sola vez y el tiempo crece en línea con el largo de la oración. En nuestra prueba, las 60 oraciones del set se analizaron en menos de un milisegundo en total.

## 4. Árboles y línea de comandos

El árbol que devuelve el parser es la derivación completa, con una hoja ε en cada regla que no consumió nada. Para verlo usamos la línea de comandos:

```
uv run python -m spanish "el niño come una manzana roja" --tree --view outline --compact
```

```
Sentence
└── Clause
    ├── NpSing
    │   └── NpMS
    │       ├── DET_MS 'el'
    │       └── NOUN_MS 'niño'
    └── VpSing
        ├── VERB_S 'come'
        └── VpTail
            └── Object
                └── NounPhrase
                    └── NpSing
                        └── NpFS
                            ├── DET_FS 'una'
                            ├── NOUN_FS 'manzana'
                            └── AdjListFS
                                └── ADJ_FS 'roja'
```

Las opciones son las de la Fase 1. `--tokens` muestra la tabla de tokens con su UPOS, `--tree` dibuja el árbol y `--view` elige dónde: en la terminal, en una ventana de NLTK o un nodo por línea, como arriba. `--compact` esconde las ramas ε, pero solo en el dibujo. El comando imprime `Oración válida` o el error y termina con código 0 o 1. Nada de esto usa internet, que es lo que necesitamos para la demo.

## 5. Resultados sobre el set de prueba

`experiments/run_parser.py` corre `analyze()` sobre las 60 oraciones de `data/test_set.jsonl` y escribe `results/parser.jsonl` con el formato de la sección 8 del contrato. De cada oración aceptada guarda las UPOS (tomadas del lexicón), el árbol y a qué se pegó la frase preposicional; de cada rechazada, el mensaje de error.

| Nivel | Aceptadas | Errores léxicos | Errores sintácticos |
|---|---|---|---|
| 1 | 20 | 0 | 0 |
| 2 | 13 | 0 | 7 |
| 3 | 0 | 13 | 7 |
| Total | 33 | 13 | 14 |

Las 60 respuestas coinciden con la etiqueta `in_grammar` del set. Las 16 oraciones que no son español correcto se rechazaron todas; las 7 de nivel 2 son errores de concordancia y el parser marca la palabra exacta donde se rompe. Las otras 11 rechazadas sí son español correcto, pero usan cosas que dejamos fuera de la gramática, como `que`, `y`, un clítico (`el niño la come`) o el adverbio antes del verbo. En las 33 aceptadas, las UPOS coinciden palabra por palabra con las esperadas.

Dos de estos resultados salen del diseño del parser. El lexer revisa toda la oración antes de que empiece el parser, así que una palabra desconocida produce un error léxico aunque haya un error de concordancia antes: `el niña que corre duerme` y `los niño y la niña comen` salen como errores léxicos por `que` y por `y`. Lo otro es la ambigüedad. En las 6 oraciones ambiguas el parser pega la frase al sustantivo, y el set espera el verbo en 3 de ellas. Eso viene directo de la decisión de `np_tail` y es justo lo que la Tarea C compara con spaCy, HuggingFace y el LLM.

## 6. Cómo comprobamos que funciona

Las pruebas de esta parte son 293, en cuatro archivos: `test_es_lexer.py` (153), `test_es_parser.py` (109), `test_es_cli.py` (14) y `test_run_parser.py` (17). Revisan que el lexicón cuadre con `es.gram` (sus tipos de token son exactamente los 17 terminales), que haya un método por no terminal con su producción en el docstring, que cada árbol use solo producciones de la gramática y que cada error tenga la columna y el mensaje correctos. Junto con el resto del proyecto, el repositorio pasa 1117 pruebas.

Que las pruebas pasen no dice si cubren lo suficiente, por eso hicimos dos comprobaciones más.

La primera fue comparar el parser con `nltk.ChartParser`, que lee `es.gram` como una CFG cualquiera y no sabe nada de LL(1). Probamos todas las secuencias de 1 a 4 tokens que se pueden formar con los 17 terminales (88 740) y 1845 oraciones de la gramática con un token cambiado al azar. En ninguna dieron respuestas distintas. Las 3000 oraciones generadas al azar desde la gramática, sin cambios, fueron aceptadas.

La segunda fue meter errores a propósito en el código y ver si alguna prueba fallaba. Dos pasaron sin que nada lo notara: que `analyze()` no revisara si sobraban palabras después de la oración, y que `run_parser.py` guardara el árbol compacto en lugar del completo. Agregamos una prueba para cada caso.

## 7. Limitaciones

- Solo se reporta el primer error. Si una oración tiene dos, el segundo no aparece.
- Un error léxico tapa cualquier error sintáctico, porque el lexer termina antes de que empiece el parser.
- La frase preposicional siempre se pega al sustantivo. La gramática permite la otra lectura, pero el parser nunca la prueba.
- El vocabulario es cerrado. Una palabra nueva es una fila más en el lexicón, pero una construcción nueva (`que`, `y`) obliga a cambiar `es.gram`, y si la regla toca el sintagma nominal hay que escribirla una vez por cada combinación de género y número (P1 mide ese crecimiento en su sección 3).

## 8. Cómo se reproduce

```
uv run python -m spanish "el maestro lee la carta en la casa" --tree
uv run python -m spanish "los niño come" --tokens
uv run python -m experiments.run_parser
uv run pytest tests/test_es_lexer.py tests/test_es_parser.py tests/test_es_cli.py tests/test_run_parser.py
```

## Referencias

- Aho, A., Lam, M., Sethi, R. y Ullman, J. *Compiladores: principios, técnicas y herramientas*. Sección 4.4 (análisis sintáctico descendente recursivo y gramáticas LL(1)).
- Unicode Standard Annex #15. *Unicode Normalization Forms* (forma NFC).
