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
