import os
from typing import Dict, List, Optional
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def _get_db_connection():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        return None
    try:
        return psycopg2.connect(db_url)
    except Exception:
        return None


def get_user_promotions(user_email: str) -> List[Dict]:
    """Devuelve la lista de promociones a las que el usuario logueado tiene acceso autorizado."""
    conn = _get_db_connection()
    if not conn:
        return [{"id": "default", "nombre": "Grado 11 2025/2026", "anio_graduacion": 2026, "activa": True}]

    try:
        email_clean = user_email.strip().lower()
        with conn.cursor() as cur:
            # Consultar rol de usuario
            cur.execute("SELECT rol FROM usuarios WHERE LOWER(email) = %s;", (email_clean,))
            user_row = cur.fetchone()
            is_admin = user_row and user_row[0] == "admin"

            if is_admin:
                cur.execute("""
                    SELECT id::text, nombre, anio_graduacion, activa
                    FROM promociones
                    ORDER BY anio_graduacion DESC, nombre ASC;
                """)
            else:
                cur.execute("""
                    SELECT p.id::text, p.nombre, p.anio_graduacion, p.activa
                    FROM promociones p
                    JOIN usuario_promocion_acceso upa ON p.id = upa.promocion_id
                    WHERE LOWER(upa.usuario_email) = %s AND p.activa = true
                    ORDER BY p.anio_graduacion DESC, p.nombre ASC;
                """, (email_clean,))

            rows = cur.fetchall()
            promos = [
                {
                    "id": str(r[0]),
                    "nombre": r[1],
                    "anio_graduacion": r[2],
                    "activa": bool(r[3]),
                }
                for r in rows
            ]
            return promos
    finally:
        conn.close()


def create_new_promotion(nombre: str, anio_graduacion: int, docente_emails: List[str]) -> Optional[Dict]:
    """Crea una nueva promoción limpia en Supabase y asigna los accesos requeridos a los docentes."""
    conn = _get_db_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cur:
            # 1. Insertar promoción
            cur.execute("""
                INSERT INTO promociones (nombre, anio_graduacion, activa)
                VALUES (%s, %s, true)
                RETURNING id::text, nombre, anio_graduacion, activa;
            """, (nombre.strip(), anio_graduacion))
            promo_row = cur.fetchone()
            promo_id = promo_row[0]

            # 2. Asignar accesos a docentes
            # Asegurar que el admin siempre tenga acceso explícito
            emails_set = {e.strip().lower() for e in docente_emails if e and e.strip()}
            emails_set.add("juan.serrano@aspaen.edu.co")

            for email in sorted(emails_set):
                cur.execute("""
                    INSERT INTO usuario_promocion_acceso (usuario_email, promocion_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                """, (email, promo_id))

        conn.commit()
        return {
            "id": promo_id,
            "nombre": promo_row[1],
            "anio_graduacion": promo_row[2],
            "activa": promo_row[3],
        }
    finally:
        conn.close()


def delete_promotion_for_test(promo_id: str) -> bool:
    """Borra una promoción de prueba (y en cascada sus datos) para limpieza de pruebas sintéticas."""
    conn = _get_db_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM promociones WHERE id = %s;", (promo_id,))
        conn.commit()
        return True
    finally:
        conn.close()
