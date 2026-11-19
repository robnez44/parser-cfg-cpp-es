# parser-cfg-cpp-es

Proyecto de Teoría de Lenguajes de Programación, UCA, ciclo 02-2026.

En la Fase 1 implementamos en Python las tres primeras etapas de un compilador para un subconjunto de C++: el lexer, el parser y el analizador semántico. Un programa pasa por las tres en ese orden, y si una falla, las siguientes no corren.

| Etapa | Archivo | Qué revisa | Nivel en la jerarquía de Chomsky |
|---|---|---|---|
| Lexer | `minicpp/lexer.py` | Que el texto se pueda dividir en tokens válidos | Regular (tipo 3) |
| Parser | `minicpp/parser.py` | Que los tokens sigan la gramática de `grammars/cpp.gram` | Libre de contexto (tipo 2) |
| Analizador semántico | `minicpp/semantic.py` | Declaraciones, ámbitos y tipos, que una gramática libre de contexto no puede revisar | Sensible al contexto (tipo 1) |

El enunciado llama `semantico.py` al analizador semántico. Nosotros lo dejamos como `semantic.py` porque todo el código está en inglés.

El subconjunto de C++ está descrito en [docs/especificacion_subconjunto.md](docs/especificacion_subconjunto.md), y la definición formal de los tokens, con sus expresiones regulares y autómatas, en [docs/tokens.md](docs/tokens.md). Las decisiones del grupo y la forma en que se conectan los módulos están en [CONTRATO.md](CONTRATO.md).

## Instalación

Usamos [uv](https://docs.astral.sh/uv/) para el entorno y las dependencias.

1. Instalar uv, una sola vez:

   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - Mac o Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

2. Clonar el repositorio y crear el entorno:

   ```
   git clone https://github.com/robnez44/parser-cfg-cpp-es.git
   cd parser-cfg-cpp-es
   uv sync
   ```

   `uv sync` instala Python 3.12 si hace falta, junto con las versiones exactas de las dependencias que están en `uv.lock`.

Si no tienen uv, también funciona con pip dentro de un entorno virtual de Python 3.12: `pip install -r requirements.txt`.

## Uso

```
uv run python -m minicpp archivo.cpp
```

Si el programa pasa las tres etapas, imprime `Programa válido`. Si no, imprime los errores con su línea y columna:

```
Error léxico en línea 3, columna 7: carácter no reconocido '@'
Error sintáctico en línea 5, columna 12: se esperaba SEMICOLON y se encontró RBRACE ('}')
Error semántico en línea 8, columna 5: la variable 'total' no está declarada
```

Un error léxico o sintáctico detiene el análisis en el primero que aparece. Los errores semánticos se muestran todos, ordenados por línea.

Opciones:

| Opción | Qué hace |
|---|---|
| `--tokens` | Muestra la tabla de tokens que produce el lexer: línea, columna, tipo y lexema |
| `--tree` | Dibuja el árbol de análisis sintáctico |
| `--view window` | Con `--tree`, abre el árbol en una ventana de NLTK. Si la ventana no abre, lo dibuja en la terminal |
| `--view outline` | Con `--tree`, muestra un nodo por línea; sirve para programas largos que no caben a lo ancho |
| `--compact` | Con `--tree`, oculta las ramas que solo derivan ε. El árbol no cambia, solo el dibujo |

Por ejemplo, para ver los tokens y el árbol de un programa:

```
uv run python -m minicpp archivo.cpp --tokens --tree --compact
```

El comando termina con código 0 si el programa es válido, 1 si tiene errores y 2 si no pudo leer el archivo.

Las etapas también se pueden usar desde Python:

```python
from minicpp import analyze
from minicpp.lexer import tokenize

tokens = tokenize("int x = 5;")
tree, semantic_errors = analyze("int main() { return 0; }")
```

## Pruebas

| Para | Comando |
|---|---|
| Correr todas las pruebas | `uv run pytest` |
| Correr las pruebas de un módulo | `uv run pytest tests/test_lexer.py` |
| Verificar que la gramática es LL(1) | `uv run python -m verifier grammars/cpp.gram` |

Los programas de prueba completos están en `cases/valid/` y `cases/invalid/`. La primera línea de cada caso inválido dice en qué etapa y en qué línea debe fallar.

## Estructura

| Carpeta | Contenido |
|---|---|
| `minicpp/` | Lexer, parser, analizador semántico, tabla de símbolos, errores, dibujo del árbol y línea de comandos |
| `verifier/` | Verificador LL(1): calcula FIRST, FOLLOW y la tabla de la gramática, y reporta los conflictos |
| `grammars/` | Gramática del subconjunto (`cpp.gram`, y `cpp.bnf` en la notación de clase) y gramáticas de prueba del verificador |
| `cases/` | Programas válidos e inválidos para probar las tres etapas |
| `tests/` | Pruebas con pytest |
| `docs/` | Especificación del subconjunto, de los tokens y de las reglas semánticas |
| `video/` | Guion y programas del video |
