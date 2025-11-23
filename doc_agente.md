# Agente de documentación (para uso con Codex)

Guía breve para invocar un asistente de documentación mientras trabajas con Codex en este repo.

## Objetivo
- Responder preguntas rápidas sobre cómo correr, desplegar o mantener el dashboard.
- Recordar flujos de autenticación y datos esperados sin tener que abrir varios archivos.

## Fuentes que debe consultar
- `README.md` (cómo ejecutar, datos esperados, autenticación).
- `plan_implementacion.txt` (segmenta autenticación y gobierno de usuarios).
- `simulacros_ags/config.py` (nombres de archivos requeridos y materias).
- `scripts/sync_profesores.py` (cómo generar `auth_users.csv`).

## Prompts sugeridos
- **Ejecución local:** “¿Cómo levanto el dashboard con los CSV y credenciales actuales?”
- **Auth PBKDF2:** “Recuérdame cómo se genera `auth_users.csv` y qué columnas necesita.”
- **Formato de datos:** “¿Qué columnas deben traer los CSV de simulacros y qué filas se ignoran?”
- **Páginas disponibles:** “¿Qué muestra cada pestaña del dashboard y para qué sirve?”
- **Problemas comunes:** “¿Qué hago si Streamlit no encuentra los archivos o cachea datos viejos?”

## Respuestas esperadas (resumen)
- Comando de arranque: `streamlit run app.py` desde la raíz, con `pip install -r requirements.txt` previo.
- Archivos de datos: `HELMER_PARDO1.csv`, `HELMER_PARDO2.csv`, `PREPARATE.csv` con columnas `ESTUDIANTE`, `PROMEDIO PONDERADO` y las materias de `MATERIAS`.
- Auth: generar `auth_users.csv` ejecutando `python scripts/sync_profesores.py --emails listado_correeos_profes.txt --passwords claves.txt --output auth_users.csv`.
- Limpieza automática de datos: se omiten filas cuyo `ESTUDIANTE` contenga “PROMEDIO”, “TOTAL” o “MEDIA”; se descartan duplicados por `ESTUDIANTE`; se salta la primera fila de cada CSV (`skiprows=1`).
- Páginas: Inicio (overview), Rankings, Reporte General, Comparación, Análisis Individual, Avance, Estadísticas Detalladas.

## Buenas prácticas del agente
- Contestar en español, conciso, con paths en monoespaciado.
- Señalar archivos sensibles (`auth_users.csv`, `claves.txt`) y recomendar no versionarlos si aplica.
- Sugerir borrar caché de Streamlit o reiniciar la app si no se ven cambios.
