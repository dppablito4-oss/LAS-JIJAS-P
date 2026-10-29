# Correcciones de auditoría e integración IA

29 de octubre de 2026, America/Lima. Esta actualización integra las correcciones sobre la revisión `1cf00db`, conservando los perfiles Sol y Economy que se añadieron mientras se desarrollaban los cambios. Los resultados de `VALIDATION.md`, `LIVE_SMOKE.json` y `MODEL_EVALUATION.json` permanecen como evidencia histórica del recorrido original.

## Comportamiento corregido

- `.env.example` admite tarifas vacías; no se convierten a cero ni se interpretan como coste conocido.
- Consultas deportivas y ajuste/validación Dixon-Coles corren en procesos terminables. Un timeout o cancelación termina y recoge el proceso. Selecciones del mismo evento/corte comparten ajuste.
- En modo real, una cuota futura o posterior al inicio se rechaza antes de encolar. El informe también comprueba coherencia temporal. Una cuota antigua o históricos antiguos suspenden el EV; los históricos antiguos suspenden además la probabilidad aplicable del mercado.
- Fútbol acepta únicamente fuente explícita ESPN e identidades válidas. Deduplica por competición/evento y rechaza duplicados contradictorios. El modelo usa IDs ESPN en lugar de nombres; NBA enlaza etiquetas por abreviatura cuando existe correspondencia.
- El mercado completo solo se usa para quitar margen cuando coincide la cuota seleccionada. La interfaz invalida cuotas/candidatos al editar su identidad y descarta búsquedas que terminaron después de cambiar los campos.
- Se calculan totales solicitados entre 0,5 y 9,5, solo medios goles. Fuera de ese alcance se informa como no soportado.
- La evaluación temporal usa entrenamiento creciente en bloques, cubre todo el holdout y conserva IDs/hash. Añade calibración de las tres clases 1X2, métricas por total e intervalos normales descriptivos. No demuestra rentabilidad y requiere muestras reales más amplias. No se recalcularon los JSON históricos con el nuevo protocolo.
- El E2E espera con plazo monotónico acorde al cálculo; ya no depende de una espera fija de 10 segundos.

## IA preparada

- `AI_PROFILE=sol`: un ID `gpt-6.1-sol` para captura y analista con herramientas Responses. Se conserva la continuidad del razonamiento cifrado en memoria.
- `AI_PROFILE=economy`: `gpt-6-luna` para captura y DeepSeek para herramientas, sin revisión final adicional.
- `AI_PROFILE=hybrid`: Luna, DeepSeek y revisión final `gpt-6.1-sol`. El `.env` local preparado para este trabajo selecciona hybrid y `deepseek-v4-pro` con thinking high; sus claves están vacías y Git lo ignora.

Los identificadores se verificaron en documentación oficial. DeepSeek V4.1 Flash y V4 Pro son opciones distintas; no se inventa un identificador V4.1 Pro. OpenAI permite razonamiento standard/pro configurable; Pro implica trabajo adicional y puede aumentar coste y latencia. La disponibilidad de la cuenta sigue pendiente de comprobar con claves.

Los comentarios IA se guardan separados de probabilidades, EV y conclusión. La revisión recibe hechos resumidos y no el texto bruto completo del ticket ni el grid íntegro. Si falla o se trunca, se mantiene el informe determinista y el uso ya devuelto por las APIs. No hay reintentos facturables ni cambios automáticos de modelo. Las fases IA ajustan su espera al tiempo restante del análisis.

El registro de uso identifica proveedor/modelo. La estimación del analista exige `PRICE_MODEL` coincidente con el modelo activo; si hay uso de revisión OpenAI, el total queda desconocido. Extracción y facturación completa siguen separados. Los límites de tokens incluyen razonamiento y no garantizan un importe monetario máximo.

## Comprobaciones de esta actualización

- Instalación frozen offline: 104 paquetes Python fijados. Sin cambios de dependencias o lockfiles.
- Suite final: **44 pruebas offline aprobadas en 9,70 s**. Incluye perfiles existentes y regresiones de configuración, procesos, fuentes, cuotas, alias/IDs, métricas, revisión y costes.
- Compilación final TypeScript/Vite aprobada después de resolver los cambios concurrentes. Smoke integrado con TestClient: GET / y /api/health devolvieron HTTP 200; capabilities mostró hybrid y claves pendientes. El smoke utilizó una base separada, sin trabajo deportivo o IA.
- `scripts/check_ai.py` sin claves informa `key_missing` para OpenAI y DeepSeek. No hizo llamadas a proveedores.
- Nuevo workflow `.github/workflows/ci.yml` para Windows/Linux: instalación frozen, tests y build. Su éxito remoto no se infiere de la ejecución local.

No se ejecutaron llamadas IA reales, consultas deportivas nuevas, Docker/Linux ni revisión visual móvil en esta actualización. `scripts/check_ai.py --smoke` permite una comprobación optativa facturable con datos sintéticos tras configurar claves. No certifica calidad OCR sobre capturas reales ni exactitud deportiva.

## Activación local

1. Completa solo las claves en `.env`; no las pegues en el chat ni las publiques. La copia preparada tiene `APP_MODE=real` y `AI_PROFILE=hybrid`.
2. Desde la raíz ejecuta `scripts/start.ps1` o sigue el arranque del README. Reinicia al cambiar `.env`.
3. Ejecuta `scripts/check_ai.py` con `PYTHONPATH=backend` para comprobar acceso a los IDs configurados. Una respuesta de catálogo no garantiza saldo, cuota ni disponibilidad posterior.
4. Si quieres comprobar respuestas reales y aceptas consumo, ejecuta el mismo script con `--smoke`. Revisa el uso conocido persistido y los límites.

Pendientes: más temporadas y datos recientes, intervalos adecuados a dependencia temporal, benchmark OCR, pruebas reales de IA, E2E visual, Docker/Linux, precios por modelo/caché, retención y resultado final separado. Véase ROADMAP.
