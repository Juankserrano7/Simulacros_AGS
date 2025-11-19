#!/usr/bin/env python3
"""
Sincroniza el listado de profesores y sus contraseñas en texto plano
con un almacén de autenticación basado en hashes PBKDF2.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Tuple

DEFAULT_EMAILS = Path("listado_correeos_profes.txt")
DEFAULT_PASSWORDS = Path("claves.txt")
DEFAULT_OUTPUT = Path("auth_users.csv")
PBKDF2_ITERATIONS = 390000


def load_emails(path: Path) -> Iterable[str]:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de correos: {path}")
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            email = line.strip().lower()
            if not email:
                continue
            if "@aspaen.edu.co" not in email:
                raise ValueError(f"Correo fuera del dominio permitido: {email}")
            yield email


def load_passwords(path: Path) -> Dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de claves: {path}")
    mapping: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            email, password = [part.strip() for part in line.split(":", 1)]
            if not email or not password:
                continue
            mapping[email.lower()] = password
    return mapping


def hash_password(password: str, salt: bytes | None = None) -> Tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return salt.hex(), hashed.hex()


def sync_auth_store(emails: Iterable[str], passwords: Dict[str, str], output: Path):
    rows = []
    now = datetime.now(timezone.utc).isoformat()
    for email in emails:
        if email not in passwords:
            raise ValueError(f"No se encontró una contraseña para {email} en claves.txt")
        salt_hex, hash_hex = hash_password(passwords[email])
        rows.append(
            {
                "email": email,
                "salt": salt_hex,
                "password_hash": hash_hex,
                "activo": True,
                "ultima_actualizacion": now,
            }
        )

    with output.open("w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(
            csvfile, fieldnames=rows[0].keys() if rows else [], extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera auth_users.csv desde el listado de correos y claves."
    )
    parser.add_argument(
        "--emails",
        type=Path,
        default=DEFAULT_EMAILS,
        help="Ruta del archivo con correos (uno por línea).",
    )
    parser.add_argument(
        "--passwords",
        type=Path,
        default=DEFAULT_PASSWORDS,
        help="Ruta del archivo con claves 'correo: password'.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Archivo CSV que se generará con los hashes.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    emails = list(load_emails(args.emails))
    passwords = load_passwords(args.passwords)
    if not emails:
        raise ValueError("No se encontraron correos válidos.")
    sync_auth_store(emails, passwords, args.output)
    print(f"Se sincronizaron {len(emails)} usuarios en {args.output}.")


if __name__ == "__main__":
    main()
