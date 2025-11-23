from pathlib import Path

AUTH_USERS_FILE = Path("auth_users.csv")
LOGO_PATH = Path("Logo.png")
PBKDF2_ITERATIONS = 390000

DATA_ROOT = Path("simulacros_data")
UPLOADS_DIR = DATA_ROOT / "uploads"
METADATA_FILE = DATA_ROOT / "simulacros_metadata.json"
TEMPLATE_FILE = DATA_ROOT / "plantilla_simulacro.xlsx"
MAX_UPLOAD_MB = 12
UPLOAD_ALLOWED_USER = "juan.serrano@aspaen.edu.co"

DEFAULT_SIMULACROS = [
    {"id": "hp1", "nombre": "Helmer Pardo 1", "path": Path("HELMER_PARDO1.csv"), "origen": "semilla"},
    {"id": "hp2", "nombre": "Helmer Pardo 2", "path": Path("HELMER_PARDO2.csv"), "origen": "semilla"},
    {"id": "avan", "nombre": "AVANCEMOS", "path": Path("PREPARATE.csv"), "origen": "semilla"},
]

MATERIAS = [
    "LECTURA CRÍTICA",
    "MATEMÁTICAS",
    "SOCIALES Y CIUDADANAS",
    "CIENCIAS NATURALES",
    "INGLÉS",
]
