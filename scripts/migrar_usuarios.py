import os
import random
import pandas as pd
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BACKUP_DIR = Path(os.path.expanduser("~/Desktop/respaldo_simulacros_ags_20260726"))
AUTH_USERS_CSV = BACKUP_DIR / "auth_users.csv"

def migrar_usuarios(db_url: str):
    if not AUTH_USERS_CSV.exists():
        raise FileNotFoundError(f"Archivo auth_users.csv no encontrado en respaldo: {AUTH_USERS_CSV}")

    df = pd.read_csv(AUTH_USERS_CSV)
    df["email"] = df["email"].str.strip().str.lower()

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # Obtener ID de la promoción activa
            cur.execute("SELECT id FROM promociones WHERE nombre = %s;", ("Grado 11 2025/2026",))
            promo_row = cur.fetchone()
            if not promo_row:
                raise ValueError("No se encontró la promoción 'Grado 11 2025/2026'. Ejecuta migrar_a_supabase.py primero.")
            promocion_id = promo_row[0]

            usuarios_insertados = 0
            accesos_concedidos = 0

            for _, row in df.iterrows():
                email = str(row["email"]).strip().lower()
                salt = str(row["salt"]).strip()
                password_hash = str(row["password_hash"]).strip()
                
                val_activo = row.get("activo", True)
                if isinstance(val_activo, bool):
                    activo = val_activo
                else:
                    activo = str(val_activo).strip().lower() in ("true", "1", "yes", "si")

                rol = "admin" if email == "juan.serrano@aspaen.edu.co" else "docente"

                cur.execute("""
                    INSERT INTO usuarios (email, salt, password_hash, activo, rol, ultima_actualizacion)
                    VALUES (%s, %s, %s, %s, %s, now())
                    ON CONFLICT (email) DO UPDATE SET
                        salt = EXCLUDED.salt,
                        password_hash = EXCLUDED.password_hash,
                        activo = EXCLUDED.activo,
                        rol = EXCLUDED.rol,
                        ultima_actualizacion = now();
                """, (email, salt, password_hash, activo, rol))
                usuarios_insertados += 1

                # Conceder acceso a la promoción
                cur.execute("""
                    INSERT INTO usuario_promocion_acceso (usuario_email, promocion_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                """, (email, promocion_id))
                accesos_concedidos += 1

        conn.commit()
        print(f"Migrados {usuarios_insertados} usuarios a Supabase.")
        print(f"Otorgado acceso a {accesos_concedidos} usuarios a la promoción ID {promocion_id}.")

        # Verificación: 3 emails al azar comparados carácter por carácter sin mostrar los secretos
        emails_lista = df["email"].tolist()
        muestra_emails = random.sample(emails_lista, min(3, len(emails_lista)))

        print("\n--- Verificación de Integridad de Hashes (3 muestras al azar) ---")
        verificacion_exitosa = True
        with conn.cursor() as cur:
            for em in muestra_emails:
                row_csv = df[df["email"] == em].iloc[0]
                csv_salt = str(row_csv["salt"]).strip()
                csv_hash = str(row_csv["password_hash"]).strip()

                cur.execute("SELECT salt, password_hash, rol FROM usuarios WHERE email = %s;", (em,))
                db_row = cur.fetchone()
                if not db_row:
                    print(f"ERROR DE VERIFICACIÓN: Usuario {em} no encontrado en DB.")
                    verificacion_exitosa = False
                    continue

                db_salt, db_hash, db_rol = db_row
                
                salt_exacto = (csv_salt == db_salt)
                hash_exacto = (csv_hash == db_hash)

                if salt_exacto and hash_exacto:
                    print(f"Usuario {em}: Salt coincidente = OK, Hash coincidente = OK (Rol: {db_rol})")
                else:
                    print(f"ERROR DE VERIFICACIÓN en {em}: Mismatch detectado.")
                    verificacion_exitosa = False

        if verificacion_exitosa:
            print("VERIFICACIÓN COMPLETA: Todos los salts y hashes coinciden carácter por carácter con el CSV de respaldo.")
        else:
            print("CRITICAL ERROR: Discrepancia detectada en la verificación de hashes.")

    finally:
        conn.close()

if __name__ == "__main__":
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("ERROR: La variable de entorno SUPABASE_DB_URL no está configurada en .env.")
        exit(1)
    migrar_usuarios(db_url)
