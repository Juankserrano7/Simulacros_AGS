"""Módulo de autenticación y autorización para simulacros AGS.

Maneja hashes PBKDF2, roles de usuario en Supabase y registro de accesos.
"""

import base64
import hashlib
import hmac
from pathlib import Path
from typing import Dict, Union

import streamlit as st

from .config import LOGO_PATH, PBKDF2_ITERATIONS
from .core_utils import get_db_connection


def load_logo_base64(path: Union[str, Path] = LOGO_PATH) -> str:
    """Carga el logo institucional y lo convierte a base64 para uso en la interfaz."""
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        return ""


def format_name_from_email(email: str) -> str:
    """Genera un nombre legible a partir del correo electrónico institucional."""
    if not email:
        return "Docente"
    try:
        username = email.split("@")[0]
        parts = [part for part in username.replace("_", " ").split(".") if part]
        if not parts:
            return str(username).title()
        return " ".join(part.capitalize() for part in parts)
    except Exception:
        return str(email)


def get_user_role(email: str) -> str:
    """Consulta el rol asignado al usuario desde Supabase ('admin' o 'docente')."""
    if not email:
        return "docente"
    email_clean = email.strip().lower()
    
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT rol FROM usuarios WHERE LOWER(email) = %s AND activo = true;",
                    (email_clean,)
                )
                row = cur.fetchone()
                if row and row[0]:
                    return str(row[0]).strip().lower()
        except Exception:
            pass
        finally:
            conn.close()

    return "docente"


def load_auth_users_from_db() -> Dict[str, dict]:
    """Carga usuarios activos desde la tabla `usuarios` en Supabase."""
    conn = get_db_connection()
    if not conn:
        return {}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email, salt, password_hash, activo, rol FROM usuarios WHERE activo = true;")
            rows = cur.fetchall()
            users = {}
            for email, salt, password_hash, activo, rol in rows:
                if email:
                    users[email.strip().lower()] = {
                        "salt": salt,
                        "password_hash": str(password_hash),
                        "activo": bool(activo),
                        "rol": rol or "docente",
                    }
            return users
    finally:
        conn.close()


@st.cache_data(ttl=60)
def load_auth_users() -> Dict[str, dict]:
    """Carga credenciales cacheadas desde Supabase."""
    try:
        return load_auth_users_from_db()
    except Exception as exc:
        st.error(f"Error al conectar con la base de datos de usuarios en Supabase: {exc}")
        return {}


def verify_credentials(email: str, password: str, users: Dict[str, dict]) -> bool:
    """Valida credenciales usando PBKDF2 y comparación en tiempo constante (hmac)."""
    user = users.get(email.lower())
    if not user or not user.get("activo"):
        return False
    try:
        salt_bytes = bytes.fromhex(str(user["salt"]))
    except ValueError:
        return False
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_bytes, PBKDF2_ITERATIONS
    ).hex()
    return hmac.compare_digest(hashed, str(user["password_hash"]))


def registrar_inicio_sesion(usuario_email: str, exitoso: bool = True, detalles: str = "Inicio de sesión exitoso"):
    """Registra un intento de inicio de sesión en la tabla inicios_sesion en Supabase."""
    if not usuario_email:
        return
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO inicios_sesion (usuario_email, exitoso, detalles)
                VALUES (%s, %s, %s);
            """, (usuario_email.strip().lower(), exitoso, detalles))
            conn.commit()
    except Exception:
        pass
    finally:
        conn.close()
