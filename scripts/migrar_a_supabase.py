import os
import json
import unicodedata
import psycopg2
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env en la raíz del proyecto
load_dotenv()

BACKUP_DIR = Path(os.path.expanduser("~/Desktop/respaldo_simulacros_ags_20260726"))
METADATA_FILE = BACKUP_DIR / "simulacros_data" / "simulacros_metadata.json"
SCHEMA_FILE = Path("supabase/schema.sql")

COLUMN_CANONICAL_MAP = {
    "estudiante": "ESTUDIANTE",
    "grado": "GRADO",
    "lectura critica": "LECTURA CRÍTICA",
    "lectura crítica": "LECTURA CRÍTICA",
    "matematicas": "MATEMÁTICAS",
    "matemáticas": "MATEMÁTICAS",
    "sociales y ciudadanas": "SOCIALES Y CIUDADANAS",
    "ciencias naturales": "CIENCIAS NATURALES",
    "ingles": "INGLÉS",
    "inglés": "INGLÉS",
    "promedio simple": "PROMEDIO SIMPLE",
    "promedio ponderado": "PROMEDIO PONDERADO",
    "desv. estandar": "DESVIACIÓN ESTÁNDAR",
    "desviación estándar": "DESVIACIÓN ESTÁNDAR",
    "pp por materia": "PP POR MATERIA",
}

def _canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    new_cols = []
    for col in df.columns:
        key = str(col).strip().lower()
        new_cols.append(COLUMN_CANONICAL_MAP.get(key, str(col).strip()))
    df.columns = new_cols
    return df

def _clean_student_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = _canonicalize_columns(df)
    df["ESTUDIANTE"] = df["ESTUDIANTE"].astype(str).str.strip()
    df["ESTUDIANTE"] = df["ESTUDIANTE"].apply(
        lambda s: unicodedata.normalize("NFKD", s)
        .encode("ascii", "ignore")
        .decode()
        .upper()
        .replace("-", " ")
    )
    df["ESTUDIANTE"] = df["ESTUDIANTE"].str.replace(r"[^A-Z0-9 ]+", " ", regex=True)
    df["ESTUDIANTE"] = df["ESTUDIANTE"].str.replace(r"\s+", " ", regex=True).str.strip()
    df["ESTUDIANTE"] = df["ESTUDIANTE"].str.replace("D SILVA", "DSILVA", regex=False)
    df["ESTUDIANTE"] = df["ESTUDIANTE"].str.replace("D  SILVA", "DSILVA", regex=False)
    df.loc[df["ESTUDIANTE"].str.lower() == "nan", "ESTUDIANTE"] = ""

    df = df[df["ESTUDIANTE"].notna()]
    df = df[df["ESTUDIANTE"] != ""]
    df = df[~df["ESTUDIANTE"].str.upper().str.contains("PROMEDIO", na=False)]
    df = df[~df["ESTUDIANTE"].str.upper().str.contains("TOTAL", na=False)]
    df = df[~df["ESTUDIANTE"].str.upper().str.contains("MEDIA", na=False)]
    df = df.drop_duplicates(subset=["ESTUDIANTE"], keep="first")

    return df.reset_index(drop=True)

def _try_read_file(path: Path) -> pd.DataFrame:
    readers = []
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        readers = [lambda: pd.read_excel(path, skiprows=1), lambda: pd.read_excel(path)]
    else:
        readers = [lambda: pd.read_csv(path, skiprows=1), lambda: pd.read_csv(path)]

    last_exc = None
    for reader in readers:
        try:
            df = reader()
            if "ESTUDIANTE" in df.columns or "estudiante" in [str(c).lower() for c in df.columns]:
                return df
        except Exception as exc:
            last_exc = exc
            continue
    if last_exc:
        raise last_exc
    raise ValueError(f"No se pudo leer el archivo: {path}")

def run_schema(conn):
    print("--- Aplicando supabase/schema.sql ---")
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print("Esquema aplicado exitosamente con RLS activado.")

def migrar_datos(db_url: str, execute_ddl: bool = True):
    if not os.path.exists(BACKUP_DIR):
        raise FileNotFoundError(f"Carpeta de respaldo no encontrada en {BACKUP_DIR}")

    conn = psycopg2.connect(db_url)
    try:
        if execute_ddl:
            run_schema(conn)

        with conn.cursor() as cur:
            # 1. Crear Promoción por defecto
            cur.execute("""
                INSERT INTO promociones (nombre, anio_graduacion, activa)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id;
            """, ("Grado 11 2025/2026", 2026, True))
            row = cur.fetchone()
            if row:
                promocion_id = row[0]
            else:
                cur.execute("SELECT id FROM promociones WHERE nombre = %s;", ("Grado 11 2025/2026",))
                promocion_id = cur.fetchone()[0]

            print(f"Promoción ID: {promocion_id}")

            # 2. Leer Metadatos del respaldo
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                meta = json.load(f)
            simulacros_list = meta.get("simulacros", [])

            # Cargar y limpiar todos los dataframes
            parsed_simulacros = []
            all_students = {}  # nombre -> grado

            for sim in simulacros_list:
                rel_path = sim.get("path")
                full_path = BACKUP_DIR / rel_path
                clean_df = _clean_student_frame(_try_read_file(full_path))
                parsed_simulacros.append({
                    "meta": sim,
                    "df": clean_df
                })
                for _, r in clean_df.iterrows():
                    name = r["ESTUDIANTE"]
                    grado = str(r.get("GRADO")).strip() if "GRADO" in clean_df.columns and pd.notna(r.get("GRADO")) else None
                    if name not in all_students or (grado and not all_students[name]):
                        all_students[name] = grado

            # 3. Insertar Estudiantes
            student_id_map = {}
            for name, grado in sorted(all_students.items()):
                cur.execute("""
                    INSERT INTO estudiantes (nombre, grado, promocion_id, es_inclusion)
                    VALUES (%s, %s, %s, false)
                    ON CONFLICT (nombre, promocion_id) 
                    DO UPDATE SET grado = EXCLUDED.grado
                    RETURNING id;
                """, (name, grado, promocion_id))
                st_id = cur.fetchone()[0]
                student_id_map[name] = st_id

            print(f"Estudiantes procesados en DB: {len(student_id_map)}")

            # 4. Insertar Simulacros
            for item in parsed_simulacros:
                sim_meta = item["meta"]
                sim_id = sim_meta.get("id")
                nombre = sim_meta.get("nombre")
                origen = sim_meta.get("origen", "upload")
                estado = sim_meta.get("estado", "ready")
                creado_por = sim_meta.get("creado_por", "sistema")
                creado_en = sim_meta.get("creado_en")
                insights = json.dumps(sim_meta.get("insights", {}))

                cur.execute("""
                    INSERT INTO simulacros (id, nombre, promocion_id, origen, estado, creado_por, creado_en, insights)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (id) DO UPDATE SET
                        nombre = EXCLUDED.nombre,
                        insights = EXCLUDED.insights,
                        estado = EXCLUDED.estado;
                """, (sim_id, nombre, promocion_id, origen, estado, creado_por, creado_en, insights))

            print(f"Simulacros procesados en DB: {len(parsed_simulacros)}")

            # 5. Insertar Resultados de Simulacros
            total_resultados_insertados = 0
            for item in parsed_simulacros:
                sim_id = item["meta"]["id"]
                df = item["df"]

                for _, r in df.iterrows():
                    st_name = r["ESTUDIANTE"]
                    st_id = student_id_map[st_name]

                    def safe_float(val):
                        if pd.isna(val):
                            return None
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            return None

                    lc = safe_float(r.get("LECTURA CRÍTICA"))
                    mat = safe_float(r.get("MATEMÁTICAS"))
                    soc = safe_float(r.get("SOCIALES Y CIUDADANAS"))
                    cn = safe_float(r.get("CIENCIAS NATURALES"))
                    ing = safe_float(r.get("INGLÉS"))
                    ps = safe_float(r.get("PROMEDIO SIMPLE"))
                    pp = safe_float(r.get("PROMEDIO PONDERADO"))
                    de = safe_float(r.get("DESVIACIÓN ESTÁNDAR"))

                    cur.execute("""
                        INSERT INTO resultados_simulacro (
                            simulacro_id, estudiante_id, lectura_critica, matematicas,
                            sociales_ciudadanas, ciencias_naturales, ingles,
                            promedio_simple, promedio_ponderado, desviacion_estandar
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (simulacro_id, estudiante_id) DO UPDATE SET
                            lectura_critica = EXCLUDED.lectura_critica,
                            matematicas = EXCLUDED.matematicas,
                            sociales_ciudadanas = EXCLUDED.sociales_ciudadanas,
                            ciencias_naturales = EXCLUDED.ciencias_naturales,
                            ingles = EXCLUDED.ingles,
                            promedio_simple = EXCLUDED.promedio_simple,
                            promedio_ponderado = EXCLUDED.promedio_ponderado,
                            desviacion_estandar = EXCLUDED.desviacion_estandar;
                    """, (sim_id, st_id, lc, mat, soc, cn, ing, ps, pp, de))
                    total_resultados_insertados += 1

            print(f"Resultados de simulacro procesados en DB: {total_resultados_insertados}")

        conn.commit()
        print("Migración a Supabase completada con éxito.")

        # 6. Conteo de verificación posterior desde Supabase
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM promociones;")
            count_promos = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM estudiantes;")
            count_estudiantes = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM simulacros;")
            count_simulacros = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM resultados_simulacro;")
            count_resultados = cur.fetchone()[0]

        return {
            "promociones": count_promos,
            "estudiantes": count_estudiantes,
            "simulacros": count_simulacros,
            "resultados_simulacro": count_resultados
        }
    finally:
        conn.close()

if __name__ == "__main__":
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("ERROR: La variable de entorno SUPABASE_DB_URL no está configurada en .env.")
        exit(1)
    results = migrar_datos(db_url, execute_ddl=True)
    print("Conteos finales en Supabase:", results)
