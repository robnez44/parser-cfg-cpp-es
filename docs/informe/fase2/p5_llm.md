# Comportamiento del LLM frente a las reglas

Sección del informe a cargo de P5. Cubre O3 y la actividad A6.

## 1. Pregunta

Queremos saber si un LLM sigue una gramática formal cuando se la damos en el prompt, o si termina guiándose por lo que ya sabe del español. Para eso le pasamos `es.gram` y el lexicón, le pedimos que acepte o rechace cada oración del set y que, si la acepta, escriba el árbol de derivación. Después revisamos ese árbol con un programa, sin confiar en lo que el modelo dice de sí mismo.

## 2. Montaje del experimento

Usamos Claude Haiku 5.5 (`claude-haiku-5-5`) por la API de Anthropic. El contrato pedía temperatura 0, pero este modelo ya no acepta el parámetro `temperature`: cualquier valor devuelve un error 400. En lugar de fijar la temperatura, repetimos cada oración tres veces y nos quedamos con la respuesta de la mayoría. Así también medimos qué tan estable es el modelo: si en las tres repeticiones no dice lo mismo, lo contamos aparte. Apagamos el razonamiento interno del modelo (`thinking: disabled`) para que todas las llamadas trabajen igual. El identificador del modelo, la fecha, el prompt completo y la respuesta cruda de cada llamada quedan en `logs/llm/`.

Hay dos prompts, en `prompts/`:

- `zero_shot.txt`: las 35 producciones de `es.gram`, el lexicón agrupado por tipo de token, los pasos para analizar y el formato de la respuesta. No tiene ningún ejemplo resuelto.
- `few_shot.txt`: el mismo texto con cinco ejemplos resueltos que no están en el set. Tres se aceptan (una oración con punto, una con adjetivo, adverbio y frase preposicional, y una con la frase preposicional en el sujeto) y dos se rechazan (`el niña come` por concordancia y `el perro que corre duerme` por una palabra fuera del vocabulario).

En ningún prompt le dijimos al modelo a dónde pegar una frase preposicional ambigua. `es.gram` permite las dos lecturas de `el maestro lee la carta en la casa` (es el conflicto aceptado `M[NpTail, PREP]`); el parser elige el sustantivo porque así está programado, no porque la gramática lo obligue. Si le dábamos esa regla al modelo, la Tarea C solo mediría si obedece una instrucción más.

La respuesta es un objeto JSON con cuatro campos: `accepted`, `tree`, `upos` y `violated_rule`. Las categorías UPOS se piden siempre, aunque el modelo rechace la oración, para poder compararlo con spaCy y HuggingFace en la Tarea B.

## 3. El validador

`experiments/llm_validator.py` revisa cada árbol contra `es.gram` y el lexicón:

1. La raíz es `Sentence`.
2. Cada nodo no terminal usa una producción que existe. Se permite omitir las ramas que solo derivan ε, igual que la vista compacta del parser.
3. Cada palabra cuelga de su tipo de token, y ese tipo es el que le da el lexicón (`el` solo puede ser `DET_MS`).
4. Las hojas del árbol, leídas de izquierda a derecha, son exactamente las palabras de la oración.
5. Si el modelo rechaza, no debe dar árbol; si acepta, sí.

Un árbol que no pasa cuenta como desviación de las reglas aunque `accepted` acierte. Para confiar en el validador lo comparamos con el parser: aceptó los 6000 árboles (completos y compactos) que el parser generó para 3000 oraciones aleatorias de la gramática, y en 5000 árboles con una palabra cambiada al azar, cada vez que el validador dijo "válido" el parser también aceptó la oración.

## 4. Qué medimos

- Aceptar o rechazar contra `in_grammar` (si sigue nuestra gramática) y contra `spanish_ok` (si distingue español correcto), con precisión, recall y tasa de rechazo correcto, igual que las otras herramientas.
- Tasa de desviación: de las oraciones de nivel 3, que son español correcto pero están fuera de la gramática, qué fracción acepta el modelo.
- Árboles inválidos: cuántas veces acepta con un árbol que no pasa el validador.
- Estabilidad: en cuántas oraciones las tres repeticiones no coinciden.
- Zero-shot frente a few-shot en todo lo anterior.

## 5. Resultados

Pendiente: se llena cuando el set de prueba esté completo y corramos `uv run python -m experiments.run_llm`.
