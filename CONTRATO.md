# Contrato del proyecto TLP02-2026, Fase 1

Este documento fija las decisiones y las interfaces entre las partes del proyecto. Si alguien necesita cambiar algo de aquí, lo habla con el dueño de esa sección y avisa al grupo antes de tocar código.

## 1. Referencias del PDF

| Código | Objetivo |
|---|---|
| O1 | Implementar el parser y comprobar que funciona correctamente |
| O2 | Extender la CFG para capturar fenómenos del español |
| O3 | Identificar y documentar con precisión formal en qué punto y por qué falla la CFG |
| O4 | Conectar la práctica con la jerarquía de Chomsky |

| Código | Actividad |
|---|---|
| A1 | Investigar las diferencias entre lenguajes formales y naturales |
| A2 | Implementar en Python el parser, con árbol y manejo de errores |
| A3 | Definir pruebas con entradas válidas e inválidas |
| A4 | Extender la CFG al español |
| A5 | Documentar los puntos de falla y relacionarlos con Chomsky |
| A6 | Demo con NLTK/spaCy |

## 2. Decisiones

| # | Tema | Decisión |
|---|---|---|
| 1 | Tipo de parser | Descendente recursivo sin backtracking sobre una gramática LL(1). Un verificador calcula FIRST, FOLLOW, la tabla y los conflictos |
| 2 | Tipos de datos | `int`, `float`, `double`, `char`, `bool` y `string`. `void` solo como tipo de retorno de funciones |
| 3 | Agregados al subconjunto | `++`, `--`, asignaciones compuestas (`+=`, `-=`, `*=`, `/=`, `%=`), literales de cadena y de carácter, `endl` |
| 4 | Fuera del alcance | Arreglos, punteros, referencias, `struct`, clases, operador ternario, operadores de bits, casts, `const`, prototipos de funciones, `std::` calificado y preprocesador general |
| 5 | Encabezado | `#include <iostream>`, `#include <string>` y `using namespace std;`, todos opcionales |
| 6 | Árbol | Parse tree (árbol de derivación), no AST |
| 7 | Dangling else | El `else` se asocia al `if` más cercano. Es el único conflicto LL(1) aceptado |
| 8 | `cin` y `cout` | Sentencias propias. Después de `<<` va una expresión aditiva o `endl`; después de `>>` va solo un identificador |
| 9 | Errores | Se reporta el primer error con línea, columna, lo esperado y lo encontrado. El modo pánico es opcional |
| 10 | Extensión al español | Módulo aparte que reutiliza el nodo del árbol y el verificador, con sus propios archivos de gramática |
| 11 | Herramientas | uv para el entorno y las dependencias, Python 3.12, pytest, NLTK, spaCy con `es_core_news_md`, GitHub |
| 12 | Docente | Se le envía `docs/especificacion_subconjunto.md` antes de programar |
| 13 | Forma del árbol | El árbol sigue exactamente la BNF de `grammars/cpp.gram`, con los no terminales `...Tail` y las hojas ε |
| 14 | Idioma | Código en inglés; documentación y mensajes al usuario en español (detalle en la sección 3) |

`string` no es un tipo primitivo de C++: es una clase de la biblioteca estándar. Aquí lo tratamos como palabra reservada para simplificar, y el informe lo aclara.

### Decisiones que salen de la gramática

- **Declaraciones múltiples.** Se permiten, por ejemplo `int a, b = 2, c;`.
- **Variables globales.** Se permiten. Las funciones no se pueden anidar.
- **Etiquetas de `case`.** Solo aceptan literales: entero, entero negativo, carácter, `true` o `false`. C++ acepta cualquier expresión constante, pero eso queda fuera.
- **Sentencia vacía.** Se acepta un `;` suelto.
- **Variables en asignaciones e incrementos.** El lado izquierdo de una asignación y el operando de `++` o `--` deben ser una variable. La gramática no lo puede expresar sin perder la propiedad LL(1), así que P1 lo revisa en el código y lanza `SyntacticError`. En el informe se presenta como una restricción de contexto.

## 3. Idioma

| En inglés | En español |
|---|---|
| Identificadores (clases, funciones, variables, constantes) | `CONTRATO.md`, `README.md` y todo lo que está en `docs/` |
| Comentarios y docstrings del código | Informe y presentación |
| Nombres de archivos y carpetas del código | Mensajes que ve el usuario: errores léxicos y sintácticos, salida de la línea de comandos |
| Gramáticas (`.gram`, `.bnf`) y tipos de token | Oraciones del español (son datos del experimento) |
| Mensajes de commit y nombres de ramas | Guion de la demo |

Los mensajes al usuario van en español porque la demo y la defensa son en español. Viven en el código como cadenas de texto; todo lo demás del código va en inglés.

## 4. Contrato de tokens

Dueño: P2.

```python
@dataclass
class Token:
    type: str      # token type name, e.g. "ID" or "SEMICOLON"
    lexeme: str    # text as it appears in the source code
    line: int      # starts at 1
    column: int    # starts at 1
```

El lexer expone `tokenize(code: str) -> list[Token]`. La lista termina siempre con un token `EOF` de lexema vacío.

### Tipos de token

| Grupo | Tipo | Lexema |
|---|---|---|
| Encabezado | `INCLUDE` | `#include <iostream>` o `#include <string>`, la directiva completa en un solo token |
| | `USING`, `NAMESPACE`, `STD` | `using`, `namespace`, `std` |
| Tipos | `INT`, `FLOAT`, `DOUBLE`, `CHAR`, `BOOL`, `STRING`, `VOID` | la palabra en minúsculas |
| Control | `IF`, `ELSE`, `WHILE`, `DO`, `FOR`, `SWITCH`, `CASE`, `DEFAULT`, `BREAK`, `CONTINUE`, `RETURN` | la palabra en minúsculas |
| E/S | `CIN`, `COUT`, `ENDL` | `cin`, `cout`, `endl` |
| Literales | `INT_LITERAL` | `0`, `42` |
| | `FLOAT_LITERAL` | `3.14` (dígitos, punto, dígitos) |
| | `STRING_LITERAL` | `"Hola\n"` |
| | `CHAR_LITERAL` | `'a'`, `'\n'` |
| | `TRUE`, `FALSE` | `true`, `false` |
| Identificador | `ID` | letra o `_`, seguida de letras, dígitos o `_` |
| Aritméticos | `PLUS`, `MINUS`, `STAR`, `SLASH`, `PERCENT` | `+ - * / %` |
| Incremento | `INCREMENT`, `DECREMENT` | `++ --` |
| Asignación | `ASSIGN`, `PLUS_ASSIGN`, `MINUS_ASSIGN`, `STAR_ASSIGN`, `SLASH_ASSIGN`, `PERCENT_ASSIGN` | `= += -= *= /= %=` |
| Comparación | `EQUAL`, `NOT_EQUAL`, `LESS`, `GREATER`, `LESS_EQUAL`, `GREATER_EQUAL` | `== != < > <= >=` |
| Lógicos | `AND`, `OR`, `NOT` | `&& \|\| !` |
| E/S | `SHIFT_LEFT`, `SHIFT_RIGHT` | `<< >>` |
| Delimitadores | `LPAREN`, `RPAREN`, `LBRACE`, `RBRACE`, `SEMICOLON`, `COMMA`, `COLON` | `( ) { } ; , :` |
| Fin | `EOF` | vacío |

### Reglas léxicas

- **Coincidencia más larga.** `++` es `INCREMENT` y no dos `PLUS`; `<<` es un solo token; `<=` es `LESS_EQUAL`.
- **Palabras reservadas.** Se reconocen primero como identificador y después se buscan en la tabla de reservadas.
- **Lo que se ignora.** Espacios, tabulaciones, saltos de línea, comentarios `//` hasta el fin de la línea y comentarios `/* */`.
- **Literales.**
  - Las cadenas no pueden ocupar varias líneas.
  - Escapes aceptados: `\n`, `\t`, `\\`, `\"`, `\'`.
  - No se aceptan sufijos como `3.14f`, ni números como `.5` o `5.`.
- **Errores léxicos.**
  - Un carácter no reconocido, como `@` o `$`.
  - Una cadena o un comentario sin cerrar.
  - Un carácter vacío (`''`).
  - Un `#include` de otra biblioteca.

## 5. Formato del archivo de gramática

Dueño: P4.

- Una regla por línea: `A -> alternativa1 | alternativa2`.
- Los símbolos van separados por espacios. `ε` es la cadena vacía.
- Los no terminales van en CamelCase y los terminales con el nombre exacto del tipo de token.
- La primera regla define el símbolo inicial.
- `EOF` no se escribe en la gramática: el verificador lo usa como `$`.
- Las líneas que empiezan con `#` son comentarios.

El verificador se ejecuta con `uv run python -m verifier grammars/cpp.gram` e imprime FIRST, FOLLOW, la tabla y los conflictos. Cada conflicto se reporta así:

```
Conflict at M[ElsePart, ELSE]:
  ElsePart -> ELSE Stmt
  ElsePart -> ε
```

## 6. Gramática del subconjunto

Dueño: P1. La gramática existe en dos archivos con el mismo contenido, regla por regla:

| Archivo | Formato | Para qué |
|---|---|---|
| `grammars/cpp.gram` | `AdditiveExpr -> MultExpr AdditiveExprTail` | Lo lee el verificador |
| `grammars/cpp.bnf` | `<additive_expr> ::= <mult_expr> <additive_expr_tail>`, la notación de clase | Lo leemos nosotros; va en el informe y en la presentación |

`cpp.gram` es la fuente. Si cambia, se regenera `cpp.bnf` con `uv run python -m verifier grammars/cpp.gram --class-notation`. `cpp.bnf` incluye al final el nivel léxico (identificadores, números, cadenas), que reconoce el lexer y no el parser.

- **Tamaño.** 68 no terminales, 144 producciones y 63 terminales, sin contar `EOF`.
- **Conflictos.** Uno solo, `M[ElsePart, ELSE]`. El parser lo resuelve eligiendo `ElsePart -> ELSE Stmt`.
- **Recursión izquierda.** No hay. Las expresiones usan el esquema `X -> Y XTail` y `XTail -> op Y XTail | ε`.
- **Precedencia.** Va de menor a mayor en este orden:

  | Nivel | Operadores |
  |---|---|
  | Asignación | `=`, `+=`, `-=`, `*=`, `/=`, `%=` (asociativa por la derecha) |
  | O lógico | `\|\|` |
  | Y lógico | `&&` |
  | Igualdad | `==`, `!=` |
  | Relacionales | `<`, `>`, `<=`, `>=` |
  | Aditivos | `+`, `-` |
  | Multiplicativos | `*`, `/`, `%` |
  | Unarios | `!`, `-`, `+`, `++` y `--` prefijos |
  | Postfijos | `++`, `--` |
  | Primarios | identificadores, llamadas, literales, paréntesis |

- **Asociatividad izquierda.** En el árbol, `XTail` se ve como recursión derecha. La asociatividad izquierda (que `a - b - c` sea `(a - b) - c`) corresponde a la interpretación del árbol, y el informe lo explica.

En el informe se explica con las reglas del ejemplo de clase cómo se llegó a esta forma:

- **Eliminación de la recursión izquierda.** `<expresion> ::= <expresion> "+" <termino>` pasa a `<additive_expr>` y `<additive_expr_tail>`.
- **Factorización por la izquierda.** Las alternativas de `<condicional>` que empiezan igual pasan a `<if_stmt>` y `<else_part>`.

## 7. Contrato del nodo y del parser

Dueño del contrato: P3. Dueño del parser: P1.

```python
class Node:
    def __init__(self, label: str, children: list["Node"] | None = None, token: Token | None = None):
        self.label = label           # nonterminal, token type or "ε"
        self.children = children or []
        self.token = token           # only on terminal leaves
```

Además tiene `is_epsilon()`, `leaves()`, que devuelve los tokens de las hojas de izquierda a derecha sin las ε, y `pretty()`, que devuelve el árbol como texto con sangría para depurar. La visualización para la demo es la de P2.

| Situación | Cómo se construye el nodo |
|---|---|
| No terminal | `Node("AdditiveExpr", children)` |
| Terminal | `Node("ID", token=tok)` |
| ε | `Node("ε")` |

API del parser:

- `Parser(tokens).parse() -> Node` devuelve la raíz con etiqueta `Program`.
- `minicpp.analyze(code: str) -> Node` une el lexer y el parser.
- `uv run python -m minicpp file.cpp` imprime "Programa válido" y el árbol, o el mensaje de error. Con `--no-tree` omite el árbol.

### Convenciones del parser

- Cada no terminal tiene un método con el mismo nombre en snake_case. Por ejemplo, `AdditiveExprTail` se implementa en `additive_expr_tail`.
- La primera línea del docstring de cada método es la producción que implementa, copiada de `cpp.gram`.
- Los auxiliares se llaman `current()`, que devuelve el token de lookahead, y `consume(token_type)`, que avanza o lanza `SyntacticError`.

## 8. Contrato de errores

Dueño: P3.

```python
class LexicalError(Exception):
    def __init__(self, line: int, column: int, detail: str): ...

class SyntacticError(Exception):
    def __init__(self, line: int, column: int, expected: list[str], found: Token): ...
```

No se usa el nombre `SyntaxError` porque ya existe en Python.

Formato único de los mensajes, en español:

```
Error léxico en línea 3, columna 7: carácter no reconocido '@'
Error sintáctico en línea 5, columna 12: se esperaba SEMICOLON y se encontró RBRACE ('}')
```

## 9. Formato de las pruebas

| Componente | Archivo | Dueño |
|---|---|---|
| Lexer | `tests/test_lexer.py` | P2 |
| Parser (pruebas unitarias por función) | `tests/test_parser_units.py` | P1 |
| Parser (programas completos) | `tests/test_parser.py` y `cases/` | P3 |
| Verificador | `tests/test_verifier.py` y `grammars/test_grammars/` | P4 |
| Español | `tests/test_spanish.py` y `spanish/sentences.tsv` | P5 |

- **Casos del parser.**
  - Los programas válidos van en `cases/valid/` y los inválidos en `cases/invalid/`.
  - Nombre de archivo: `NN_construct_description.cpp`, por ejemplo `07_switch_without_break.cpp`.
- **Primera línea de cada caso inválido.** Indica el error esperado y su línea:

  ```cpp
  // ERROR: syntactic 4
  ```

  Para un error léxico, la línea dice `// ERROR: lexical 3`.
- **Lo que comprueba pytest.**
  - Los casos válidos no lanzan excepción.
  - Los inválidos lanzan el tipo de error indicado en la línea indicada.
- **Pruebas del verificador.** Usan gramáticas del libro de Aho con FIRST y FOLLOW conocidos, por ejemplo la gramática de expresiones `E -> T E'`.
- **`spanish/sentences.tsv`.** Tiene cuatro columnas: `sentence`, `expected` (`ACCEPT` o `REJECT`), `reason` y `step`. Las oraciones y los motivos se escriben en español.

## 10. Estructura del repositorio

```
.
├── README.md                     P2
├── CONTRATO.md                   todos
├── pyproject.toml                P2 (dependencias, las administra uv)
├── uv.lock                       versiones exactas, lo genera uv
├── requirements.txt              lo genera uv, no se edita a mano
├── .python-version               P2 (3.12)
├── .gitignore                    P2
├── docs/
│   ├── especificacion_subconjunto.md   P5
│   └── informe/                  una sección por persona; P3 integra
├── grammars/
│   ├── cpp.gram                  P1 (fuente, la lee el verificador)
│   ├── cpp.bnf                   P1 (misma gramática en notación de clase)
│   ├── spanish/                  P5 (step1_svo.gram, step2_agreement.gram, ...)
│   └── test_grammars/            P4 (gramáticas del libro para probar el verificador)
├── minicpp/
│   ├── __init__.py               expone analyze()
│   ├── __main__.py               línea de comandos (P2)
│   ├── tokens.py                 Token y tabla de reservadas (P2)
│   ├── errors.py                 LexicalError y SyntacticError (P3)
│   ├── node.py                   Node (P3)
│   ├── lexer.py                  P2
│   ├── parser.py                 P1
│   └── visualization.py          P2
├── verifier/
│   ├── __init__.py
│   ├── __main__.py               P4
│   ├── grammar.py                lectura del archivo .gram (P4)
│   ├── ll1.py                    FIRST, FOLLOW, tabla y conflictos (P4)
│   └── class_notation.py         conversión a notación de clase (P4)
├── spanish/
│   ├── lexicon.py                P5
│   ├── spanish_parser.py         P5
│   ├── sentences.tsv             P5
│   └── nlp_demo.py               NLTK y spaCy (P5)
├── cases/
│   ├── valid/                    P3
│   └── invalid/                  P3
├── tests/
│   ├── test_lexer.py             P2
│   ├── test_parser_units.py      P1 (pruebas unitarias por función)
│   ├── test_parser.py            P3
│   ├── test_verifier.py          P4
│   └── test_spanish.py           P5
└── demo/
    ├── guion_demo.md             P2
    └── programs/                 P2
```

### Entorno con uv

Todo el grupo usa uv en lugar de `pip` y `venv`. uv crea el entorno virtual, instala Python 3.12 si hace falta y fija las versiones exactas en `uv.lock`, así que todos tienen las mismas dependencias.

| Para | Comando |
|---|---|
| Instalar uv (Mac o Linux) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Instalar uv (Windows, PowerShell) | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| Crear el entorno después de clonar o hacer pull | `uv sync` |
| Correr todas las pruebas | `uv run pytest` |
| Correr las pruebas de un archivo | `uv run pytest tests/test_parser_units.py` |
| Analizar un programa | `uv run python -m minicpp archivo.cpp` |
| Correr el verificador | `uv run python -m verifier grammars/cpp.gram` |
| Agregar una dependencia | `uv add nombre` (o `uv add --dev nombre` si solo sirve para desarrollo) |
| Regenerar `requirements.txt` | `uv export --format requirements-txt --no-hashes --no-emit-project -o requirements.txt` |

- `uv sync` crea `.venv/` e instala la versión de Python de `.python-version` si no está en la computadora.
- Solo agrega dependencias el dueño del componente que las necesita: NLTK lo agrega P2 y spaCy lo agrega P5. El cambio en `pyproject.toml` y `uv.lock` va en un pull request propio.
- Cada vez que se agrega una dependencia, se regenera `requirements.txt` y se suben juntos `pyproject.toml`, `uv.lock` y `requirements.txt`.
- `requirements.txt` existe para ver las dependencias de un vistazo y para quien no tenga uv: `pip install -r requirements.txt` instala lo mismo.
- El modelo de spaCy se agrega como dependencia con la URL de su archivo `.whl` (`uv add <url del modelo>`), porque `spacy download` usa pip y no funciona dentro de un entorno de uv. La versión del modelo debe coincidir con la versión de spaCy.

### Forma de trabajo con Git

- `main` solo recibe cambios por pull request.
- Cada persona trabaja en su rama: `p1-parser`, `p2-lexer`, `p3-tests`, `p4-verifier`, `p5-spanish`.
- Los mensajes de commit van en inglés y empiezan con el componente, por ejemplo `lexer: recognize compound operators`.
- `pyproject.toml`, `uv.lock`, `requirements.txt` y `.python-version` se suben al repo. `.venv/` no se sube.

## 11. Reparto

### Etapa 0: dueños de cada contrato

Este documento cubre la Etapa 0. Cada dueño revisa su sección y el grupo la aprueba en una reunión antes de programar.

| Persona | Es dueño de |
|---|---|
| P1 | Gramática del subconjunto (sección 6, `cpp.gram` y `cpp.bnf`) |
| P2 | Contrato de tokens (sección 4) y estructura del repositorio (sección 10) |
| P3 | Contrato del nodo (sección 7), contrato de errores (sección 8) y formato de pruebas (sección 9) |
| P4 | Formato del archivo de gramática (sección 5); corre `cpp.gram` por el verificador apenas lo tenga |
| P5 | Especificación para el docente (`docs/especificacion_subconjunto.md`) |

### Trabajo principal

| Persona | Del PDF | Construye | Sus pruebas | Entregable que alimenta |
|---|---|---|---|---|
| P1 | O1; A2 (análisis sintáctico) | Parser descendente recursivo completo: expresiones con sus niveles de precedencia, declaraciones, funciones, todas las sentencias, `cin`/`cout`, dangling else, construcción del árbol, errores sintácticos y la revisión de variables en asignaciones e incrementos | Pruebas unitarias por función mientras desarrolla | Código y demo en vivo |
| P2 | O1; A2 (lexer y visualización) | Lexer: palabras reservadas, operadores (coincidencia más larga), literales, comentarios, línea y columna, errores léxicos y encabezado. Además, la visualización del árbol (`nltk.Tree`, con `pretty_print` de respaldo), la línea de comandos y el README | Pruebas del lexer: cada tipo de token y casos borde (`>>` frente a `> >`, `<=`, comentarios y cadenas sin cerrar) | Código, README y guion de la demo |
| P3 | O1 (comprobar el funcionamiento); A3 y A1 | Suite de pruebas del parser: al menos un programa válido y uno inválido por cada construcción, programas combinados y mensajes de error esperados. Además, la investigación de lenguajes formales frente a naturales y la integración del informe | Es su entregable principal | Casos de prueba, marco teórico (A1) e informe integrado |
| P4 | O1 (verifica la gramática), O3 y O4; A5 | Verificador LL(1): FIRST, FOLLOW, tabla, reporte de conflictos y conversión a notación de clase (`--class-notation`). Demuestra que la gramática de P1 es LL(1) salvo el dangling else, detecta errores de la BNF antes de programar y señala la regla y el token exactos donde falla la gramática del español. Además, el análisis formal de fallas, que distingue un conflicto LL(1) de un fenómeno que no es libre de contexto (este último se demuestra con el lema de bombeo), y la sección sobre jerarquía de Chomsky y limitaciones de las CFG | Pruebas del verificador con gramáticas del libro de Aho cuyo FIRST y FOLLOW ya se conocen | Análisis de fallas y marco teórico del informe |
| P5 | O2; A4 y A6 | Extensión al español en escalera: SVO, concordancia, subordinada, modificadores y "respectivamente"; reutiliza el nodo del árbol y el verificador. Además, la demo de NLTK/spaCy con las mismas oraciones | Conjunto de oraciones con el resultado esperado (aceptar o rechazar) y el motivo | Código de la extensión y demo con NLTK/spaCy |

### Dependencias

- P2 y P4 arrancan apenas se apruebe este contrato.
- P1 arranca con las expresiones. Mientras el lexer no esté listo, prueba con listas de tokens escritas a mano siguiendo la sección 4.
- P3 escribe sus casos desde `cpp.gram`, sin esperar el código de P1.
- P5 depende solo del verificador.
- P4 y P5 trabajan en pareja, porque las fallas que documenta P4 salen de los intentos de P5.

### Cierre

1. Cada persona escribe la sección del informe de su componente, y P3 integra.
2. P2 arma el guion de la demo en vivo.
3. Recorrido de módulos: cada autor explica su parte al grupo. El parser de P1 lo explican además P3 y otro integrante.
4. Simulacro: cada persona prepara 5 preguntas sobre un módulo que no es suyo.
5. La presentación grupal es de todos.