# Agente de Auditoría de Escalamiento (Simulacros AGS)

Guía breve para verificar que la plataforma siga funcionando al incorporar nuevos simulacros.

## Checklist ante cada subida
- **Plantilla y datos**: confirmar que `simulacros_data/plantilla_simulacro.xlsx` está actualizada y que el archivo cargado respeta encabezados (`ESTUDIANTE`, `GRADO`, materias, `PROMEDIO PONDERADO`).
- **Metadatos y rutas**: revisar `simulacros_data/simulacros_metadata.json` tras la carga (estado `ready`, ruta del CSV/xlsx en `simulacros_data/uploads/`, sin errores).
- **IA y alertas**: verificar que el modelo/generación de IA agrega `alertas`, `fortalezas` y recomendaciones (corto/mediano/largo). Si no hay clave `OPENAI_API_KEY`, se usa heurística local.
- **UI dinámica**: confirmar que el nuevo simulacro aparece en filtros, tabla comparativa, rankings y estadísticas detalladas sin hardcodes de nombres.
- **Validaciones**: sí/no para columnas requeridas, tipos numéricos en materias y `PROMEDIO PONDERADO`, tamaño de archivo < límite (`MAX_UPLOAD_MB` en config).

## Pruebas rápidas
- `streamlit run app.py` y cargar un Excel de prueba; esperar estado `ready` y presencia en todas las pestañas.
- Revisar hallazgos/recomendaciones en Inicio: se deben poblar los bloques ⚠️/✅ y las tarjetas de corto/mediano/largo plazo.
- Rankings: Top Global renderizado, tabla filtrable sin columnas vacías.
- Estadísticas detalladas: correlaciones visibles (hasta 3 simulacros), análisis por grado solo si existe columna `GRADO`.
- Prueba local sin secrets: el push se omite; si hay entradas fallidas, borra `simulacros_data/simulacros_metadata.json`, reinicia la app (se recrea con semillas) y vuelve a subir el simulacro.

## Recuperación ante fallos
- Si un simulacro queda en estado `failed`, revisar `errores` en `simulacros_data/simulacros_metadata.json`, corregir archivo y recargar.
- Borrar `simulacros_data/simulacros_metadata.json` solo si es necesario regenerar metadatos (se crearán desde semillas); no borrar uploads válidos.
- Sin conexión a IA: revisar heurística en `simulacros_ags/ai.py` y mantener mensajes claros en UI.

## Configuración clave
- Límite de archivo y usuario autorizado de carga en `simulacros_ags/config.py` (`MAX_UPLOAD_MB`, `UPLOAD_ALLOWED_USER`).
- Dependencias: `pip install -r requirements.txt` (incluye `openai`).
- Estructura de datos: nuevos simulacros se guardan en `simulacros_data/uploads/` y se indexan en `simulacros_metadata.json`.
