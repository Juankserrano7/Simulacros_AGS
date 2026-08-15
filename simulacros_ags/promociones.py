"""Módulo para la gestión y autorización de promociones (cohortes académicas).

Permite el aislamiento multi-promoción y configuración de salones.
"""

from typing import Dict, List, Optional, Tuple

from .core_utils import get_db_connection


def _ensure_promociones_schema(conn) -> None:
    """Asegura la presencia de la columna `num_salones` en la tabla `promociones`."""
    try:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE promociones ADD COLUMN IF NOT EXISTS num_salones INTEGER DEFAULT 1;")
        conn.commit()
    except Exception:
        conn.rollback()


def get_salones_for_promotion(num_salones: int) -> List[str]:
    """Genera la lista de salones según el conteo de la promoción (1 -> ['11'], 2 -> ['11A', '11B'], etc)."""
    if not num_salones or num_salones <= 1:
        return ["11"]
    return [f"11{chr(65 + i)}" for i in range(min(num_salones, 26))]


def get_user_promotions(user_email: str) -> List[Dict]:
    """Devuelve la lista de promociones a las que el usuario logueado tiene acceso autorizado."""
    conn = get_db_connection()
    if not conn:
        return [{"id": "default", "nombre": "Grado 11 2025/2026", "anio_graduacion": 2026, "activa": True, "num_salones": 1}]

    try:
        _ensure_promociones_schema(conn)
        email_clean = user_email.strip().lower()
        with conn.cursor() as cur:
            cur.execute("SELECT rol FROM usuarios WHERE LOWER(email) = %s;", (email_clean,))
            user_row = cur.fetchone()
            is_admin = bool(user_row and user_row[0] == "admin")

            if is_admin:
                cur.execute("""
                    SELECT id::text, nombre, anio_graduacion, activa, COALESCE(num_salones, 1)
                    FROM promociones
                    ORDER BY anio_graduacion DESC, nombre ASC;
                """)
            else:
                cur.execute("""
                    SELECT p.id::text, p.nombre, p.anio_graduacion, p.activa, COALESCE(p.num_salones, 1)
                    FROM promociones p
                    JOIN usuario_promocion_acceso upa ON p.id = upa.promocion_id
                    WHERE LOWER(upa.usuario_email) = %s AND p.activa = true
                    ORDER BY p.anio_graduacion DESC, p.nombre ASC;
                """, (email_clean,))

            rows = cur.fetchall()
            return [
                {
                    "id": str(r[0]),
                    "nombre": r[1],
                    "anio_graduacion": r[2],
                    "activa": bool(r[3]),
                    "num_salones": r[4] if len(r) > 4 else 1,
                }
                for r in rows
            ]
    finally:
        conn.close()


def create_new_promotion(
    nombre: str,
    anio_graduacion: int,
    num_salones: int = 1,
    docente_emails: Optional[List[str]] = None
) -> Optional[Dict]:
    """Crea una nueva promoción limpia en Supabase y asigna los accesos a los docentes."""
    conn = get_db_connection()
    if not conn:
        return None

    docente_emails = docente_emails or []

    try:
        _ensure_promociones_schema(conn)
        with conn.cursor() as cur:
            # 1. Insertar promoción
            cur.execute("""
                INSERT INTO promociones (nombre, anio_graduacion, num_salones, activa)
                VALUES (%s, %s, %s, true)
                RETURNING id::text, nombre, anio_graduacion, num_salones, activa;
            """, (nombre.strip(), anio_graduacion, max(1, num_salones)))
            promo_row = cur.fetchone()
            promo_id = promo_row[0]

            # 2. Asignar accesos a docentes
            emails_set = {e.strip().lower() for e in docente_emails if e and e.strip()}

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
            "num_salones": promo_row[3],
            "activa": promo_row[4],
        }
    finally:
        conn.close()


def update_promotion(promo_id: str, nombre: str, anio_graduacion: int, num_salones: int) -> Tuple[bool, str]:
    """Actualiza datos y número de salones de una promoción en Supabase."""
    conn = get_db_connection()
    if not conn:
        return False, "Sin conexión a Supabase."

    try:
        _ensure_promociones_schema(conn)
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE promociones
                SET nombre = %s, anio_graduacion = %s, num_salones = %s
                WHERE id = %s;
            """, (nombre.strip(), anio_graduacion, max(1, num_salones), promo_id))
        conn.commit()
        return True, f"Promoción '{nombre.strip()}' actualizada exitosamente."
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        return False, f"Error actualizando promoción: {exc}"
    finally:
        conn.close()


def delete_promotion_for_test(promo_id: str) -> bool:
    """Borra una promoción de prueba (y en cascada sus datos) para pruebas sintéticas."""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM promociones WHERE id = %s;", (promo_id,))
        conn.commit()
        return True
    finally:
        conn.close()
