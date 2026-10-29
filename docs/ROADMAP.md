# Pendientes y límites de MVP 0.1

## Para habilitar IA real

- Configurar modelos y claves locales, confirmar acceso y tarifas de la cuenta, ejecutar smoke optativo de visión y tool calling real con un presupuesto explícito. No se ejecutó consumo IA en esta entrega.
- Añadir tabla de precios por proveedor/modelo y tarifa de caché; estimación de extracción y consolidación por análisis. El uso bruto devuelto ya se persiste.
- Evaluar calidad de extracción con tickets reales anonimizados, múltiples selecciones y fechas ilegibles. Hoy hay validación estructural y simulación offline, no un benchmark de OCR real.

## Calidad y cobertura

- Validación temporal de fútbol más amplia, rolling-origin, más temporadas, intervalos de incertidumbre y calibración con muestra suficiente. No etiquetar como ventaja validada por una evaluación inicial pequeña.
- NBA: verificar e integrar eficiencias y ritmo con definiciones y fuentes; ampliar descanso al calendario completo y diferenciar temporada regular/playoffs. Sin modelo predictivo NBA hasta evaluación contra baseline.
- Identidades persistentes multifuente y temporadas, cobertura explícita de alias y cambios de nombre; no unir categorías por similitud textual.
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
