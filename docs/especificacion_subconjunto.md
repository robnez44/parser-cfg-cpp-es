# Especificación del subconjunto de C++ para la Fase 1

Proyecto TLP02-2026, grupo: [nombre del grupo]

Integrantes: [nombres]

## Lenguaje elegido

Para la Fase 1 vamos a trabajar con un subconjunto de C++. El parser lo implementamos en Python como un analizador descendente recursivo sobre una gramática LL(1), y genera el árbol de análisis sintáctico de cada programa.

## Qué incluye

- Tipos `int`, `float`, `double`, `char`, `bool` y `string`. `void` como tipo de retorno de funciones.
- Declaración de variables, con inicialización opcional y varias variables en una misma línea.
- `if` / `else`, `while`, `do-while`, `for` y `switch` con `case` y `default`.
- Funciones con parámetros, llamadas a funciones y `return`.
- `break` y `continue`.
- Entrada y salida con `cin >>` y `cout <<`, incluido `endl`.
- Operadores aritméticos, de comparación, lógicos, de asignación (también los compuestos como `+=`) y `++` / `--`.
- Encabezado opcional con `#include <iostream>`, `#include <string>` y `using namespace std;`.

## Qué no incluye

Arreglos, punteros, referencias, estructuras y clases, el operador ternario, operadores de bits, conversiones de tipo, `const`, prototipos de funciones, nombres calificados con `std::` y el preprocesador en general.

## Decisiones de diseño

- Tomamos `string` como palabra reservada para simplificar, aunque en C++ es una clase de la biblioteca estándar.
- En un `if` anidado, el `else` se asocia al `if` más cercano, igual que en C++. Este es el único punto en que la gramática no es LL(1), y lo resolvemos de forma explícita.
- Para `cout <<` aceptamos expresiones aritméticas. Una comparación necesita paréntesis, como `cout << (a < b)`, igual que en C++ por la precedencia de `<<`. Para `cin >>` aceptamos solo variables.
- El análisis semántico queda fuera: no revisamos tipos ni si una variable fue declarada antes de usarse.

## Ejemplo de programa aceptado

```cpp
#include <iostream>
using namespace std;

int factorial(int n) {
    int r = 1;
    for (int i = 2; i <= n; i++) {
        r *= i;
    }
    return r;
}

int main() {
    int n;
    cin >> n;
    if (n < 0)
        cout << "Numero invalido" << endl;
    else
        cout << "Factorial: " << factorial(n) << endl;
    return 0;
}
```
