# parser-cfg-cpp-es

> **Video de la Fase 1:** https://drive.google.com/file/d/10WEc90ypi8l6zpKv5QwHnCzPubSXIwIk/view?usp=sharing

Proyecto de Teoría de Lenguajes de Programación, UCA, ciclo 02-2026.

En la Fase 1 implementamos en Python las tres primeras etapas de un compilador para un subconjunto de C++: el lexer, el parser y el analizador semántico. Un programa pasa por las tres en ese orden, y si una falla, las siguientes no corren.

| Etapa | Archivo | Qué revisa | Nivel en la jerarquía de Chomsky |
|---|---|---|---|
| Lexer | `minicpp/lexer.py` | Que el texto se pueda dividir en tokens válidos | Regular (tipo 3) |
| Parser | `minicpp/parser.py` | Que los tokens sigan la gramática de `grammars/cpp.gram` | Libre de contexto (tipo 2) |
| Analizador semántico | `minicpp/semantic.py` | Declaraciones, ámbitos y tipos, que una gramática libre de contexto no puede revisar | Sensible al contexto (tipo 1) |

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

## Reflexión: lo que una gramática libre de contexto no puede revisar

### Por qué hace falta una tercera etapa

El parser acepta este programa sin errores:

```cpp
int suma(int a, int b) {
    return a + b;
}

int main() {
    total = suma(1, 2, 3);
}
```

Cada sentencia tiene la forma correcta, así que la gramática no tiene nada que objetar. Pero `total` nunca se declaró y `suma` recibe tres argumentos cuando espera dos. Para notarlo hay que recordar lo que apareció antes en el programa, y una gramática libre de contexto no puede hacerlo: cada producción se aplica igual sin importar lo que hay alrededor. Por eso el analizador semántico corre después del parser, sobre su árbol, y guarda lo declarado en una tabla de símbolos.

### Lo que no cabe en una gramática libre de contexto

Para mostrar que una regla no cabe en una CFG, la reducimos a un lenguaje formal que ya se sabe que no es libre de contexto. Los dos casos clásicos vienen de Aho et al., *Compiladores*, sección 4.3.5.

**Declarar antes de usar (S1, S2 y S5).** Si quitamos todo lo demás, un programa que declara una variable y después la usa tiene la forma $wcw$: la primera $w$ es el nombre en la declaración, $c$ es lo que hay en medio y la segunda $w$ es el uso, que tiene que ser exactamente el mismo nombre. El lenguaje $\{wcw \mid w \in \{a, b\}^*\}$ no es libre de contexto. La intuición está en la pila: el parser puede guardar $w$ mientras la lee, pero al sacarla la recibe al revés. Con eso puede comparar $w$ con su reverso, como en un palíndromo, pero no con $w$ en el mismo orden. Y como los nombres pueden tener cualquier largo, tampoco se resuelve escribiendo una regla por cada nombre posible. La demostración con el lema de bombeo, para $\{ww\}$, que es el mismo caso sin el separador, está en [docs/informe/p4_analisis_formal.md](docs/informe/p4_analisis_formal.md), sección 3.3.

**Cantidad de argumentos (S6).** Con dos funciones, una de $n$ parámetros y otra de $m$, y después una llamada a cada una:

```cpp
int f(int a, int b) { return a; }    // n = 2
int g(int x) { return x; }           // m = 1

int main() {
    return f(1, 2) + g(3);
}
```

el programa tiene la forma $a^n b^m c^n d^m$: los parámetros de `f`, los de `g`, los argumentos de `f` y los de `g`. Las parejas son el primer bloque con el tercero y el segundo con el cuarto, o sea, las dependencias se cruzan. Una pila maneja dependencias anidadas, como en $a^n b^m c^m d^n$, donde lo último que entró es lo primero que se compara, pero no cruzadas. $\{a^n b^m c^n d^m \mid n, m \geq 1\}$ no es libre de contexto. Con las letras renombradas es el lenguaje $\{a^n b^m a^n b^m\}$, que el mismo documento demuestra que no es libre de contexto.

**Tipos (S3, S4, S9 y el valor de un `return`).** Para saber si `x + "hola"` es válido hay que saber de qué tipo es `x`, y eso lo dice una declaración que puede estar en cualquier parte más arriba. Es el mismo problema que declarar antes de usar, con un dato más: además de encontrar el nombre, hay que traer su tipo. La gramática solo ve `ID PLUS STRING_LITERAL`, que es una expresión válida sea cual sea el tipo de `x`.

| Regla | Lenguaje formal | Por qué no alcanza una pila |
|---|---|---|
| Declarar antes de usar (S1, S2 y S5) | $\{wcw\}$ | Hay que comparar dos copias del mismo nombre en el mismo orden |
| Cantidad de argumentos (S6) | $\{a^n b^m c^n d^m\}$ | Las dependencias se cruzan |
| Tipos (S3, S4, S7 y S9) | El mismo caso que $\{wcw\}$ | El tipo viene de una declaración que puede estar lejos |

### Lo que sí cabe en una CFG, pero no conviene

**`break` y `continue` fuera de lugar (S8).** Esta regla sí se puede escribir en una gramática libre de contexto. Lo único que hay que saber es en cuál de tres situaciones está una sentencia: fuera de todo, dentro de un `switch` o dentro de un ciclo. Como son finitas, basta con tener tres versiones de cada no terminal de sentencia (`Stmt`, `StmtInSwitch`, `StmtInLoop`, y lo mismo para `Block`, `IfStmt`, `StmtList` y los demás) y permitir `break` y `continue` solo en las versiones que corresponden. La gramática seguiría siendo de tipo 2, pero la parte de sentencias se triplicaría y cada cambio habría que hacerlo tres veces. Por eso los compiladores lo revisan en el análisis semántico, y nosotros también.

Con S7 pasa algo parecido. Que una función `void` no devuelva un valor, o que una función con tipo tenga al menos un `return`, depende de información finita que está en la misma producción de la función (su tipo de retorno), así que también se podría escribir duplicando no terminales.

La diferencia con la sección anterior está en cuánta información hay que recordar. Si es una cantidad finita (estoy en un ciclo o no, la función es `void` o no), una CFG la puede llevar en sus no terminales, aunque la gramática crezca. Si no tiene límite (un nombre de cualquier largo, una cantidad cualquiera de parámetros), ninguna CFG alcanza.

### Lo que es un límite de LL(1), no de las CFG

Dos cosas del parser parecen límites de la gramática, pero en realidad vienen de decidir con un solo token de adelanto:

- **El destino de una asignación.** El lado izquierdo de `=`, `+=`, `++` o `--` tiene que ser una variable. Una CFG lo expresa sin problema: `AssignExpr -> ID AssignOp AssignExpr | OrExpr`. El problema es que las dos alternativas pueden empezar con `ID` (`a = 1` y `a + 1`), y con un solo token el parser no sabe cuál elegir. Haría falta mirar dos tokens (LL(2)) o duplicar toda la cadena de expresiones. Por eso el parser lo revisa en el código (`require_variable`) y lanza un error sintáctico.
- **El `else` colgante.** En `if (a) if (b) x = 1; else x = 2;`, el `else` puede pertenecer a cualquiera de los dos `if`: la gramática es ambigua. El verificador lo muestra como el único conflicto de la tabla, `M[ElsePart, ELSE]`. Lo resolvemos igual que C++: el `else` va con el `if` más cercano.

Ninguno de los dos saca al lenguaje del tipo 2. Son consecuencia de usar un parser LL(1), y se ven como conflictos en la tabla, no como reglas imposibles de escribir.

### Lo que no cubrimos

**Que todos los caminos devuelvan un valor.** El analizador revisa que una función con tipo tenga al menos un `return`, pero no que todos los caminos terminen en uno. Esto pasa sin error:

```cpp
int signo(int x) {
    if (x > 0) return 1;
}
```

g++ lo compila con la advertencia `control reaches end of non-void function`. Para detectarlo hay que seguir cada camino de ejecución: las dos ramas del `if`, los ciclos que pueden no ejecutarse, el `default` del `switch`. Eso ya no es un problema de contexto sino de flujo de control. Decidirlo con exactitud es imposible en general: si la condición es `if (f(x))`, saber si esa rama se ejecuta depende de lo que devuelva `f`, y eso en general se reduce al problema de la parada. Lo que hacen los compiladores es una aproximación conservadora: suponen que cualquier rama puede ejecutarse. Esa aproximación sí se puede implementar, pero quedó fuera del alcance de esta fase.

### Simplificaciones respecto a C++

En algunos casos nos apartamos de C++ a propósito, para que el subconjunto sea más simple de analizar y de explicar:

| Caso | C++ | Nosotros |
|---|---|---|
| `string` | Es una clase de la biblioteca estándar (`std::string`), no un tipo primitivo | Es una palabra reservada, igual que `int` o `double` |
| `string` con un número (`s = 65;`) | Algunos casos compilan: `s = 65` guarda el carácter `'A'` | Siempre es error |
| Función con tipo sin ningún `return` | Advertencia de g++ | Error |
| `int x = x + 1;` | Compila, aunque `x` tiene basura | Error: `x` todavía no está declarada en su propio inicializador |
| `main` sin `return` | Válido, devuelve 0 | Igual que C++ |

Tratar `string` como clase nos obligaría a manejar sus métodos y la sobrecarga de operadores, que están fuera del subconjunto. Los demás casos son más estrictos que C++: preferimos marcar como error algo que en C++ compila pero casi siempre es un descuido.

### Cada etapa con la memoria que necesita

Las tres etapas siguen la jerarquía de Chomsky, y se nota en cuánta memoria usa cada una:

| Etapa | Memoria | Nivel |
|---|---|---|
| Lexer | Solo el estado del autómata: no recuerda nada de lo que ya leyó | Regular (tipo 3) |
| Parser | Una pila: la pila de llamadas del parser descendente recursivo | Libre de contexto (tipo 2) |
| Analizador semántico | La tabla de símbolos, con todo lo declarado hasta ese punto | Sensible al contexto (tipo 1) |

Para el analizador semántico no escribimos una gramática de tipo 1. Hacemos lo que hacen los compiladores reales: la gramática libre de contexto da la estructura del programa, y un recorrido del árbol con una tabla de símbolos revisa lo que la gramática no puede. Es la idea de las definiciones dirigidas por la sintaxis (Aho et al., capítulo 5). Aun así, el nivel sigue siendo el tipo 1: la tabla nunca guarda más de lo que ya está escrito en el programa, así que la memoria que usa está acotada por el largo de la entrada. Esa es justo la restricción de un autómata linealmente acotado, el que reconoce los lenguajes sensibles al contexto.
