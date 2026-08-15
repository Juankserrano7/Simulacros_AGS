"""Utilidades transversales y funciones puras para el sistema de simulacros AGS."""

import json
import os
import re
import unicodedata
from typing import Any, Dict, Optional, Tuple

import numpy as np
import psycopg2
from dotenv import load_dotenv

from .config import MATERIAS

load_dotenv()


def get_db_connection() -> Optional[psycopg2.extensions.connection]:
    """Crea y retorna una nueva conexión a la base de datos PostgreSQL/Supabase.
    
    Returns:
        psycopg2 connection si SUPABASE_DB_URL está definida y la conexión es exitosa,
        None en caso contrario.
    """
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        return None
    try:
        return psycopg2.connect(db_url)
    except Exception:
        return None


def normalize_student_name(name: Any) -> str:
    """Normaliza de forma canónica el nombre de un estudiante.
    
    - Elimina acentos y diacríticos.
    - Convierte a mayúsculas.
    - Estandariza casos especiales (ej: D'SILVA / D SILVA -> DSILVA).
    - Colapsa espacios múltiples y elimina caracteres no alfanuméricos.
    """
    if not isinstance(name, str) or not name.strip():
        return ""
    
    # Quitar acentos / diacríticos
    normalized = (
        unicodedata.normalize("NFKD", name)
        .encode("ascii", "ignore")
        .decode()
        .upper()
        .replace("-", " ")
    )
    # Limpiar caracteres especiales dejando sólo letras, números y espacios
    clean = re.sub(r"[^A-Z0-9 ]+", " ", normalized)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Manejo de variaciones de apellidos compuestos
    clean = re.sub(r"\bD\s+SILVA\b", "DSILVA", clean)
    
    return clean if clean.lower() != "nan" else ""


def sanitize_score(value: Any, min_val: float = 0.0, max_val: float = 100.0, default: Optional[float] = 0.0) -> Optional[float]:
    """Convierte de forma segura un valor a flotante y lo acota entre min_val y max_val.
    
    Args:
        value: Valor de entrada (str, int, float, None).
        min_val: Límite inferior permitido.
        max_val: Límite superior permitido.
        default: Valor por defecto si es nulo o inválido.
        
    Returns:
        float acotado o default si la conversión falla.
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return default
    try:
        num = float(value)
        if np.isnan(num):
            return default
        return max(min_val, min(max_val, num))
    except (ValueError, TypeError):
        return default


def calculate_icfes_scores(
    subject_scores: Dict[str, Optional[float]],
    custom_global: Optional[float] = None
) -> Tuple[float, float, float]:
    """Aplica las fórmulas institucionales y oficiales del ICFES Saber 11.
    
    Pesos ICFES:
        - Lectura Crítica: 3
        - Matemáticas: 3
        - Sociales y Ciudadanas: 3
        - Ciencias Naturales: 3
        - Inglés: 1
        - Suma de ponderadores: 13
        
    Returns:
        Tuple[float, float, float]: (promedio_simple, puntaje_global_ponderado, desviacion_estandar)
    """
    lc = sanitize_score(subject_scores.get("LECTURA CRÍTICA"), 0.0, 100.0, 0.0) or 0.0
    mat = sanitize_score(subject_scores.get("MATEMÁTICAS"), 0.0, 100.0, 0.0) or 0.0
    soc = sanitize_score(subject_scores.get("SOCIALES Y CIUDADANAS"), 0.0, 100.0, 0.0) or 0.0
    cn = sanitize_score(subject_scores.get("CIENCIAS NATURALES"), 0.0, 100.0, 0.0) or 0.0
    ing = sanitize_score(subject_scores.get("INGLÉS"), 0.0, 100.0, 0.0) or 0.0

    promedio_simple = lc + mat + soc + cn + ing
    pp_materia = ((lc * 3.0) + (mat * 3.0) + (soc * 3.0) + (cn * 3.0) + (ing * 1.0)) / 13.0

    if custom_global is not None:
        try:
            custom_num = float(custom_global)
            puntaje_global = custom_num if (custom_num > 0 and not np.isnan(custom_num)) else (pp_materia * 5.0)
        except (ValueError, TypeError):
            puntaje_global = pp_materia * 5.0
    else:
        puntaje_global = pp_materia * 5.0

    scores_list = [lc, mat, soc, cn, ing]
    desviacion_estandar = float(np.std(scores_list, ddof=1)) if len(scores_list) > 1 else 0.0

    return (
        round(promedio_simple, 2),
        round(puntaje_global, 2),
        round(desviacion_estandar, 2),
    )


def record_audit_log(
    cur,
    user_email: str,
    action_type: str,
    table_name: str,
    record_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Registra una entrada en la tabla auditoria_cambios sin interrumpir el flujo principal."""
    try:
        cur.execute("""
            INSERT INTO auditoria_cambios (usuario_email, tipo_accion, tabla_afectada, registro_id, detalles, creado_en)
            VALUES (%s, %s, %s, %s, %s::jsonb, now());
        """, (
            user_email.strip().lower() if user_email else "sistema",
            action_type.strip().upper(),
            table_name.strip().lower(),
            str(record_id) if record_id else None,
            json.dumps(details or {})
        ))
    except Exception:
        # La auditoría es no bloqueante
        pass
