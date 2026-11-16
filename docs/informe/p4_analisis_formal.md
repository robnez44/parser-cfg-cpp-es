# Jerarquía de Chomsky y límites de las gramáticas libres de contexto

Sección del informe a cargo de P4. Cubre O1 (verificación de la gramática), O3 y O4, y la actividad A5.

## 1. Marco teórico: la jerarquía de Chomsky

Chomsky clasifica las gramáticas por la forma de sus producciones. Cada tipo genera una clase de lenguajes y tiene un autómata que lo reconoce.

| Tipo | Forma de las producciones | Lenguajes | Autómata |
|---|---|---|---|
| 0 | α → β, con α ≠ ε | Recursivamente enumerables | Máquina de Turing |
| 1 | αAβ → αγβ, con γ ≠ ε (equivale a gramáticas no contractivas) | Sensibles al contexto | Autómata linealmente acotado |
| 2 | A → γ | Libres de contexto (CFL) | Autómata de pila |
| 3 | A → aB, A → a, A → ε | Regulares | AFD / AFN |

Las clases quedan anidadas: regulares ⊂ libres de contexto ⊂ sensibles al contexto ⊂ recursivamente enumerables. Un lenguaje se clasifica por la gramática más restrictiva que lo genera, así que una gramática de tipo 2 puede generar un lenguaje regular.

En este proyecto cada nivel aparece en un lugar concreto:

| Pieza del proyecto | Nivel | Por qué |
|---|---|---|
| Lexer (identificadores, números, cadenas, comentarios) | Tipo 3 | Cada categoría léxica se describe con una expresión regular |
| Parser del subconjunto de C++ | Tipo 2 | La anidación de paréntesis, bloques y expresiones necesita una pila |
| Declarar antes de usar, compatibilidad de tipos | Tipo 1 | Depende de lo declarado antes en el programa (ver sección 4) |

Dentro de las gramáticas de tipo 2, el proyecto usa la subclase **LL(1)**: se decide qué producción aplicar mirando un solo token de adelanto. Los lenguajes LL(1) son un subconjunto de los libres de contexto deterministas, y toda gramática LL(1) es no ambigua. De ahí sale la pregunta de esta sección: cuando el verificador reporta un conflicto, ¿el problema es de la gramática, de la ambigüedad o del lenguaje mismo?

## 2. El verificador LL(1) y qué demuestra sobre la gramática de C++

El verificador (`uv run python -m verifier`) calcula FIRST, FOLLOW y la tabla M[A, a]. Una gramática es LL(1) exactamente cuando ninguna celda de la tabla tiene más de una producción.

Resultado sobre `grammars/cpp.gram`:

| Dato | Valor |
|---|---|
| No terminales | 68 |
| Producciones | 144 |
| Terminales (sin contar `$`) | 63 |
| Conflictos LL(1) | 1 |
| Recursión izquierda | ninguna |
| Errores de la gramática (símbolos sin regla, no terminales improductivos) | ninguno |

El único conflicto es:

```
Conflict at M[ElsePart, ELSE]:
  ElsePart -> ELSE Stmt
  ElsePart -> ε
```

**Por qué ocurre.** La única regla donde aparece `ElsePart` es `IfStmt -> IF LPAREN Expr RPAREN Stmt ElsePart`, y `IfStmt` es una alternativa de `Stmt`. Entonces `ELSE` está en FIRST(ElsePart) por la regla `ElsePart -> ELSE Stmt`, y también está en FOLLOW(ElsePart): dentro de un `if` anidado, el `Stmt` del `if` externo va seguido de un `ElsePart`, y ese `ElsePart` puede empezar con `ELSE`. Con `ELSE` como siguiente token, la tabla no sabe si elegir `ELSE Stmt` o la producción vacía.

**Qué clase de problema es.** Es un conflicto **FIRST/FOLLOW** causado por una **ambigüedad de la gramática**: la cadena `if (a) if (b) x; else y;` tiene dos árboles de derivación, según a qué `if` pertenezca el `else`. Con un solo token de adelanto no hay información para decidir. Existe una gramática no ambigua para el mismo lenguaje (sentencias emparejadas y abiertas), pero sus alternativas comparten el prefijo `if ( Expr )`, lo que produce conflictos FIRST/FIRST en `Stmt` y la saca del esquema LL(1) directo. Por eso el proyecto mantiene la gramática LL(1) y resuelve la ambigüedad con una regla de desempate, igual que C++: el `else` se asocia al `if` más cercano, es decir, el parser elige `ElsePart -> ELSE Stmt` cuando ve `ELSE`. El archivo `cpp.gram` declara el conflicto como aceptado, y el verificador lo distingue de cualquier otro conflicto que aparezca por error.

Sobre las otras dos clases de conflicto que sí se corrigen con transformaciones de la gramática:

- **Recursión izquierda** (`E -> E + T`): produce conflictos FIRST/FIRST (la alternativa recursiva y la que le sigue empiezan con los mismos tokens) y se elimina con el esquema `E -> T E'`, `E' -> + T E' | ε`. El verificador la detecta por adelantado, incluso la indirecta.
- **Prefijo común** (`S -> a b | a c`): produce un conflicto FIRST/FIRST y se corrige con factorización por la izquierda (`S -> a S'`, `S' -> b | c`).

Ambas son propiedades de **cómo se escribió la gramática**, no del lenguaje: el mismo lenguaje tiene una gramática LL(1) equivalente. Sirven de contraste con los fenómenos de las secciones 3 y 4.

## 3. Cómo se clasifica una falla de la gramática del español

Cuando una extensión de P5 falla, hay cuatro explicaciones posibles, y el informe debe decir cuál es la correcta para cada caso:

| Causa | ¿Es un problema del lenguaje? | Cómo se ve en el verificador | Remedio |
|---|---|---|---|
| A. Mala escritura de la gramática (recursión izquierda, prefijo común) | No | Conflicto FIRST/FIRST | Transformar la gramática |
| B. Ambigüedad estructural | Sí, pero sigue siendo libre de contexto | Conflicto FIRST/FOLLOW | No tiene remedio sintáctico; se elige una lectura o se usa semántica |
| C. Concordancia con rasgos finitos | No (sigue siendo tipo 2), pero la gramática crece | No aparece como conflicto: aparece como explosión de reglas | Duplicar no terminales por rasgo |
| D. Dependencias cruzadas sin límite | **Sí: el lenguaje sale del tipo 2** | Ninguna gramática tipo 2 lo resuelve | Pasar a tipo 1 o a formalismos con más poder |

### 3.1 Ambigüedad estructural (causa B): un ejemplo real

La gramática mínima `grammars/test_grammars/spanish_pp_attachment.gram` modela frases preposicionales:

```
NounPhrase -> DET NOUN NounTail
NounTail   -> PREP NounPhrase | ε
VerbPhrase -> VERB NounPhrase VerbTail
VerbTail   -> PREP NounPhrase | ε
```

La oración «vi al hombre con el telescopio» tiene dos análisis: «con el telescopio» modifica a «hombre» (`NounTail`) o a «vi» (`VerbTail`). El verificador lo reporta con la regla y el token exactos:

```
Conflict at M[NounTail, PREP]:
  NounTail -> PREP NounPhrase
  NounTail -> ε
```

`PREP` está en FIRST(NounTail) y también en FOLLOW(NounTail), porque después del objeto directo puede venir el `VerbTail`, que empieza con `PREP`. Es la misma estructura que el `else` colgante, pero en lenguaje natural no existe una convención que elija la lectura: la decisión depende del significado, no de la sintaxis. Esta es una diferencia clave con los lenguajes de programación, que se diseñan para tener una sola lectura.

### 3.2 Concordancia de género y número (causa C): cabe en tipo 2, pero cuesta

El género (masculino, femenino) y el número (singular, plural) toman un número **finito** de valores. Por eso una CFG puede capturar la concordancia sustantivo-adjetivo y sujeto-verbo duplicando los no terminales por rasgo:

```
NP_ms -> DET_ms NOUN_ms ADJ_ms        NP_fp -> DET_fp NOUN_fp ADJ_fp
```

Con 2 géneros y 2 números hay 4 versiones de cada no terminal con rasgos, y cada rasgo nuevo multiplica ese número. La gramática sigue siendo de tipo 2, así que **la concordancia por sí sola no es el punto donde falla la CFG**: falla la mantenibilidad. Lo mismo vale para la concordancia sujeto-verbo a distancia, incluso con una subordinada en medio, porque el rasgo se puede propagar por los no terminales sin necesidad de recordar nada ilimitado.

### 3.3 Dependencias cruzadas (causa D): el lenguaje sale del tipo 2

El fenómeno que sí excede las CFG es el de las construcciones con «respectivamente»: «Ana, Luis y sus hermanos son alta, simpático e inteligentes, respectivamente». El primer sujeto se empareja con el primer predicado, el segundo con el segundo y así sucesivamente. Las dependencias **se cruzan**, a diferencia de las dependencias anidadas (a b b a), que una pila sí maneja.

**Formalización mínima.** Sea Σ = {a, b}, donde a es un sujeto singular y b uno plural, y sea T = {A, B}, donde A es un predicado singular y B uno plural. Sea L el conjunto de oraciones con n sujetos seguidos de n predicados en las que el i-ésimo predicado concuerda en número con el i-ésimo sujeto:

L = { w · h(w) | w ∈ {a, b}⁺ }, con h(a) = A y h(b) = B.

L es una copia del lenguaje { ww } con las letras de la segunda mitad renombradas.

**Demostración de que L no es libre de contexto.**

1. Los lenguajes libres de contexto son cerrados bajo homomorfismo. Con g(A) = a y g(B) = b, si L fuera libre de contexto, g(L) = { ww | w ∈ {a, b}⁺ } también lo sería.
2. Los libres de contexto son cerrados bajo intersección con un lenguaje regular. Intersectemos con el regular a⁺b⁺a⁺b⁺: una cadena ww pertenece a esa forma solo si w = aⁿbᵐ con n, m ≥ 1, y el resultado es L′ = { aⁿbᵐaⁿbᵐ | n, m ≥ 1 }.
3. L′ no es libre de contexto, por el lema de bombeo. Sea p la longitud de bombeo y tomemos z = aᵖbᵖaᵖbᵖ = uvwxy, con |vwx| ≤ p y |vx| ≥ 1.
    - Si v y x caen dentro de un solo bloque, bombear cambia la cantidad de letras de ese bloque y no la de su pareja (el primer bloque con el tercero, el segundo con el cuarto): la cadena sale de L′.
    - Si vwx cruza dos bloques contiguos, o bien v o x contiene letras distintas (y al bombear se rompe la forma a⁺b⁺a⁺b⁺), o bien v y x viven en bloques distintos (y se rompe la igualdad de cantidades con la pareja de alguno).
    - En todos los casos uv²wx²y ∉ L′.

Luego L′ no es libre de contexto. Por (2), { ww } tampoco, y por (1), L tampoco.

**Alcance del argumento.** Es una idealización: supone un número **ilimitado** de pares. Para un n máximo fijo el lenguaje es finito, y todo lenguaje finito es regular, así que existe una gramática (enorme) que lo cubre. La conclusión correcta para el informe es: *para cada n hace falta un conjunto distinto de reglas, y ninguna gramática de tipo 2 cubre todos los n a la vez*. Este tipo de argumento es el que se usó con las dependencias cruzadas del alemán suizo (Shieber, 1985) para sostener que el lenguaje natural no es libre de contexto en general.

**Relación con la jerarquía.** { ww } es un lenguaje sensible al contexto (tipo 1) y no libre de contexto. Lo mismo ocurre con { aⁿbⁿcⁿ }: ambos exigen comparar varias cantidades a la vez, cosa que una sola pila no puede hacer.

## 4. Límites de contexto dentro del propio subconjunto de C++

C++ completo tampoco es libre de contexto, por dos razones que se prueban igual que en la sección 3.3:

- La sentencia `a * b;` es una declaración de puntero si `a` es un tipo y una multiplicación si `a` es una variable. La gramática sola no lo decide.
- «Declarar antes de usar» exige que el identificador usado sea **idéntico** al declarado, sea cual sea su longitud. Intersectado con el lenguaje regular `int w1; w2 = 1;`, queda esencialmente { ww }, que no es libre de contexto.

El subconjunto del proyecto deja estas reglas **fuera del parser**: no hace análisis semántico, así que no revisa tipos ni declaraciones. Es una decisión consciente de diseño y se declara en `docs/especificacion_subconjunto.md`.

**Nota sobre el lado izquierdo de una asignación.** `CONTRATO.md` presenta como «restricción de contexto» la revisión de que el lado izquierdo de `=`, `+=` y el operando de `++` sea una variable. Conviene corregir esa etiqueta en el informe: exigir que el lado izquierdo sea un identificador **sí se puede escribir con una CFG** (por ejemplo, `AssignExpr -> ID AssignOp AssignExpr | OrExpr`). Lo que se pierde al hacerlo es la propiedad **LL(1)**, porque `ID` pasa a ser prefijo común de dos alternativas; es decir, el límite es el de LL(1) con un solo token de adelanto, no el de las gramáticas libres de contexto. Esta distinción es justo la de la sección 3: un conflicto LL(1) frente a un fenómeno que no es libre de contexto.

## 5. Cómo se reproduce el análisis

```
uv run python -m verifier grammars/cpp.gram                       # FIRST, FOLLOW, tabla y conflictos
uv run python -m verifier grammars/cpp.gram --conflicts           # solo los conflictos y el resumen
uv run python -m verifier grammars/cpp.gram --table --table-format grid   # tabla en Markdown
uv run python -m verifier grammars/cpp.gram --class-notation -o grammars/cpp.bnf
uv run python -m verifier grammars/spanish/step1_svo.gram --conflicts     # por cada paso del español (P5)
uv run pytest tests/test_verifier.py
```

Para cada intento de extensión al español, P5 y P4 llenan una fila como esta, que es la evidencia de A5:

| Paso | Fenómeno | Regla y token del conflicto | Tipo de conflicto | Causa (A, B, C o D) | Nivel de Chomsky |
|---|---|---|---|---|---|
| (ejemplo) frases preposicionales | Adjunción de «con el telescopio» | `M[NounTail, PREP]` | FIRST/FOLLOW | B: ambigüedad estructural | Tipo 2, no LL(1) |

Las filas de los pasos reales (SVO, concordancia, subordinada, modificadores, «respectivamente») se llenan con la salida del verificador sobre `grammars/spanish/`, cuando P5 tenga esos archivos.

## Referencias

- Hopcroft, J., Motwani, R. y Ullman, J. *Introducción a la teoría de autómatas, lenguajes y computación*. Capítulos 4 (lema de bombeo y cerraduras de los regulares), 5 (gramáticas y ambigüedad) y 7 (lema de bombeo y cerraduras de los libres de contexto).
- Aho, A., Lam, M., Sethi, R. y Ullman, J. *Compiladores: principios, técnicas y herramientas*. Sección 4.4 (análisis sintáctico descendente, FIRST, FOLLOW y gramáticas LL(1)).
- Chomsky, N. (1956). *Three models for the description of language*. IRE Transactions on Information Theory.
- Shieber, S. (1985). *Evidence against the context-freeness of natural language*. Linguistics and Philosophy, 8.
