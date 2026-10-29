# Integración de cambios locales y GitHub

29/10/2026, America/Lima.

Se revisaron e integraron los commits remotos `0194251` y `b32a898` (PR #1) con los cambios locales de híbrido conservados en `7169420`. Se resolvieron diez archivos con conflictos; no se descartó una rama completa para reemplazarla por la otra.

## Resultado

- Conservados los adaptadores auditados: identidad por IDs ESPN, namespace explícito, duplicados contradictorios rechazados y correspondencia NBA por abreviatura.
- Conservados el modelo en proceso terminable, reutilización por evento/corte, evaluación de todo el holdout por bloques crecientes, calibración por clase/total y hash de entrenamiento.
- Conservados los controles de cuota completa y el editor remoto que invalida candidatos/mercados antiguos y descarta respuestas de búsquedas obsoletas.
- Integradas la revisión estructurada local y la compatibilidad con el campo histórico remoto `ai_review`. Los informes nuevos incluyen `review` con resultado validado; el render muestra una sola revisión. Las probabilidades y EV permanecen en el motor determinista.
- Conservados los límites locales de tiempo por llamada, tokens por etapa y presupuesto conjunto IA, subordinados al plazo del trabajo completo. Se reserva tiempo para revisión cuando está habilitada.
- Unificados los controles de antigüedad: no se ajusta un modelo con históricos inutilizables; cuotas futuras/posteriores al evento se rechazan antes de encolar; precios antiguos suspenden probabilidades aplicables y EV.
- Uso IA etiquetado con proveedor, modelo y etapa. La estimación del analista no se confunde con el coste total cuando se solicita revisión. Un fallo de revisión conserva el informe y el uso conocido.
- Conservados workflow Windows/Linux y script opcional de diagnóstico de modelos. No se ejecutó el diagnóstico con credenciales ni su modo facturable.

## Corrección detectada durante la revisión

La versión local anterior equiparaba `OPENAI_REVIEW_MODE=pro` a esfuerzo `max`. La documentación oficial y el SDK confirman que **modo y esfuerzo son independientes**. La integración transmite `reasoning={'mode':'pro','effort':'high'}` cuando eso se configura, con el mismo ID. Se actualizaron comentarios y pruebas para verificar ambos parámetros por separado. Fuente: [OpenAI Docs, Reasoning mode](https://developers.openai.com/api/docs/guides/reasoning#reasoning-mode).

## Validación

- Suite combinada: **54 pruebas offline aprobadas**; incluye pruebas de ambos lados y aislamiento de claves reales en tests.
- Compilación TypeScript/Vite correcta.
- `.env` permanece ignorado por Git. Se corrigió únicamente un comentario sobre pro; se comprobó igualdad de todos sus valores antes/después, incluidas ambas claves.
- No hubo llamadas IA facturables, consultas deportivas nuevas ni cambios de dependencias. No se publicaron cambios ni se hizo push como parte de esta integración.

Los resultados originales de smoke/evaluación se conservan como evidencia histórica, sin atribuirlos al protocolo nuevo. Docker/Linux, CI remoto y revisión visual no se declaran comprobados por la ejecución local.
