import os
import unicodedata
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv("/home/santiago/Desktop/simulacros-ags/.env")

excel_path = "/home/santiago/Desktop/simulacros-ags/SABER 11 SAUCARA 2026 OFICIALES.xlsx"
if not os.path.exists(excel_path):
    print(f"ERROR: File {excel_path} does not exist!")
    exit(1)

def normalize_str(s):
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8')
    return s.strip().upper()

db_url = os.getenv("SUPABASE_DB_URL")
if not db_url:
    print("ERROR: SUPABASE_DB_URL not found!")
    exit(1)

conn = psycopg2.connect(db_url)
try:
    with conn.cursor() as cur:
        # Get active promotion ID
        cur.execute("SELECT id, nombre, anio_graduacion FROM promociones ORDER BY anio_graduacion DESC LIMIT 1;")
        promo_row = cur.fetchone()
        if not promo_row:
            print("ERROR: No promotion found in database!")
            exit(1)

        promocion_id, promo_nombre, anio_grad = promo_row
        anio_presentacion = anio_grad or 2026
        print(f"Ingesting ICFES Real for Promotion: {promo_nombre} ({promocion_id}) - Año: {anio_presentacion}")

        # Get existing count in `resultados_icfes_real`
        cur.execute("SELECT COUNT(*) FROM resultados_icfes_real WHERE promocion_id = %s;", (promocion_id,))
        count_before = cur.fetchone()[0]

        # Get students map
        cur.execute("SELECT id, nombre FROM estudiantes WHERE promocion_id = %s;", (promocion_id,))
        db_students = cur.fetchall()
        db_st_map = {normalize_str(s[1]): s[0] for s in db_students}

        df_raw = pd.read_excel(excel_path)
        inserted_count = 0

        for idx, row in df_raw.iterrows():
            raw_name = row.iloc[2]
            if pd.isna(raw_name) or not isinstance(raw_name, str):
                continue
            
            norm_name = normalize_str(raw_name)
            if norm_name in ["ESTUDIANTE", "PROMEDIO", "DESVIACION", "TOTAL"]:
                continue

            matched_id = db_st_map.get(norm_name)
            if not matched_id:
                for key in db_st_map:
                    if key in norm_name or norm_name in key:
                        matched_id = db_st_map[key]
                        break

            if not matched_id:
                print(f"WARNING: Student '{raw_name}' not matched in DB!")
                continue

            def safe_num(v):
                if pd.isna(v):
                    return None
                try:
                    val = float(v)
                    return val if not pd.isna(val) else None
                except (ValueError, TypeError):
                    return None

            puntaje_global = safe_num(row.iloc[3])
            lc = safe_num(row.iloc[4])
            mat = safe_num(row.iloc[5])
            soc = safe_num(row.iloc[6])
            cn = safe_num(row.iloc[7])
            ing = safe_num(row.iloc[8])

            cur.execute("""
                INSERT INTO resultados_icfes_real (
                    estudiante_id, promocion_id, anio_presentacion, lectura_critica, matematicas,
                    sociales_ciudadanas, ciencias_naturales, ingles, puntaje_global
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (estudiante_id, anio_presentacion) DO UPDATE SET
                    promocion_id = EXCLUDED.promocion_id,
                    lectura_critica = EXCLUDED.lectura_critica,
                    matematicas = EXCLUDED.matematicas,
                    sociales_ciudadanas = EXCLUDED.sociales_ciudadanas,
                    ciencias_naturales = EXCLUDED.ciencias_naturales,
                    ingles = EXCLUDED.ingles,
                    puntaje_global = EXCLUDED.puntaje_global;
            """, (matched_id, promocion_id, anio_presentacion, lc, mat, soc, cn, ing, puntaje_global))
            inserted_count += 1

        conn.commit()

        # Get count after
        cur.execute("SELECT COUNT(*) FROM resultados_icfes_real WHERE promocion_id = %s;", (promocion_id,))
        count_after = cur.fetchone()[0]

        print("\n==========================================")
        print("   TABLA DE VERIFICACIÓN DE CONTEOS       ")
        print("==========================================")
        print(f"  Resultados Pre-Ingesta:  {count_before}")
        print(f"  Resultados Post-Ingesta: {count_after}")
        print(f"  Cambio Neto Ingestado:   +{count_after - count_before} filas")
        print("==========================================\n")

finally:
    conn.close()
