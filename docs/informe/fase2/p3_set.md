# Set de prueba y metodología

## Diseño del set

El set contiene 60 oraciones, divididas en 20 por nivel. El nivel 1 reúne
estructuras simples de sujeto, verbo y objeto opcional; el nivel 2 agrega
modificadores, pretérito, frases preposicionales y errores de concordancia;
el nivel 3 incluye fenómenos que exceden la gramática formal, como
subordinación, coordinación, clíticos, contracciones, `respectivamente` y
variaciones de orden.

Cada registro incluye dos referencias distintas: `spanish_ok` indica si la
oración es aceptable en español, mientras que `in_grammar` indica si la
reconoce `grammars/es.gram`. Por eso las oraciones correctas de nivel 3
pueden tener `spanish_ok: true` e `in_grammar: false`. El campo `upos` contiene
una categoría por palabra para las oraciones correctas y es `null` para las
incorrectas. Las ambiguas tienen una etiqueta `attachment` (`noun` o `verb`)
que expresa la lectura elegida para la comparación.

El set incluye 16 oraciones marcadas como español incorrecto y 6 ambiguas.
`tests/test_test_set.py` valida el esquema, los mínimos por nivel, las
etiquetas UPOS, la cobertura de fenómenos y la concordancia de `in_grammar`
con el parser propio.

## Clasificación de errores

`experiments/classify_errors.py` compara las salidas disponibles en
`results/*.jsonl` con ambas referencias y con las etiquetas UPOS. Cada
discrepancia se escribe en `results/errors.csv` como falso positivo, falso
negativo o error de etiquetado, acompañada por la referencia y los fenómenos
de la oración. Una etiqueta de aceptación `null` no se cuenta como falso
positivo ni falso negativo; si una herramienta no entrega UPOS para una
oración que sí tiene referencia, cada palabra esperada cuenta como error de
etiquetado.

La clasificación debe generarse después de ejecutar las herramientas y tener
sus archivos JSONL en `results/`. No se reportan resultados cuantitativos aquí
hasta contar con esas salidas; el CSV se regenera directamente desde ellas.
