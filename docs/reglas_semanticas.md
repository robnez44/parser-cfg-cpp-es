# Reglas semánticas

Un programa puede ser sintácticamente correcto y aun así no tener sentido: usar una variable que nunca se declaró, o declarar dos veces el mismo nombre. La gramática no puede detectar esto porque es libre de contexto: para saber si `x` está declarada hay que mirar lo que apareció antes en el programa. Por eso se revisa en una etapa aparte, sobre el árbol que entrega el parser.

Este archivo lo escriben P4 (S1, S2 y S5) y P5 (S3, S4 y S9). P1 agrega S6, S7 y S8.

## Tabla de símbolos y ámbitos

La tabla de símbolos (`minicpp/symbols.py`) es una pila de diccionarios, uno por ámbito. Cada entrada guarda el nombre, la clase (`variable`, `parameter` o `function`), el tipo y la posición donde se declaró.

| Ámbito | Se abre en | Se cierra en |
|---|---|---|
| Global | Inicio del programa | Fin del programa |
| Función | Después de declarar el nombre de la función | Fin del cuerpo |
| Bloque | Cada `{ }` interno | Su `}` |
| `for` | El `for`, antes de su inicialización | Fin del cuerpo del `for` |
| `switch` | La `{` del `switch` (todos los `case` comparten el ámbito) | Su `}` |

- Los parámetros y el bloque principal del cuerpo comparten un ámbito, como en C++: `int f(int a) { int a; }` es un error.
- El nombre de la función se declara en el ámbito global **antes** de revisar el cuerpo, así una función puede llamarse a sí misma.
- Una función solo se puede llamar si está definida más arriba en el archivo (no hay prototipos).
- Un nombre de un ámbito interno puede tapar a uno externo (*shadowing*) mientras dure el ámbito interno.
- En `int x = x + 1;` el inicializador se revisa antes de declarar `x`, así que ese `x` no existe todavía (C++ lo acepta, pero el resultado es basura; aquí lo marcamos).

## S1: todo nombre usado está declarado antes

La búsqueda (`lookup`) va del ámbito más interno hacia afuera. Si no encuentra el nombre, hay error. Se revisan los nombres en expresiones, argumentos de llamadas y `cin >>`.

Válido:

```cpp
int main() {
    int total = 0;
    total = total + 1;
    return total;
}
```

Inválido (línea 2):

```cpp
int main() {
    total = 1;          // Error semántico en línea 2, columna 5: la variable 'total' no está declarada
    return 0;
}
```

Inválido (función definida después de usarse):

```cpp
int main() { return f(); }   // la función 'f' no está declarada
int f() { return 1; }
```

## S2: un nombre por ámbito

Al declarar, `declare` devuelve el símbolo anterior si el nombre ya estaba **en el mismo ámbito**. El error apunta a la segunda declaración e indica la línea de la primera. La primera declaración se conserva.

Válido (ámbitos distintos):

```cpp
int x = 1;
int main() {
    int x = 2;          // tapa a la global
    { int x = 3; }      // tapa a la anterior
    return x;
}
```

Inválido:

```cpp
int main() {
    int x = 1;
    int x = 2;          // Error semántico en línea 3, columna 9: 'x' ya fue declarada en este ámbito (línea 2)
    return 0;
}
```

Con otro tipo sigue siendo error: `int x; double x;`. Lo mismo para dos parámetros con el mismo nombre y para una función y una variable global con el mismo nombre.

## S5: una variable no se ve fuera de su bloque

No necesita código aparte: al cerrar el ámbito, sus nombres desaparecen de la tabla, y un uso posterior falla en S1 con el mismo mensaje (`la variable 'i' no está declarada`).

Válido:

```cpp
for (int i = 0; i < 3; i++) { }
for (int i = 0; i < 3; i++) { }     // otra i distinta
```

Inválido:

```cpp
int main() {
    for (int i = 0; i < 3; i++) { }
    i = 5;              // Error semántico en línea 3, columna 5: la variable 'i' no está declarada
    return 0;
}
```

Lo mismo ocurre con una variable declarada dentro de un `if`, un `while`, un bloque suelto o un `case` del `switch`, usada afuera.

## Cómo se implementó

- `minicpp/symbols.py`: `Symbol` y `SymbolTable` (`enter_scope`, `exit_scope`, `declare`, `lookup`). No conoce el árbol.
- `minicpp/semantic.py`, sección 2: métodos `visit_*` para `GlobalDecl`, `LocalDecl`, `Block`, `ForStmt`, `SwitchStmt`, `Primary` y `CinStmt`. Abren y cierran ámbitos y llaman a la tabla.
- Los errores se acumulan en una lista, no se lanzan, y se ordenan por línea.
- Pruebas: `tests/test_symbols.py` (la tabla sola) y `tests/test_semantic_scopes.py` (el analizador sobre programas pequeños).

## S6: llamadas a funciones

En una llamada `f(...)` se revisa que `f` sea una función y que reciba tantos argumentos como parámetros tiene. También se revisa el caso contrario: un nombre de función sin paréntesis no se puede usar como variable. Si el nombre no está declarado, solo se reporta S1, para no sumar un segundo error por la misma causa.

Válido:

```cpp
int suma(int a, int b) {
    return a + b;
}

int main() {
    return suma(1, suma(2, 3));
}
```

Inválido (cantidad de argumentos):

```cpp
int suma(int a, int b) {
    return a + b;
}

int main() {
    return suma(1, 2, 3);   // Error semántico en línea 6, columna 12: 'suma' espera 2 argumentos y recibió 3
}
```

Inválido (el nombre no es una función):

```cpp
int main() {
    int x = 1;
    x();                    // Error semántico en línea 3, columna 5: 'x' no es una función
    return 0;
}
```

Inválido (una función usada como variable):

```cpp
int cero() {
    return 0;
}

int main() {
    int y = cero;           // Error semántico en línea 6, columna 13: 'cero' es una función, no una variable
    return y;
}
```

- Una variable local con el mismo nombre que una función la tapa, como en C++: después de `int suma = 1;`, la llamada `suma(1, 2)` da "'suma' no es una función".
- Con un parámetro el mensaje dice "1 argumento", en singular.
- Falta revisar que el tipo de cada argumento sea compatible con su parámetro. Se agrega cuando exista `type_of()` (S3 y S4).
- `cin >> cero;` con `cero` función no se detecta, porque los nombres de `cin` se revisan aparte, en S1.

## S7: `return` según el tipo de la función

Se revisa cada `return` y, al terminar el cuerpo, si la función tenía alguno:

| Caso | Resultado | En C++ (g++) |
|---|---|---|
| `void` con `return 5;` | Error | Error |
| Con tipo y `return;` | Error, incluido `main` | Error |
| Con tipo y ningún `return` | Error en la `}` del cuerpo | Advertencia: `no return statement in function returning non-void` |
| `main` sin ningún `return` | Válido, devuelve 0 | Válido |

Válido:

```cpp
void saludar() {
    cout << "hola" << endl;
}

int main() {
    saludar();
}
```

Inválido (`void` con valor):

```cpp
void saludar() {
    return 1;           // Error semántico en línea 2, columna 5: la función 'saludar' es void y no puede devolver un valor
}
```

Inválido (`return` sin valor):

```cpp
int doble(int x) {
    return;             // Error semántico en línea 2, columna 5: la función 'doble' debe devolver un valor de tipo int
}
```

Inválido (ningún `return`):

```cpp
int suma(int a, int b) {
    int c = a + b;
}                       // Error semántico en línea 3, columna 1: la función 'suma' debe devolver un valor de tipo int
```

**Limitación.** No se revisa que todos los caminos devuelvan un valor. Esto pasa sin error:

```cpp
int signo(int x) {
    if (x > 0) return 1;
}
```

g++ lo compila con la advertencia `control reaches end of non-void function`. Para detectarlo hay que seguir cada camino de ejecución (las dos ramas del `if`, ciclos que pueden no ejecutarse, el `default` del `switch`), y eso ya es análisis de flujo de control, que el enunciado no pide.

Falta revisar que el valor devuelto sea compatible con el tipo de la función (`return "hola";` en una función `int`). Se agrega cuando exista `type_of()`.

## S8: `break` y `continue`

`break` solo puede ir dentro de un ciclo (`while`, `do-while`, `for`) o de un `switch`. `continue` solo dentro de un ciclo. La regla depende de dónde está escrito el `break`, no de desde dónde se llama la función que lo contiene.

Válido (`continue` dentro de un `switch` que está dentro de un ciclo):

```cpp
int main() {
    int op = 1;
    while (true) {
        switch (op) {
            case 1: continue;
            default: break;
        }
        break;
    }
    return 0;
}
```

Inválido (`break` fuera de un ciclo):

```cpp
int main() {
    break;              // Error semántico en línea 2, columna 5: break solo puede ir dentro de un ciclo o de un switch
    return 0;
}
```

Inválido (`continue` en un `switch` sin ciclo):

```cpp
int main() {
    int op = 1;
    switch (op) {
        case 1: continue;   // Error semántico en línea 4, columna 17: continue solo puede ir dentro de un ciclo
    }
    return 0;
}
```

Una CFG sí podría expresar esta regla con tres versiones de cada no terminal de sentencia: fuera de todo, dentro de un `switch` y dentro de un ciclo. La parte de sentencias de la gramática se triplicaría. Por eso la revisamos aquí, como hacen los compiladores.

## Cómo se implementaron S6, S7 y S8

- `minicpp/semantic.py`, sección 4: `visit_break_stmt` y `visit_continue_stmt` (S8); `check_call` y `call_arguments` (S6); `enter_function`, `exit_function` y `visit_return_stmt` (S7).
- S8 usa dos contadores, `loop_depth` y `switch_depth`, que suben al entrar a un ciclo o a un `switch` y bajan al salir. Se actualizan en `visit()` (sección 1) y no en `visit_for_stmt` ni en `visit_switch_stmt`, para no reemplazar esos métodos de la sección 2.
- S6 y S7 se enganchan en dos métodos de la sección 2: `visit_primary` llama a `check_call` cuando el nombre existe y es una llamada, y `declare_function` llama a `enter_function` antes del cuerpo y a `exit_function` después.
- Pruebas: `tests/test_semantic_functions.py`, con los prefijos `test_s6_`, `test_s7_` y `test_s8_`.
