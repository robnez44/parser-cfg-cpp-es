# Contrato del proyecto TLP02-2026, Fase 2

Este documento fija las decisiones y las interfaces entre las partes de la Fase 2. Si alguien necesita cambiar algo de aquí, lo habla con el dueño de esa sección y avisa al grupo antes de tocar código. El contrato de la Fase 1 (`CONTRATO.md`) queda como estaba: esa fase ya se entregó.

## 0. Punto de partida

La Fase 2 es el parser para un subconjunto del español y su comparación con herramientas de NLP y con un LLM. Vale 70% del proyecto y se entrega con informe, código y presentación.

De la Fase 1 reutilizamos `Token`, `Node`, `LexicalError`, `SyntacticError`, la visualización con NLTK, el verificador LL(1) y la forma de escribir el parser: un método por no terminal, sin backtracking.

No hacemos analizador semántico. El enunciado lo recomienda para la concordancia, pero no lo exige; la concordancia va dentro de la gramática (sección 5).

La gramática (sección 5), el lexicón (sección 4) y los formatos (secciones 7 a 11) ya están definidos. Con eso los cinco pueden empezar a la vez.

## 1. Referencias del PDF

| Código | Objetivo |
|---|---|
| O1 | Parser propio para un subconjunto del español, con árboles visuales |
| O2 | Evaluar cuantitativamente el parser frente a herramientas de NLP |
| O3 | Medir si un LLM sigue reglas gramaticales formales cuando se le dan en el prompt |
| O4 | Hallazgos respaldados con datos, no con impresiones |

| Código | Actividad |
|---|---|
| A1 | Definir la CFG del español: SVO, modificadores, dos tiempos verbales, concordancia y vocabulario |
| A2 | Implementar el parser y la visualización de los árboles |
| A3 | Set de prueba de al menos 60 oraciones en tres niveles, con la salida esperada |
| A4 | Procesar el set con dos herramientas de NLP |
| A5 | Métricas: precisión, recall, tasa de rechazo correcto y clasificación de errores, en tablas y gráficas |
| A6 | Experimento con el LLM: si respeta las reglas, en qué acierta y falla, y zero-shot frente a few-shot |
| A7 | Analizar robustez, ambigüedad, escalabilidad, costo computacional y aplicabilidad de cada enfoque |

| Código | Entregable |
|---|---|
| E1 | Informe de 7 a 10 páginas |
| E2 | Código del parser, la visualización, el set de prueba, el script de comparación y los prompts con sus logs, en el repositorio, con un README que explique cómo reproducir los experimentos |
| E3 | Presentación de 15 a 20 minutos con demo en vivo del parser y las tablas comparativas. Asiste al menos la mitad más uno del grupo |

## 2. Decisiones

| # | Tema | Decisión |
|---|---|---|
| 1 | Tipo de parser | Descendente recursivo sin backtracking sobre una gramática LL(1), igual que en la Fase 1. "LL(1)" es la propiedad de la gramática; "descendente recursivo" es cómo se implementa: un método por no terminal |
| 2 | Ambigüedad | La gramática del parser tiene un solo conflicto aceptado, `M[NpTail, PREP]`: una frase preposicional se pega al sustantivo más cercano, la misma decisión que el else colgante de la Fase 1. La ambigüedad del español se demuestra aparte, con la gramática natural (sección 5) |
| 3 | Concordancia | Dentro de la gramática, duplicando no terminales: número entre sujeto y verbo, y género y número entre determinante, sustantivo y adjetivos. No hay analizador semántico |
| 4 | Lexer | Parte la oración en palabras y busca cada una en el lexicón (sección 4). Una palabra que no está en el lexicón es un error léxico |
| 5 | Vocabulario | 98 palabras sin ambigüedad de categoría: cada palabra tiene un solo tipo de token. Sin contracciones (`del`, `al`), sin pronombres y sin adjetivos que no cambian de género (`grande`) |
| 6 | Tiempos verbales | Presente y pretérito indefinido (`come`, `comió`). La gramática no los distingue; el tiempo es un rasgo del lexicón |
| 7 | Árbol | Parse tree, igual que en la Fase 1, dibujado con `nltk.Tree` reutilizando `minicpp/visualization.py` |
| 8 | Set de prueba | Cada oración lleva dos etiquetas: si es español correcto (`spanish_ok`) y si la cubre nuestra gramática (`in_grammar`). Las métricas se calculan contra las dos (sección 9) |
| 9 | Qué se compara | Tarea A: aceptar o rechazar. Tarea B: categoría gramatical (UPOS) de cada palabra. Tarea C: dónde se pega la frase preposicional en las oraciones ambiguas |
| 10 | Herramientas de NLP | spaCy con `es_core_news_md` y un modelo de HuggingFace para etiquetado en español (sección 10) |
| 11 | LLM | Claude Haiku por la API de Anthropic, con temperatura 0 y respuesta en JSON (sección 11) |
| 12 | Demo | La demo del parser corre sin internet. Los resultados de spaCy, HuggingFace y el LLM se presentan desde los archivos ya guardados |
| 13 | Idioma | Igual que en la Fase 1: código en inglés; documentación, datos del español, prompts y mensajes al usuario en español (sección 3) |
| 14 | Git y entorno | Igual que en la Fase 1: uv, PR a `develop`, Conventional Commits (sección 13) |

### Decisiones que salen de la gramática

- **Estructura cubierta.** Sujeto, verbo, objeto opcional, un adverbio opcional después del objeto y frases preposicionales al final. El sujeto y el objeto siempre llevan determinante (`los niños comieron manzanas` queda fuera).
- **Orden fijo.** El adverbio va después del objeto. `el niño come rápidamente una manzana` queda fuera; es un buen caso de nivel 2 o 3.
- **Punto final opcional.** `el perro duerme` y `el perro duerme.` son válidas.
- **Sin coma ni otros signos.** Cualquier otro signo es un error léxico.
- **La concordancia de tiempo no existe en esta gramática.** Solo se revisan género y número.

### Decisiones posteriores

Se toman durante el desarrollo, cada una por su dueño:

| Decisión | Dueño | Cuándo |
|---|---|---|
| Modelo exacto de HuggingFace | P4 | Al inicio, antes de escribir el set de resultados |
| Detalles del criterio de aceptación de spaCy | P4 con P3 | Cuando el set tenga sus primeras 20 oraciones |
| Ejemplos del prompt few-shot (3 a 5, fuera del set) | P5 | Antes de correr el experimento |
| Repeticiones por oración en el LLM | P5 | Antes de correr el experimento |
| Tipos de gráfica | P4 | Con las primeras métricas |
| Quién pone la tarjeta para la API | Todos | Antes de que P5 corra el experimento |
| Orden y tiempos de la presentación | P5 | Con los resultados listos |

## 3. Idioma

| En inglés | En español |
|---|---|
| Identificadores, comentarios y docstrings | `CONTRATO_FASE2.md`, `README.md`, `docs/` e informe |
| Nombres de archivos, carpetas, ramas y commits | Oraciones del set y palabras del lexicón (son los datos del experimento) |
| Gramáticas (`.gram`, `.bnf`) y tipos de token | Prompts del LLM |
| Campos de los archivos JSONL y TSV | Mensajes de error y salida de la línea de comandos |

## 4. Lexicón y tokens

Dueño: P2. Archivo: `spanish/lexicon.tsv`, separado por tabuladores:

| Columna | Contenido | Ejemplo |
|---|---|---|
| `word` | La palabra en minúsculas, con tilde | `comió` |
| `type` | Tipo de token, que es el terminal de la gramática | `VERB_S` |
| `upos` | Categoría universal, para comparar con spaCy y HuggingFace | `VERB` |
| `lemma` | Forma base | `comer` |
| `gender` | `M`, `F` o vacío | |
| `number` | `S`, `P` o vacío | `S` |
| `tense` | `presente`, `preterito` o vacío | `preterito` |

### Tipos de token

| Tipo | Palabras | UPOS |
|---|---|---|
| `DET_MS`, `DET_FS`, `DET_MP`, `DET_FP` | `el la los las un una unos unas` | `DET` |
| `NOUN_MS`, `NOUN_FS`, `NOUN_MP`, `NOUN_FP` | `niño perro gato libro maestro árbol parque`, `niña manzana casa mesa maestra carta escuela` y sus plurales | `NOUN` |
| `ADJ_MS`, `ADJ_FS`, `ADJ_MP`, `ADJ_FP` | `pequeño rojo alto viejo nuevo blanco` en sus cuatro formas | `ADJ` |
| `VERB_S`, `VERB_P` | `comer leer escribir ver buscar correr dormir`, en presente y pretérito, tercera persona singular y plural | `VERB` |
| `ADV` | `rápidamente lentamente ayer hoy siempre temprano` | `ADV` |
| `PREP` | `en con de sobre` | `ADP` |
| `PERIOD` | `.` | `PUNCT` |
| `EOF` | Fin de la oración, lexema vacío | |

En total, 98 palabras y el punto.

### Reglas del lexer

- `tokenize(sentence: str) -> list[Token]` en `spanish/lexer.py`. Reutiliza `Token` de `minicpp/tokens.py`; la línea siempre es 1 y la columna es la posición del primer carácter de la palabra.
- Pasa todo a minúsculas antes de buscar. Respeta las tildes: `arbol` sin tilde es un error léxico.
- Separa el punto aunque vaya pegado: `manzana.` da dos tokens.
- Una palabra que no está en el lexicón lanza `LexicalError` con el mensaje `palabra fuera del vocabulario 'gatas'`.
- La lista siempre termina con `EOF`.
- Para cambiar el lexicón se avisa a P1 y P3, porque cambia lo que el set puede usar.

## 5. Gramática del español

Dueño: P1. Tres archivos en `grammars/`, en el mismo formato que `cpp.gram`:

| Archivo | Qué es | Producciones | ¿LL(1)? |
|---|---|---|---|
| `es.gram` | La gramática del parser, con concordancia | 35 (22 no terminales, 17 terminales) | Sí, salvo `M[NpTail, PREP]` aceptado |
| `es_base.gram` | La misma estructura sin concordancia; acepta `los niño come` | 18 (12 no terminales, 7 terminales) | Sí, salvo el mismo conflicto |
| `es_natural.gram` | La gramática como se escribiría sin pensar en LL(1), con recursión izquierda | 9 | No: 2 conflictos sin aceptar |

`es.bnf` es `es.gram` en notación de clase. Se regenera con `uv run python -m verifier grammars/es.gram --class-notation -o grammars/es.bnf`.

### Lo que demuestra cada archivo

- **La concordancia hace crecer la gramática.** Pasar de `es_base.gram` a `es.gram` lleva las producciones de 18 a 35 y los no terminales de 12 a 22, solo con género y número. Cada rasgo nuevo multiplica las copias: persona o tiempo las multiplicarían otra vez. Con rasgos finitos, la concordancia sí cabe en una CFG, pero la gramática explota.
- **El español es ambiguo.** Con `es_natural.gram`, la oración `el maestro lee la carta en la casa` tiene dos árboles: `en la casa` puede modificar a `carta` o a `lee`. Comprobado con `nltk.ChartParser`. Una gramática LL(1) no puede ser ambigua, así que `es.gram` elige una lectura (la frase se pega a `carta`).
- **Lo que no cabe en ninguna CFG.** Las dependencias cruzadas, como `Juan, Ana y Luis están cansado, cansada y cansado, respectivamente`. Esto no se programa: se demuestra en el informe con el lema de bombeo, y aparece en el set como oración de nivel 3.

### Gramática del parser (`es.gram`)

```
Sentence -> Clause EndMark
Clause -> NpSing VpSing | NpPlur VpPlur
EndMark -> PERIOD | ε
NounPhrase -> NpSing | NpPlur
NpSing -> NpMS | NpFS
NpPlur -> NpMP | NpFP
NpMS -> DET_MS NOUN_MS AdjListMS NpTail
NpFS -> DET_FS NOUN_FS AdjListFS NpTail
NpMP -> DET_MP NOUN_MP AdjListMP NpTail
NpFP -> DET_FP NOUN_FP AdjListFP NpTail
AdjListMS -> ADJ_MS AdjListMS | ε
AdjListFS -> ADJ_FS AdjListFS | ε
AdjListMP -> ADJ_MP AdjListMP | ε
AdjListFP -> ADJ_FP AdjListFP | ε
NpTail -> PrepPhrase NpTail | ε
PrepPhrase -> PREP NounPhrase
VpSing -> VERB_S VpTail
VpPlur -> VERB_P VpTail
VpTail -> Object AdvOpt PpList
Object -> NounPhrase | ε
AdvOpt -> ADV | ε
PpList -> PrepPhrase PpList | ε
```

## 6. Parser y árbol

Dueño: P2.

- `spanish/parser.py`, clase `SpanishParser(tokens).parse() -> Node`, con raíz `Sentence`. Reutiliza `Node` y `SyntacticError` de `minicpp`.
- Las mismas convenciones de la Fase 1: un método por no terminal en snake_case (`np_ms`, `adj_list_ms`, `np_tail`), con la producción en la primera línea del docstring, y los auxiliares `current`, `check`, `consume`, `consume_one_of`, `epsilon` y `error`.
- `np_tail` elige `PrepPhrase NpTail` siempre que ve `PREP`, y su docstring explica el conflicto, igual que `else_part` en el parser de C++.
- `spanish.analyze(sentence) -> Node` une el lexer y el parser.
- Línea de comandos: `uv run python -m spanish "el niño come una manzana" --tree`, con las mismas opciones de vista que en la Fase 1 (`--view console`, `window` u `outline`). Imprime "Oración válida" o el error.
- `experiments/run_parser.py` corre el parser sobre todo el set y escribe `results/parser.jsonl` (sección 8).

## 7. Set de prueba

Dueño: P3. Archivo: `data/test_set.jsonl`, una oración por línea:

```json
{"id": "L2-07", "level": 2, "sentence": "el maestro lee la carta en la casa", "spanish_ok": true, "in_grammar": true, "upos": ["DET", "NOUN", "VERB", "DET", "NOUN", "ADP", "DET", "NOUN"], "ambiguous": true, "attachment": "noun", "phenomena": ["pp", "ambigua"], "note": ""}
```

| Campo | Contenido |
|---|---|
| `id` | `L` + nivel + número: `L1-01`, `L3-15` |
| `level` | 1, 2 o 3 |
| `sentence` | La oración, en minúsculas, con punto final opcional |
| `spanish_ok` | ¿Es español correcto? |
| `in_grammar` | ¿La acepta `es.gram`? Se comprueba corriendo el parser; si no coincide con lo que se esperaba, se revisa la oración |
| `upos` | Categoría esperada de cada palabra, sin el punto. `null` si la oración no es español correcto |
| `ambiguous` | ¿Tiene más de una lectura? |
| `attachment` | Solo en las ambiguas: `noun` o `verb`, según la lectura más natural |
| `phenomena` | Etiquetas de lo que prueba la oración (lista de abajo) |
| `note` | Comentario libre, por ejemplo por qué es agramatical |

Etiquetas de `phenomena`: `svo`, `intransitiva`, `adj`, `adv`, `pp`, `preterito`, `plural`, `concordancia_numero`, `concordancia_genero`, `orden`, `ambigua`, `subordinada`, `coordinacion`, `respectivamente`, `clitico`, `contraccion`, `fuera_de_vocabulario`.

### Composición

| Nivel | Mínimo | Qué tiene |
|---|---|---|
| 1 | 20 | Oraciones simples que la gramática acepta: sujeto, verbo y a veces objeto |
| 2 | 20 | Modificadores y variaciones: adjetivos, adverbios, frases preposicionales, pretérito, plurales, y errores de concordancia |
| 3 | 20 | Fenómenos que exceden la gramática: subordinadas, coordinación, `respectivamente`, clíticos, contracciones, otro orden de palabras |

En todo el set tiene que haber al menos **15 oraciones con `spanish_ok: false`** (sin ellas no se puede medir la tasa de rechazo correcto) y al menos **6 ambiguas**.

`tests/test_test_set.py` revisa el formato y los mínimos: que cada línea tenga todos los campos, que `upos` tenga una etiqueta por palabra y que se cumplan los mínimos de esta tabla.

## 8. Formato común de resultados

Cada herramienta escribe `results/<herramienta>.jsonl`, con una línea por oración del set:

```json
{"id": "L2-07", "tool": "spacy", "accepted": true, "upos": ["DET", "NOUN", "VERB", "DET", "NOUN", "ADP", "DET", "NOUN"], "attachment": "verb", "tree": null, "error": null}
```

| Campo | Contenido |
|---|---|
| `tool` | `parser`, `spacy`, `hf`, `llm_zero` o `llm_few` |
| `accepted` | `true` o `false`; `null` si la herramienta no hace esa tarea |
| `upos` | Lista de categorías, una por palabra y sin el punto; `null` si no hay salida |
| `attachment` | `noun`, `verb` o `null` |
| `tree` | El árbol en formato de corchetes (el de `nltk.Tree`), si la herramienta lo da |
| `error` | El mensaje de error del parser o del LLM, si hubo |

Para el parser, `upos` sale del lexicón cuando acepta la oración, y es `null` cuando la rechaza.

## 9. Métricas

Dueño: P4. Script: `experiments/metrics.py`, que lee `data/test_set.jsonl` y todos los `results/*.jsonl` y escribe `results/metrics.csv` y las gráficas en `figures/`.

### Tarea A: aceptar o rechazar

La clase positiva es "aceptar". Con VP, FP, VN y FN como verdaderos y falsos positivos y negativos:

$$\text{precisión} = \frac{VP}{VP + FP} \qquad \text{recall} = \frac{VP}{VP + FN} \qquad \text{rechazo correcto} = \frac{VN}{VN + FP}$$

Se calcula dos veces, contra dos referencias:

- **Contra `in_grammar`:** qué tanto sigue cada herramienta nuestra gramática formal.
- **Contra `spanish_ok`:** qué tanto distingue el español correcto del incorrecto.

Las dos referencias no coinciden en las oraciones de nivel 3, que son español correcto pero están fuera de la gramática. Ahí se ve la diferencia entre un parser formal y una herramienta estadística. Para el LLM, la **tasa de desviación** es la fracción de esas oraciones que acepta: muestra cuándo se guía por su conocimiento del español en vez de las reglas.

Todo se reporta en total y por nivel.

### Tarea B: categorías

Exactitud de UPOS por palabra, sobre las oraciones con `upos` esperado. Una herramienta sin salida para una oración cuenta como error en todas sus palabras, y se reporta aparte su cobertura (qué fracción de oraciones etiquetó).

### Tarea C: ambigüedad

En las oraciones con `ambiguous: true`, cuántas veces cada herramienta pega la frase preposicional al sustantivo y cuántas al verbo, y cuántas coinciden con `attachment`.

### Clasificación de errores

Dueño: P3. Cada error de cada herramienta se clasifica como falso positivo (acepta algo que debía rechazar), falso negativo (rechaza algo que debía aceptar) o error de etiquetado (categoría equivocada), con el fenómeno de la oración. Sale en `results/errors.csv`.

## 10. Herramientas de NLP

Dueño: P4. Script: `experiments/run_nlp.py`, que escribe `results/spacy.jsonl` y `results/hf.jsonl`.

- **spaCy** con `es_core_news_md`. Da UPOS, rasgos morfológicos (`Gender`, `Number`) y dependencias.
  - Tarea A: spaCy nunca rechaza una oración, así que se le aplica un criterio fijo. Acepta si cada determinante y adjetivo concuerda en género y número con su sustantivo, y si el sujeto (`nsubj`) concuerda en número con su verbo. Si no, rechaza.
  - Tarea C: la frase preposicional se pega al sustantivo si su cabeza en el árbol de dependencias es un `NOUN`, y al verbo si es un `VERB`.
- **HuggingFace**: un modelo de clasificación de tokens con UPOS para español. Si también da rasgos morfológicos, se le aplica el mismo criterio de la Tarea A; si no, participa solo en la Tarea B, y el informe lo dice.
- El modelo de spaCy se agrega con la URL de su `.whl` (`uv add <url>`), porque `spacy download` no funciona dentro de un entorno de uv. Su versión tiene que coincidir con la de spaCy.
- `transformers` necesita `torch`, que pesa varios cientos de MB. Conviene instalar la versión solo para CPU.

## 11. Experimento con el LLM

Dueño: P5.

- **Modelo:** Claude Haiku por la API de Anthropic (paquete `anthropic`). El identificador exacto del modelo queda guardado en cada log.
- **Clave:** en la variable de entorno `ANTHROPIC_API_KEY`, nunca en el código. `.env` va en el `.gitignore`.
- **Parámetros:** temperatura 0.
- **Prompts** en `prompts/`, en español:
  - `zero_shot.txt`: las reglas de `es.gram` y el lexicón, y la instrucción de analizar siguiendo **solo** esas reglas.
  - `few_shot.txt`: lo mismo, más 3 a 5 ejemplos resueltos que **no** están en el set.
- **Respuesta pedida**, en JSON:

  ```json
  {"accepted": true, "tree": "(Sentence (Clause (NpSing ...)))", "upos": ["DET", "NOUN", "VERB"], "violated_rule": null}
  ```

- **Validador** (`experiments/llm_validator.py`): revisa que el árbol del LLM use solo producciones de `es.gram` y palabras del lexicón con su tipo. Un árbol que no pasa el validador cuenta como desviación de las reglas aunque la respuesta `accepted` acierte.
- **Logs** en `logs/llm/<modo>.jsonl`: fecha, modelo, modo, `id` de la oración, prompt completo, respuesta cruda y resultado del validador. Se suben al repositorio.
- `experiments/run_llm.py` escribe `results/llm_zero.jsonl` y `results/llm_few.jsonl` a partir de los logs. Si los logs ya existen, no vuelve a llamar a la API.

## 12. Formato de las pruebas

| Componente | Archivo | Dueño |
|---|---|---|
| Gramáticas del español | `tests/test_es_grammars.py`: `es.gram` y `es_base.gram` solo tienen el conflicto aceptado, y `es_natural.gram` no es LL(1) | P1 |
| Lexer del español | `tests/test_es_lexer.py` | P2 |
| Parser del español | `tests/test_es_parser.py` | P2 |
| Set de prueba | `tests/test_test_set.py` | P3 |
| Métricas y conversión de salidas | `tests/test_metrics.py` y `tests/test_nlp_convert.py` | P4 |
| Validador del LLM | `tests/test_llm_validator.py` | P5 |

- Las pruebas nunca llaman a la API ni descargan modelos: usan respuestas guardadas o salidas de ejemplo.
- Los nombres siguen la regla de la Fase 1: empiezan con el no terminal, la regla o el tema que prueban (`test_np_tail_...`, `test_out_of_vocabulary_...`, `test_precision_...`).
- Las 607 pruebas de la Fase 1 tienen que seguir pasando.

## 13. Estructura del repositorio

Lo nuevo de la Fase 2:

```
.
├── CONTRATO_FASE2.md             todos
├── grammars/
│   ├── es.gram                   P1
│   ├── es.bnf                    P1 (se genera de es.gram)
│   ├── es_base.gram              P1
│   └── es_natural.gram           P1
├── spanish/
│   ├── __init__.py               analyze() (P2)
│   ├── __main__.py               línea de comandos (P2)
│   ├── lexicon.tsv               P2
│   ├── lexer.py                  P2
│   └── parser.py                 P2
├── data/
│   └── test_set.jsonl            P3
├── experiments/
│   ├── run_parser.py             P2
│   ├── run_nlp.py                P4
│   ├── metrics.py                P4
│   ├── classify_errors.py        P3
│   ├── run_llm.py                P5
│   └── llm_validator.py          P5
├── prompts/
│   ├── zero_shot.txt             P5
│   └── few_shot.txt              P5
├── logs/llm/                     P5
├── results/                      los genera cada script
├── figures/                      P4
├── docs/informe/fase2/           una sección por persona; P3 integra
└── tests/                        los archivos de la sección 12
```

### Entorno y Git

Igual que en la Fase 1:

- uv para todo. Las dependencias nuevas (`spacy`, el modelo de spaCy, `transformers`, `torch`, `anthropic`, `matplotlib`) las agrega su dueño con `uv add`, y se regenera `requirements.txt` en el mismo commit.
- Todos los pull requests van a `develop`. `main` no se toca hasta la entrega.
- Ramas: `feat/es-grammar` (P1), `feat/es-parser` (P2), `feat/test-set` (P3), `feat/nlp-metrics` (P4), `feat/llm` (P5).
- Conventional Commits. Alcances nuevos: `es-grammar`, `es-lexer`, `es-parser`, `test-set`, `nlp`, `metrics`, `llm`, `report`.
- Antes de cada pull request, `uv run pytest` pasa completo.

## 14. Reparto de la Fase 2

### Etapa 0: ya hecha

| Qué | Dónde |
|---|---|
| Las tres gramáticas y `es.bnf`, revisadas con el verificador | `grammars/` |
| El lexicón de 98 palabras | `spanish/lexicon.tsv` |
| Los formatos del set, de los resultados, de las métricas y del LLM | Secciones 7 a 11 |

Cada quien revisa su sección y la aprueba antes de programar. Desde ahí, los cinco empiezan a la vez.

### Trabajo principal

| Persona | Del PDF | Construye | Sus pruebas | Sección del informe | En la presentación |
|---|---|---|---|---|---|
| P1, ResidenteM | O1; A1 | Dueño de las gramáticas. Los dos árboles de la oración ambigua (con `nltk.ChartParser` sobre `es_natural.gram`). La tabla de crecimiento por concordancia. La demostración con el lema de bombeo de que `respectivamente` no es libre de contexto | `test_es_grammars.py` | Marco teórico, diseño de la gramática y análisis formal de dónde falla la CFG | La gramática y por qué una CFG no alcanza |
| P2, César | O1; A2 | Lexer, parser, `analyze()`, línea de comandos y `run_parser.py` | `test_es_lexer.py` y `test_es_parser.py` | Implementación del parser | Demo en vivo del parser con sus árboles |
| P3, Diego Rosa | O4; A3 | El set de prueba completo con sus etiquetas, la clasificación de errores (`classify_errors.py`) y la integración del informe | `test_test_set.py` | Set de prueba, metodología y clasificación de errores | El set y cómo se etiquetó |
| P4, Rober | O2, O4; A4, A5, A7 | `run_nlp.py` con spaCy y HuggingFace, `metrics.py`, tablas y gráficas | `test_metrics.py` y `test_nlp_convert.py` | Resultados cuantitativos y análisis de diferencias (A7) | Tablas y gráficas comparativas |
| P5, Diego Mejía | O3; A6 | Prompts, `run_llm.py`, el validador y los logs. Arma la presentación | `test_llm_validator.py` | Comportamiento del LLM frente a las reglas | El experimento con el LLM y las conclusiones |

### Dependencias

- Con la Etapa 0 hecha, nadie espera a nadie para empezar:
  - P2 programa contra `es.gram` y el lexicón.
  - P3 escribe oraciones con el vocabulario del lexicón.
  - P4 prueba spaCy y HuggingFace con oraciones cualquiera y escribe `metrics.py` contra el formato de la sección 8.
  - P5 escribe los prompts con `es.gram` y prueba el validador con árboles escritos a mano.
- El set de P3 es lo primero que hace falta completo: P2, P4 y P5 lo necesitan para correr sus experimentos. Conviene que suba una primera versión de 20 oraciones lo antes posible.
- `in_grammar` se confirma con el parser de P2. Hasta que exista, P3 la marca a mano.
- `metrics.py` corre cuando están los cinco archivos de `results/`.
- La clasificación de errores de P3 sale de las métricas.

### Cierre de la Fase 2

1. Cada persona escribe su sección del informe en `docs/informe/fase2/`, y P3 integra el informe de 7 a 10 páginas.
2. P5 arma la presentación de 15 a 20 minutos, con un tiempo para cada persona.
3. Ensayo de la demo sin internet: el parser en vivo y los resultados desde archivos.
4. Recorrido de módulos: cada quien explica su parte al grupo y prepara 5 preguntas sobre un módulo que no es suyo.
5. README: cómo reproducir cada experimento, en orden.
6. Al final, `develop` se une a `main` con un pull request.
