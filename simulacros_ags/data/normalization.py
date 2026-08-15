"""Módulo de normalización, sanitización y validación de esquemas de datos de simulacros."""

from pathlib import Path
from typing import List

import pandas as pd

from ..config import MATERIAS
from ..core_utils import normalize_student_name

REQUIRED_COLUMNS = ["ESTUDIANTE", "PROMEDIO PONDERADO"] + MATERIAS
OPTIONAL_NUMERIC = ["PROMEDIO SIMPLE", "DESVIACIÓN ESTÁNDAR", "PP POR MATERIA"]

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


def get_regular_presented_df(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica el protocolo institucional: Excluye estudiantes de inclusión y ausentes."""
    if df is None or df.empty:
        return pd.DataFrame()
    res = df.copy()
    if "es_inclusion" in res.columns:
        res = res[res["es_inclusion"] == False]  # noqa: E712
    if "PROMEDIO PONDERADO" in res.columns:
        res = res[res["PROMEDIO PONDERADO"].notna()]
    return res


def _canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza encabezados al formato esperado (acentos y mayúsculas canónicas)."""
    new_cols = [COLUMN_CANONICAL_MAP.get(str(col).strip().lower(), str(col).strip()) for col in df.columns]
    df.columns = new_cols
    return df


def _clean_student_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitiza y normaliza un DataFrame de estudiantes."""
    df = _canonicalize_columns(df)
    df["ESTUDIANTE"] = df["ESTUDIANTE"].apply(normalize_student_name)
    df = df[df["ESTUDIANTE"].notna() & (df["ESTUDIANTE"] != "")]
    # Excluir posibles filas de totales o medias agregadas
    df = df[~df["ESTUDIANTE"].str.contains("PROMEDIO", na=False)]
    df = df[~df["ESTUDIANTE"].str.contains("TOTAL", na=False)]
    df = df[~df["ESTUDIANTE"].str.contains("MEDIA", na=False)]
    return df.drop_duplicates(subset=["ESTUDIANTE"], keep="first").reset_index(drop=True)


def _try_read_file(path: Path) -> pd.DataFrame:
    """Lee un archivo Excel o CSV probando con y sin encabezado de salto."""
    suffix = path.suffix.lower()
    is_excel = suffix in (".xlsx", ".xls")
    readers = (
        [lambda: pd.read_excel(path, skiprows=1), lambda: pd.read_excel(path)]
        if is_excel
        else [lambda: pd.read_csv(path, skiprows=1), lambda: pd.read_csv(path)]
    )

    last_exc = None
    for reader in readers:
        try:
            df = reader()
            if "ESTUDIANTE" in df.columns:
                return df
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue
    if last_exc:
        raise last_exc
    raise ValueError("No se pudo leer el archivo del simulacro.")


def _validate_schema(df: pd.DataFrame) -> List[str]:
    """Valida la presencia de columnas requeridas y su formato numérico."""
    errores: List[str] = []
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        errores.append(f"Faltan las columnas requeridas: {', '.join(missing)}")

    for col in [c for c in REQUIRED_COLUMNS + OPTIONAL_NUMERIC if c != "ESTUDIANTE" and c in df.columns]:
        try:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if df[col].isna().all():
                errores.append(f"La columna '{col}' no contiene valores numéricos válidos.")
        except Exception as exc:  # noqa: BLE001
            errores.append(f"No se pudo convertir la columna '{col}' a número ({exc}).")

    return errores
