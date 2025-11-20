import base64
import hashlib
import hmac
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st

from .config import AUTH_USERS_FILE, LOGO_PATH, PBKDF2_ITERATIONS


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
            return username.title()
        return " ".join(part.capitalize() for part in parts)
    except Exception:
        return email


def load_auth_users(path: str | Path = AUTH_USERS_FILE) -> Dict[str, dict]:
    """Lee el almacén de credenciales PBKDF2 desde CSV."""
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        st.error(
            f"No se encontró el archivo de credenciales ({path}). "
            "Ejecuta scripts/sync_profesores.py para generarlo."
        )
        return {}

    required_cols = {"email", "salt", "password_hash", "activo"}
    if not required_cols.issubset(df.columns):
        st.error(
            "El archivo de autenticación no contiene las columnas requeridas: "
            f"{', '.join(required_cols)}"
        )
        return {}

    df["email"] = df["email"].str.strip().str.lower()

    def as_bool(value):
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "1", "yes", "si")

    return {
        row["email"]: {
            "salt": row["salt"],
            "password_hash": str(row["password_hash"]),
            "activo": as_bool(row["activo"]),
        }
        for _, row in df.iterrows()
        if isinstance(row["email"], str) and row["email"]
    }


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
