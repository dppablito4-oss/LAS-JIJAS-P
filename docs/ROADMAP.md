# Pendientes y límites de MVP 0.1

## Para habilitar IA real

- Completar claves locales y confirmar acceso y tarifas. Modelos predeterminados: Luna para visión, DeepSeek V4 Pro para herramientas y Sol para revisión. Ejecutar scripts/check_ai.py y, con presupuesto explícito, --smoke. No se ejecutó consumo IA real en esta actualización.
- Añadir tabla de precios por proveedor/modelo y tarifa de caché; estimación de extracción y consolidación por análisis. El uso bruto devuelto ya se persiste.
- Evaluar calidad de extracción con tickets reales anonimizados, múltiples selecciones y fechas ilegibles. Hoy hay validación estructural y simulación offline, no un benchmark de OCR real.

## Calidad y cobertura

- Ampliar la validación temporal existente en bloques con entrenamiento creciente a más temporadas y datos recientes. Añadir intervalos que contemplen dependencia entre partidos y calibración con muestra suficiente; ya hay métricas por totales y calibración 1X2. No etiquetar como ventaja validada por una evaluación inicial pequeña.
- NBA: verificar e integrar eficiencias y ritmo con definiciones y fuentes; ampliar descanso al calendario completo y diferenciar temporada regular/playoffs. Sin modelo predictivo NBA hasta evaluación contra baseline.
- Identidades persistentes multifuente y cobertura amplia de alias. El adaptador fútbol ya utiliza IDs ESPN en el modelo y rechaza otras fuentes; NBA enlaza etiquetas por abreviatura cuando está disponible.
- Fuentes verificadas de bajas y alineaciones, además de xG con derechos compatibles. Actualmente no disponibles.
- Actualización del resultado final como registro separado e inmutable, con fuente y fecha. No reemplazar el informe prepartido.
- Presupuesto HTTP interno del SDK, además de timeout de proceso; adaptar consultas de temporada para reducir fan-out. Partir de caché, por defecto solo lectura.

## Operación e interfaz

- Probar Docker/Linux: el equipo de implementación no tiene Docker.
- Revisión visual mediante capturas, viewport móvil y E2E de clics: la interfaz sí cargó y se inspeccionó su árbol accesible, pero la captura de ventanas falló por timeout y los clics por geometría no disponible.
- Paginación visible del historial (API ya admite offset/limit), borrado recuperable y política configurable de retención. Exportación JSON ya disponible.
- Informes parciales incrementales ante agotamiento del plazo global y mejores fases de progreso. Actualmente se informa queued/running/estado terminal sin porcentajes inventados.
- Revisar periódicamente dependencias transitivas y reducir el peso científico de penaltyblog cuando sea compatible con su API pública.

No se incluyen en esta hoja de ruta colocación de apuestas, recuperación de pérdidas, importes sugeridos, wallets, depósitos ni cuentas de casas. Props, vivo y mercados con liquidación parcial siguen fuera de alcance.

## Completado tras la auditoría

- Plantilla .env compatible con tarifas vacías.
- Ajuste estadístico en proceso terminable y reutilizado por evento/corte.
- Rechazo de cuotas futuras, abstención por antigüedad y coherencia de mercado completo.
- Fuente ESPN explícita, deduplicación y rechazo de contradicciones.
- Totales solicitados hasta 9,5 y estado explícito fuera de cobertura.
- Evaluación del holdout completo por bloques, IDs/hash y métricas de 1X2/totales.
- Integración de Luna, DeepSeek Pro thinking y revisión Sol con pruebas simuladas.
- Workflow de CI Windows/Linux añadido; su resultado remoto queda pendiente de ejecución.
