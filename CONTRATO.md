# Contrato del proyecto TLP02-2026, Fase 1

Este documento fija las decisiones y las interfaces entre las partes del proyecto. Si alguien necesita cambiar algo de aquí, lo habla con el dueño de esa sección y avisa al grupo antes de tocar código.

## 0. Cambio de enunciado

Hubo un cambio en el enunciado del proyecto. La Fase 1 ahora es lexer y analizador semántico, vale 30% del proyecto y se entrega en video. El parser de C++ ya no se pide.

Decidimos entregar en la Fase 1 las tres etapas de un compilador: lexer, parser (ya está terminado) y analizador semántico. Así el semántico trabaja sobre el árbol real que produce nuestro parser y no sobre una representación armada a mano, que es lo que el enunciado sugiere a quien no tiene parser.

## 1. Referencias del PDF

| Código | Objetivo |
|---|---|
| O1 | Implementar un lexer para un subconjunto de un lenguaje de programación |
| O2 | Implementar un analizador semántico que verifique reglas que una CFG no puede capturar |
| O3 | Relacionar cada etapa con su nivel en la jerarquía de Chomsky: regulares para el lexer, libres de contexto para el parser, sensibles al contexto para el semántico |

| Código | Actividad |
|---|---|
| A1 | Definir formalmente los tokens con expresiones regulares o autómatas finitos |
| A2 | Implementar `lexer.py`: tokens con tipo, lexema, línea y columna, y errores léxicos |
| A3 | Implementar el analizador semántico (`semantic.py`): declaración previa, redeclaraciones, compatibilidad de tipos en asignaciones y expresiones, y ámbitos con tabla de símbolos |
| A4 | Probar el semántico. Nosotros lo hacemos sobre el árbol de nuestro parser |
| A5 | Definir pruebas válidas e inválidas con mensajes que digan línea y causa |
| A6 | Escribir en el README una reflexión sobre qué verificaciones no caben en una CFG y por qué |

| Código | Entregable |
|---|---|
| E1 | Código documentado (`lexer.py`, `semantic.py`, pruebas) en el repositorio, con README que explique cómo ejecutarlo |
| E2 | Video de máximo 10 minutos con cuatro partes: subconjunto y tokens (1-2 min), lexer con demo (3-4 min), semántico con demo (3-4 min) y reflexión (1 min) |
| E3 | En el video aparecen o hablan los cinco, y se ve el código corriendo, no solo diapositivas |

## 2. Decisiones

| # | Tema | Decisión |
|---|---|---|
| 1 | Tipo de parser | Descendente recursivo sin backtracking sobre una gramática LL(1) |
| 2 | Tipos de datos | `int`, `float`, `double`, `char`, `bool` y `string`. `void` solo como tipo de retorno de funciones |
| 3 | Agregados al subconjunto | `++`, `--`, asignaciones compuestas (`+=`, `-=`, `*=`, `/=`, `%=`), literales de cadena y de carácter, `endl` |
| 4 | Fuera del alcance | Arreglos, punteros, referencias, `struct`, clases, operador ternario, operadores de bits, casts, `const`, prototipos de funciones, `std::` calificado y preprocesador general |
| 5 | Encabezado | `#include <iostream>`, `#include <string>` y `using namespace std;`, todos opcionales |
| 6 | Árbol | Parse tree (árbol de derivación), no AST |
| 7 | Dangling else | El `else` se asocia al `if` más cercano. Es el único conflicto LL(1) aceptado |
| 8 | `cin` y `cout` | Sentencias propias. Después de `<<` va una expresión aditiva o `endl`; después de `>>` va solo un identificador |
| 9 | Errores | Léxicos y sintácticos: se reporta el primero y el análisis se detiene. Semánticos: se reportan todos, ordenados por línea. La recuperación en modo pánico del parser solo se hace si queda tiempo |
| 10 | Herramientas | uv, Python 3.12, pytest, NLTK para dibujar el árbol, GitHub |
| 11 | Docente | `docs/especificacion_subconjunto.md` describe el subconjunto; se le comparte junto con el repositorio |
| 12 | Forma del árbol | El árbol sigue exactamente la BNF de `grammars/cpp.gram`, con los no terminales `...Tail` y las hojas ε |
| 13 | Idioma | Código en inglés; documentación y mensajes al usuario en español (sección 3) |
| 14 | Etapas | El programa pasa por lexer, parser y semántico, en ese orden. Si una etapa falla, las siguientes no corren |
| 15 | Nombres de archivo | `minicpp/lexer.py` y `minicpp/semantic.py`. El enunciado nombra el segundo `semantico.py`; lo dejamos en inglés como el resto del código, y el README indica que `semantic.py` es el analizador semántico |
| 16 | Entrada del semántico | El parse tree completo, raíz `Program` |
| 17 | Video | Lo arma P3 con un guion por minutos; lo edita P5; nadie pasa de su tiempo (sección 12) |

`string` no es un tipo primitivo de C++: es una clase de la biblioteca estándar. Aquí lo tratamos como palabra reservada para simplificar, y la reflexión del README lo aclara.

### Decisiones que salen de la gramática

- **Declaraciones múltiples.** Se permiten, por ejemplo `int a, b = 2, c;`.
- **Variables globales.** Se permiten. Las funciones no se pueden anidar.
- **Etiquetas de `case`.** Solo aceptan literales: entero, entero negativo, carácter, `true` o `false`. C++ acepta cualquier expresión constante, pero eso queda fuera.
- **Sentencia vacía.** Se acepta un `;` suelto.
- **Variables en asignaciones e incrementos.** El lado izquierdo de una asignación y el operando de `++` o `--` deben ser una variable. Con la estructura de niveles de la gramática, decidirlo con un solo token no es posible (`a = 1` y `a + 1` empiezan igual): haría falta LL(2) o duplicar toda la cadena de expresiones. Por eso el parser lo revisa en el código y lanza `SyntacticError`. Es una limitación del análisis LL(1) con esta gramática, no de las CFG.
- **`break` y `continue` fuera de un ciclo.** El parser los acepta en cualquier lugar. Ahora los revisa el analizador semántico (regla S8). Una CFG sí podría expresarlo duplicando los no terminales de sentencia en una versión "dentro de ciclo", pero la gramática crecería casi al doble; los compiladores lo revisan en el análisis semántico.

## 3. Idioma

| En inglés | En español |
|---|---|
| Identificadores (clases, funciones, variables, constantes) | `CONTRATO.md`, `README.md` y todo lo que está en `docs/` |
| Comentarios y docstrings del código | Reflexión del README |
| Nombres de archivos y carpetas | Mensajes que ve el usuario: errores léxicos, sintácticos y semánticos, salida de la línea de comandos |
| Gramáticas (`.gram`, `.bnf`) y tipos de token | Guion del video |
| Mensajes de commit y nombres de ramas | |

Los mensajes al usuario van en español porque el video es en español. Viven en el código como cadenas de texto; todo lo demás del código va en inglés.

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

La especificación formal de los tokens (actividad A1) va en `docs/tokens.md`: una expresión regular por tipo de token y el autómata finito de identificadores y números. Esa misma tabla de expresiones regulares es la que usa `lexer.py`, así que lo que se muestra en el video es lo que corre.

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

## 5. Formato del archivo de gramática y verificador

Dueño: P4.

- Una regla por línea: `A -> alternativa1 | alternativa2`.
- Los símbolos van separados por espacios. `ε` es la cadena vacía.
- Los no terminales van en CamelCase y los terminales con el nombre exacto del tipo de token.
- La primera regla define el símbolo inicial.
- `EOF` no se escribe en la gramática: el verificador lo usa como `$`.
- Las líneas que empiezan con `#` son comentarios.

El verificador ya está hecho (rama `feat/verifier`, 46 pruebas) y confirma que la gramática tiene un solo conflicto, `M[ElsePart, ELSE]`. El enunciado nuevo no lo pide, pero se queda en el repositorio: respalda que el parser es LL(1) y su análisis formal (`docs/informe/p4_analisis_formal.md`) sirve para la reflexión del README. Se corre con `uv run python -m verifier grammars/cpp.gram`.

## 6. Gramática del subconjunto

Dueño: P1. La gramática existe en dos archivos con el mismo contenido, regla por regla:

| Archivo | Formato | Para qué |
|---|---|---|
| `grammars/cpp.gram` | `AdditiveExpr -> MultExpr AdditiveExprTail` | Lo lee el verificador |
| `grammars/cpp.bnf` | `<additive_expr> ::= <mult_expr> <additive_expr_tail>`, la notación de clase | Lo leemos nosotros; puede citarse en la reflexión |

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

- **Asociatividad izquierda.** En el árbol, `XTail` se ve como recursión derecha. La asociatividad izquierda (que `a - b - c` sea `(a - b) - c`) corresponde a la interpretación del árbol. El semántico la respeta al calcular tipos: recorre cada `XTail` de izquierda a derecha.

## 7. Contrato del nodo y del parser

Dueño del contrato: P3. Dueño del parser: P1.

```python
class Node:
    def __init__(self, label: str, children: list["Node"] | None = None, token: Token | None = None):
        self.label = label           # nonterminal, token type or "ε"
        self.children = children or []
        self.token = token           # only on terminal leaves
```

Además tiene:

- `is_epsilon()`, que indica si el nodo es una hoja ε.
- `leaves()`, que devuelve los tokens de las hojas de izquierda a derecha, sin las ε. Es la frontera del árbol. El semántico la usa para sacar la línea y la columna de un error: la del primer token del nodo.
- `pretty()`, que devuelve el árbol como texto con sangría para depurar. La visualización para el video es la de P2.

El módulo define la constante `EPSILON = "ε"`, que usan el nodo y el parser.

| Situación | Cómo se construye el nodo |
|---|---|
| No terminal | `Node("AdditiveExpr", children)` |
| Terminal | `Node("ID", token=tok)` |
| ε | `Node("ε")` |

API:

- `Parser(tokens).parse() -> Node` devuelve la raíz con etiqueta `Program`. Después de `Program` exige que el siguiente token sea `EOF`.
- `minicpp.analyze(code: str) -> tuple[Node, list[SemanticError]]` corre las tres etapas. Si hay un error léxico o sintáctico, lanza la excepción y no llega al semántico. Si no, devuelve el árbol y la lista de errores semánticos (vacía si el programa es válido).
- `uv run python -m minicpp archivo.cpp` imprime "Programa válido" o los errores. Opciones: `--tokens` muestra la lista de tokens y `--tree` dibuja el árbol. Las dos sirven para la demo del video.

### Convenciones del parser

- Cada no terminal tiene un método con el mismo nombre en snake_case. Por ejemplo, `AdditiveExprTail` se implementa en `additive_expr_tail`.
- La primera línea del docstring de cada método es la producción que implementa, copiada de `cpp.gram`.
- Los auxiliares son `current()`, `check(*token_types)`, `consume(token_type)`, `consume_one_of(token_types)`, `epsilon()`, `error(expected)` y `require_variable(target)`.
- El parser no calcula FIRST ni FOLLOW: las condiciones de cada método se escriben a mano.

## 8. Contrato de errores

Dueño: P3.

```python
class LexicalError(Exception):
    def __init__(self, line: int, column: int, detail: str): ...

class SyntacticError(Exception):
    def __init__(self, line: int, column: int, expected: list[str], found: Token): ...

class SemanticError(Exception):
    def __init__(self, line: int, column: int, detail: str): ...
```

No se usa el nombre `SyntaxError` porque ya existe en Python. `SemanticError` hereda de `Exception` para que todos los errores se manejen igual, pero el semántico no la lanza: la agrega a una lista y sigue revisando.

Formato único de los mensajes, en español:

```
Error léxico en línea 3, columna 7: carácter no reconocido '@'
Error sintáctico en línea 5, columna 12: se esperaba SEMICOLON y se encontró RBRACE ('}')
Error semántico en línea 8, columna 5: la variable 'total' no está declarada
```

## 9. Contrato del analizador semántico

Dueños: P1 (recorrido y funciones), P4 (tabla de símbolos, declaraciones y ámbitos), P5 (tipos).

### Tabla de símbolos (`minicpp/symbols.py`, P4)

```python
@dataclass
class Symbol:
    name: str
    kind: str                 # "variable", "parameter" or "function"
    type: str                 # "int", "double", "string", ... For functions, the return type
    line: int
    column: int
    params: list[str] | None = None   # parameter types, only for functions


class SymbolTable:
    def enter_scope(self) -> None: ...
    def exit_scope(self) -> None: ...
    def declare(self, symbol: Symbol) -> Symbol | None: ...   # returns the previous symbol if it was already declared in this scope
    def lookup(self, name: str) -> Symbol | None: ...         # searches from the innermost scope outwards
```

La tabla es una pila de diccionarios, uno por ámbito. Guarda nombres con su tipo y su posición, y no necesita saber nada del árbol.

### Ámbitos

| Ámbito | Se abre en | Se cierra en |
|---|---|---|
| Global | Inicio del programa | Fin del programa |
| Función | El nombre de la función se declara en el ámbito global; los parámetros y el bloque principal del cuerpo comparten un ámbito nuevo | Fin del cuerpo |
| Bloque | Cada `{ }` interno | Su `}` |
| `for` | El `for`, antes de su inicialización (así `int i` del `for` no existe afuera) | Fin del cuerpo del `for` |

Una variable de un ámbito interno puede tener el mismo nombre que una de un ámbito externo (la tapa mientras dure su ámbito). En el mismo ámbito, no.

Como en C++, una función solo se puede llamar si está definida más arriba en el archivo (no hay prototipos). Una función puede llamarse a sí misma, porque su nombre se declara antes de revisar el cuerpo.

### Reglas

Las reglas S1 a S5 son las mínimas que pide el enunciado. Las S6 a S9 las agregamos porque el parser ya nos da toda la información y suman a la reflexión.

| Regla | Qué revisa | Dueño | Ejemplo de mensaje |
|---|---|---|---|
| S1 | Toda variable o función usada está declarada antes | P4 | la variable 'total' no está declarada |
| S2 | No hay dos declaraciones con el mismo nombre en el mismo ámbito | P4 | 'x' ya fue declarada en este ámbito (línea 2) |
| S3 | En una asignación, el tipo del valor es compatible con el de la variable | P5 | no se puede asignar string a int |
| S4 | Los operandos de cada operador tienen tipos válidos para ese operador | P5 | el operador % necesita operandos enteros y recibió double |
| S5 | Ámbitos: una variable no se ve fuera del bloque donde se declaró | P4 | la variable 'i' no está declarada |
| S6 | Llamadas: el nombre es una función, la cantidad de argumentos coincide y cada argumento es compatible con su parámetro. Un nombre de función no se usa como variable (sin paréntesis) | P1 | 'suma' espera 2 argumentos y recibió 3 |
| S7 | `return`: una función `void` no devuelve valor; una función con tipo tiene al menos un `return` y cada uno devuelve un valor compatible. `main` puede terminar sin `return` (devuelve 0, como en C++). No se revisa que todos los caminos devuelvan un valor | P1 | la función 'suma' debe devolver un valor de tipo int |
| S8 | `break` solo dentro de un ciclo o de un `switch`; `continue` solo dentro de un ciclo | P1 | break solo puede ir dentro de un ciclo o de un switch |
| S9 | La condición de `if`, `while`, `do-while` y `for` no puede ser `string` ni una llamada a función `void` | P5 | la condición del if no puede ser de tipo string |

### Tipos

Grupo numérico: `bool`, `char`, `int`, `float` y `double`, de menor a mayor rango. Entre ellos C++ convierte solo, así que se pueden mezclar.

| Expresión | Tipos válidos | Tipo del resultado |
|---|---|---|
| Literal entero, real, cadena, carácter, `true`/`false` | | `int`, `double`, `string`, `char`, `bool` |
| `a + b`, `a - b`, `a * b`, `a / b` | numérico con numérico | El de mayor rango, y como mínimo `int` (`char + char` da `int`) |
| `a + b` | `string` con `string` | `string` |
| `a % b` | enteros: `bool`, `char` o `int` | `int` |
| `-a`, `+a` | numérico | El de `a`, y como mínimo `int` |
| `!a`, `a && b`, `a \|\| b` | numérico | `bool` |
| `a < b`, `<=`, `>`, `>=`, `==`, `!=` | numérico con numérico, o `string` con `string` | `bool` |
| `++a`, `a--` | `char`, `int`, `float`, `double` | El de `a` |
| `a = b` | `a` numérico y `b` numérico, o los dos `string` | El de `a` |
| `a += b` | igual que `=`, y con `string` solo `+=` | El de `a` |
| `a %= b` | los dos enteros | El de `a` |
| `cout << a` | cualquier tipo salvo `void` | |
| `cin >> a` | variable de cualquier tipo | |

Cualquier combinación que no esté en la tabla es un error S3 o S4. `string` con un número es error siempre, aunque C++ acepte algunos casos raros como `s = 65`; lo dejamos así por simplicidad y la reflexión lo menciona.

Si una subexpresión ya tuvo un error, su tipo queda como desconocido y no se reporta otro error por la misma causa. Así un solo error no genera una cascada de mensajes.

### Diseño de `minicpp/semantic.py`

```python
class SemanticAnalyzer:
    def check(self, tree: Node) -> list[SemanticError]: ...
```

- Recorre el árbol con un método por etiqueta de nodo: `visit_<etiqueta en snake_case>`, por ejemplo `visit_local_decl`. Si no hay método para una etiqueta, visita los hijos en orden.
- Las expresiones no se visitan: se les calcula el tipo con `type_of(node) -> str | None`, que devuelve `None` cuando el tipo es desconocido por un error anterior.
- La posición de cada error es la del primer token del nodo que lo causa (`node.leaves()[0]`).
- El archivo tiene cuatro secciones fijas, en este orden: recorrido general (P1), declaraciones y ámbitos (P4), tipos de expresiones (P5), y funciones, `return` y `break`/`continue` (P1). Cada quien edita solo su sección, así Git junta los cambios sin conflictos.

## 10. Formato de las pruebas

| Componente | Archivo | Dueño |
|---|---|---|
| Lexer | `tests/test_lexer.py` | P2 |
| Parser | `tests/test_parser_units.py` | P1 |
| Tabla de símbolos | `tests/test_symbols.py` | P4 |
| Semántico: declaraciones y ámbitos | `tests/test_semantic_scopes.py` | P4 |
| Semántico: tipos | `tests/test_semantic_types.py` | P5 |
| Semántico: funciones, `return`, `break` y `continue` | `tests/test_semantic_functions.py` | P1 |
| Programas completos | `tests/test_cases.py` y `cases/` | P3 |

- **Nombres de las pruebas.** Cada prueba empieza con la parte del contrato que revisa, así se encuentra rápido:

  | Componente | Prefijo | Ejemplo |
  |---|---|---|
  | Semántico | `test_sN_`, con N el número de la regla | `test_s8_break_outside_a_loop` |
  | Parser | El no terminal en snake_case, igual que su método en `parser.py`. Las pruebas de los auxiliares y de `parse()` llevan el nombre del método | `test_if_stmt_dangling_else_binds_to_nearest_if`, `test_consume_...` |
  | Lexer | La regla léxica o el grupo de tokens de la sección 4: `reserved_word`, `identifier`, `operator_and_delimiter`, `longest_match`, `literal`, `header`, `ignored`, `position`, `eof`, `lexical_error`, `rule_table` y `program` | `test_longest_match`, `test_lexical_error_unclosed_string` |
  | Tabla de símbolos, línea de comandos, visualización y verificador | El tema que prueban: el método, la opción o la gramática | `test_declare_...`, `test_tokens_option`, `test_cpp_grammar_...` |

  Las pruebas del semántico que no son de una sola regla empiezan con `test_valid_` (un programa válido que pasa por varias reglas) o `test_analyzer_` (el comportamiento general, como el orden de los errores).
- **Casos de programas completos.**
  - Los válidos van en `cases/valid/` y los inválidos en `cases/invalid/`.
  - Nombre de archivo: `NN_stage_description.cpp`, por ejemplo `21_semantic_undeclared_variable.cpp`.
  - Tiene que haber al menos un caso inválido por cada error léxico de la sección 4, por cada regla semántica S1 a S9 y por algunos errores sintácticos comunes.
- **Primera línea de cada caso inválido.** Indica la etapa y la línea del error:

  ```cpp
  // ERROR: semantic 5
  ```

  Las etapas son `lexical`, `syntactic` y `semantic`. Si un caso semántico tiene varios errores, se listan todas las líneas: `// ERROR: semantic 5, 9`.
- **Lo que comprueba pytest.**
  - Los casos válidos pasan las tres etapas sin errores.
  - Los inválidos fallan en la etapa indicada y en las líneas indicadas.
- **Pruebas del semántico.** Arman el programa con `analyze()`, que ya corre el lexer real. La ayuda `toks()` era temporal, mientras no existía el lexer.

## 11. Estructura del repositorio

```
.
├── README.md                     P2 (cómo correrlo) y P1 (reflexión, actividad A6)
├── CONTRATO.md                   todos
├── pyproject.toml                P2 (las dependencias las administra uv)
├── uv.lock                       versiones exactas, lo genera uv
├── requirements.txt              lo genera uv, no se edita a mano
├── .python-version               P2 (3.12)
├── .gitignore                    P2
├── docs/
│   ├── especificacion_subconjunto.md   P1
│   ├── tokens.md                 P2 (expresiones regulares y autómatas, actividad A1)
│   ├── reglas_semanticas.md      P4 y P5 (las reglas S1 a S9 con ejemplos válidos e inválidos)
│   └── informe/                  material para la reflexión del README (análisis formal de P4 y sección de la gramática)
├── grammars/
│   ├── cpp.gram                  P1
│   ├── cpp.bnf                   P1
│   └── test_grammars/            P4 (gramáticas del libro para probar el verificador)
├── minicpp/
│   ├── __init__.py               analyze() (P1)
│   ├── __main__.py               línea de comandos (P2)
│   ├── tokens.py                 Token y tabla de reservadas (P2)
│   ├── errors.py                 LexicalError, SyntacticError y SemanticError (P3)
│   ├── node.py                   Node (P3)
│   ├── lexer.py                  P2
│   ├── parser.py                 P1
│   ├── symbols.py                Symbol y SymbolTable (P4)
│   ├── semantic.py               SemanticAnalyzer (P1, P4 y P5, por secciones)
│   └── visualization.py          P2
├── verifier/                     P4 (ya hecho)
├── cases/
│   ├── valid/                    P3
│   └── invalid/                  P3
├── tests/
│   ├── test_lexer.py             P2
│   ├── test_parser_units.py      P1
│   ├── test_symbols.py           P4
│   ├── test_semantic_scopes.py   P4
│   ├── test_semantic_types.py    P5
│   ├── test_semantic_functions.py  P1
│   ├── test_verifier.py          P4 (ya hecho)
│   └── test_cases.py             P3
└── video/
    ├── guion.md                  P3
    └── programs/                 P3 (los programas que se corren en el video)
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
| Ver los tokens o el árbol | `uv run python -m minicpp archivo.cpp --tokens --tree` |
| Agregar una dependencia | `uv add nombre` (o `uv add --dev nombre` si solo sirve para desarrollo) |
| Regenerar `requirements.txt` | `uv export --format requirements-txt --no-hashes --no-emit-project -o requirements.txt` |

- `uv sync` crea `.venv/` e instala la versión de Python de `.python-version` si no está en la computadora.
- Solo agrega dependencias el dueño del componente que las necesita: NLTK lo agrega P2. El cambio en `pyproject.toml` y `uv.lock` va en un pull request propio.
- Cada vez que se agrega una dependencia, se regenera `requirements.txt` y se suben juntos `pyproject.toml`, `uv.lock` y `requirements.txt`.
- `requirements.txt` existe para ver las dependencias de un vistazo y para quien no tenga uv: `pip install -r requirements.txt` instala lo mismo. Todavía no está en el repositorio; P2 lo genera en su primer commit.

### Forma de trabajo con Git

- `main` solo recibe cambios por pull request.
- Ramas: `feat/parser` (P1), `feat/lexer` (P2), `feat/tests` (P3), `feat/verifier` y `feat/symbols` (P4), `feat/types` (P5). El trabajo de P1 en el semántico va en `feat/semantic`.
- Lo primero es unir a `main` las ramas `feat/parser` y `feat/verifier`, que ya están terminadas. Se unen sin conflictos y juntas pasan 187 pruebas.
- Antes de abrir un pull request, `uv run pytest` tiene que pasar completo.
- Los mensajes de commit siguen Conventional Commits, en inglés: `tipo(alcance): descripción`. Tipos: `feat`, `fix`, `test`, `docs`, `refactor`, `build`, `chore`, `style`. Alcances: `lexer`, `parser`, `semantic`, `symbols`, `types`, `cli`, `cases`, `contract`.
- `pyproject.toml`, `uv.lock`, `requirements.txt` y `.python-version` se suben al repo. `.venv/` no se sube.

## 12. Reparto de la Fase 1

### Etapa 0: lo que se aprueba antes de programar

| Persona | Revisa y aprueba |
|---|---|
| P1 | Sección 9 completa, en especial el diseño de `semantic.py`; abre el pull request de `feat/parser` y crea el esqueleto de `semantic.py` con sus cuatro secciones vacías |
| P2 | Sección 4 y la línea de comandos de la sección 7 |
| P3 | Secciones 8 y 10, y el formato del guion del video |
| P4 | La API de `SymbolTable` y la tabla de ámbitos de la sección 9; abre el pull request de `feat/verifier` |
| P5 | La tabla de tipos de la sección 9 |

### Trabajo principal

| Persona | Del PDF | Construye | Sus pruebas | Parte del video |
|---|---|---|---|---|
| P1 | O2, O3; A3, A6 | Esqueleto y recorrido de `semantic.py`; reglas S6, S7 y S8; `analyze()` que une las tres etapas; reflexión del README sobre lo que no cabe en una CFG | `test_semantic_functions.py` | Cómo el árbol del parser llega al semántico (30 s) y la reflexión final (1 min) |
| P2 | O1; A1, A2 | `lexer.py` con la tabla de expresiones regulares; `docs/tokens.md` con las expresiones y los autómatas; línea de comandos con `--tokens` y `--tree`; visualización del árbol; README (instalación y uso) | `test_lexer.py`: cada tipo de token y casos borde (`>>` frente a `> >`, `<=`, comentarios y cadenas sin cerrar) | Diseño del lexer y demo con entradas válidas y con errores léxicos (3-4 min) |
| P3 | A4, A5; E2, E3 | Programas de `cases/` para las tres etapas y `test_cases.py`; programas del video; guion por minutos y control del tiempo | `test_cases.py` | Presentación del subconjunto y de la especificación de tokens (1-2 min) |
| P4 | O2; A3 | `symbols.py`; reglas S1, S2 y S5 en su sección de `semantic.py`; `docs/reglas_semanticas.md` junto con P5 | `test_symbols.py` y `test_semantic_scopes.py` | Tabla de símbolos y ámbitos, con demo de variables no declaradas y redeclaradas (1.5 min) |
| P5 | O2; A3 | `type_of()` y reglas S3, S4 y S9 en su sección de `semantic.py`; `docs/reglas_semanticas.md` junto con P4; edición del video | `test_semantic_types.py` | Reglas de tipos, con demo de errores de tipos (1.5 min) |

Tiempo total del video: unos 9 minutos y medio. Si algo se alarga, se recorta la demo del lexer, nunca la reflexión.

### Dependencias

- P1 crea el esqueleto de `semantic.py` primero; P4 y P5 trabajan sobre él.
- P4 entrega `SymbolTable` antes que sus reglas, porque P1 y P5 la usan. Mientras tanto, P1 y P5 pueden trabajar contra la API de la sección 9.
- El semántico no espera al lexer: sus pruebas usan `toks()` hasta que `tokenize()` exista.
- `analyze()` y `test_cases.py` sí necesitan el lexer de P2.
- P3 escribe los programas de `cases/` desde las secciones 4 y 9, sin esperar código.
- El video se graba cuando `uv run pytest` pasa completo en `main`.

### Pendientes del parser (P1)

El parser está completo: las 68 reglas de `cpp.gram` tienen su método y 141 pruebas en `tests/test_parser_units.py`. Queda corregir el docstring de `require_variable`, que todavía dice que la regla no cabe en LL(1) (la explicación correcta está en la sección 2). La recuperación en modo pánico solo se hace si sobra tiempo al final de la fase.

### Cierre de la Fase 1

1. Recorrido de módulos: cada autor explica su parte al grupo. Como el docente puede preguntar por cualquier línea, cada quien prepara 5 preguntas sobre un módulo que no es suyo.
2. Ensayo del video con cronómetro.
3. Grabación, edición y revisión del límite de 10 minutos.
4. Revisión final del README: instalación, uso y reflexión.
