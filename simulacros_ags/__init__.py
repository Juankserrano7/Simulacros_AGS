"""Dashboard de Simulacros PreIcfes AGS - Aspaen Saucará."""

__version__ = "2.0.0"

from .config import LOGO_PATH, MATERIAS, MAX_UPLOAD_MB, PBKDF2_ITERATIONS
from .core_utils import (
    calculate_icfes_scores,
    get_db_connection,
    normalize_student_name,
    record_audit_log,
    sanitize_score,
)

__all__ = [
    "__version__",
    "LOGO_PATH",
    "MATERIAS",
    "MAX_UPLOAD_MB",
    "PBKDF2_ITERATIONS",
    "get_db_connection",
    "normalize_student_name",
    "sanitize_score",
    "calculate_icfes_scores",
    "record_audit_log",
]
