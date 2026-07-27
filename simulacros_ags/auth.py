import base64
import hashlib
import hmac
import os
from pathlib import Path
from typing import Dict
import psycopg2
import streamlit as st

from .config import LOGO_PATH, PBKDF2_ITERATIONS


def load_logo_base64(path: str | Path = LOGO_PATH) -> str:
    """Carga el logo y lo convierte a base64 para uso en la UI."""
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        return ""


def format_name_from_email(email: str) -> str:
    """Genera un nombre legible a partir del correo institucional."""
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
    """Consulta el rol real del usuario desde Supabase ('admin' o 'docente')."""
    if not email:
        return "docente"
    email_clean = email.strip().lower()
    db_url = os.getenv("SUPABASE_DB_URL")
    if db_url:
        try:
            conn = psycopg2.connect(db_url)
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT rol FROM usuarios WHERE LOWER(email) = %s AND activo = true;", (email_clean,))
                    row = cur.fetchone()
                    if row and row[0]:
                        return str(row[0]).strip().lower()
            finally:
                conn.close()
        except Exception:
            pass
    if email_clean == "juan.serrano@aspaen.edu.co":
        return "admin"
    return "docente"


def load_auth_users_from_db(db_url: str) -> Dict[str, dict]:
    """Carga usuarios directamente desde la tabla `usuarios` en Supabase."""
    conn = psycopg2.connect(db_url)
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
    """Carga credenciales preferentemente desde Supabase (tabla usuarios)."""
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        st.error("No se encontró la variable de entorno SUPABASE_DB_URL para la autenticación.")
        return {}
    try:
        return load_auth_users_from_db(db_url)
    except Exception as exc:
        st.error(f"Error al conectar con la base de datos de usuarios en Supabase: {exc}")
        return {}


def verify_credentials(email: str, password: str, users: Dict[str, dict]) -> bool:
    """Valida credenciales usando PBKDF2 y compara de forma segura."""
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
