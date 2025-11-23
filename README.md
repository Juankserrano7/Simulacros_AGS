# Dashboard Simulacros AGS (Streamlit)

Panel interactivo para analizar resultados de simulacros Preicfes (HP1, HP2 y Avancemos) con autenticación PBKDF2 para docentes.

## Requisitos rápidos
- Python 3.10+ y `pip`.
- Dependencias: `pip install -r requirements.txt`.
- Archivos de datos y credenciales ubicados en la raíz del repo.

## Cómo ejecutar
1) Instala dependencias:  
   `pip install -r requirements.txt`
2) Verifica que los CSV de resultados y `auth_users.csv` estén en la raíz.  
3) Inicia el dashboard:  
   `streamlit run app.py`

## Datos esperados
Los tres archivos leídos se definen en `simulacros_ags/config.py`:
- `HELMER_PARDO1.csv`
- `HELMER_PARDO2.csv`
- `PREPARATE.csv`

Cada CSV debe incluir al menos:  
- `ESTUDIANTE` (nombre completo)  
- `PROMEDIO PONDERADO`  
- Las materias listadas en `MATERIAS`: `LECTURA CRÍTICA`, `MATEMÁTICAS`, `SOCIALES Y CIUDADANAS`, `CIENCIAS NATURALES`, `INGLÉS`  
- Opcional: `GRADO`

Notas de formato:
- Se ignora la primera fila (`skiprows=1`), así que el encabezado real debe estar en la segunda línea.
- Filas con totales/medias que incluyan “PROMEDIO”, “TOTAL” o “MEDIA” en `ESTUDIANTE` se descartan automáticamente.
- Duplicados por `ESTUDIANTE` se quedan con la primera aparición.

### Nuevos simulacros desde la UI
- El usuario `juan.serrano@aspaen.edu.co` ve el apartado **🧰 Gestión de Simulacros** para subir un Excel (usa la plantilla descargable).  
- Los archivos quedan en `simulacros_data/uploads/` y se registran en `simulacros_data/simulacros_metadata.json`.
- Las gráficas y tablas se actualizan automáticamente con cualquier simulacro cargado.
- Las recomendaciones/conclusiones se generan con IA (si `OPENAI_API_KEY` está definida) o con heurística local. Modelo configurable con `OPENAI_MODEL`.

## Autenticación de docentes
El login usa `auth_users.csv` con hashes PBKDF2 (ver `simulacros_ags/auth.py`). Para generarlo:
1) Lista de correos permitidos (uno por línea) en `listado_correeos_profes.txt` (dominio `@aspaen.edu.co`).
2) Archivo `claves.txt` con pares `correo: contraseña` (texto plano, uso temporal).
3) Ejecuta el sincronizador:
   ```bash
   python scripts/sync_profesores.py \
     --emails listado_correeos_profes.txt \
     --passwords claves.txt \
     --output auth_users.csv
   ```
4) Distribuye las credenciales de forma segura y retira los archivos en texto plano si no deben versionarse.

Campos en `auth_users.csv`: `email`, `salt`, `password_hash`, `activo`, `ultima_actualizacion`.

## Navegación del dashboard
- `🏠 Inicio`: panorama general, métricas y hallazgos rápidos.
- `🎖️ Rankings`: top global y comparativo por estudiante.
- `📊 Reporte General`: vista de tabla filtrable del simulacro seleccionado.
- `🔄 Comparación Simulacros`: evolución y diferencias por materia.
- `👤 Análisis Individual`: detalle por estudiante, materias y progresión.
- `📈 Avance`: seguimiento longitudinal entre simulacros.
- `📉 Estadísticas Detalladas`: desgloses y diagnósticos adicionales.

## Estructura relevante
- `app.py`: punto de entrada Streamlit y enrutador de páginas.
- `simulacros_ags/`: lógica de autenticación, carga de datos, estilos y páginas.
- `scripts/sync_profesores.py`: genera `auth_users.csv` desde listados de correos y claves.

## Problemas frecuentes
- “No se encontró el archivo de credenciales”: genera `auth_users.csv` con el script anterior.
- Datos vacíos o errores al cargar: confirma nombres/ubicación de los CSV y que el encabezado esté en la segunda línea.
- Cambiaste datos y no ves la actualización: borra el caché de Streamlit o reinicia la app.

## Despliegue
Mantén los archivos sensibles (`auth_users.csv`, `claves.txt`) fuera del control de versiones y configúralos como secretos/variables de entorno en el entorno de despliegue. Ejecuta siempre desde la raíz del proyecto para que se encuentren los CSV y el logo.
