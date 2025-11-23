from io import BytesIO
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

from .ai import generate_ai_insights
from .config import MATERIAS, MAX_UPLOAD_MB, TEMPLATE_FILE, UPLOADS_DIR, METADATA_FILE
from .storage import (
    bootstrap_metadata,
    get_simulacros_metadata,
    mark_estado,
    register_simulacro,
    upsert_insights,
    update_simulacro,
)
from .git_sync import push_changes, has_push_config

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


def _canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza encabezados al formato esperado (acentos, mayúsculas)."""
    new_cols = []
    for col in df.columns:
        key = str(col).strip().lower()
        new_cols.append(COLUMN_CANONICAL_MAP.get(key, str(col).strip()))
    df.columns = new_cols
    return df


def _clean_student_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = _canonicalize_columns(df)
    df["ESTUDIANTE"] = df["ESTUDIANTE"].astype(str).str.strip()
    df["ESTUDIANTE"] = df["ESTUDIANTE"].apply(
        lambda s: unicodedata.normalize("NFKD", s)
        .encode("ascii", "ignore")
        .decode()
        .upper()
        .replace("-", " ")
    )
    df["ESTUDIANTE"] = df["ESTUDIANTE"].str.replace(r"[^A-Z0-9 ]+", " ", regex=True)
    df["ESTUDIANTE"] = df["ESTUDIANTE"].str.replace(r"\s+", " ", regex=True).str.strip()
    # Normalización específica de D'SILVA / D SILVA a DSILVA
    df["ESTUDIANTE"] = df["ESTUDIANTE"].str.replace("D SILVA", "DSILVA", regex=False)
    df["ESTUDIANTE"] = df["ESTUDIANTE"].str.replace("D  SILVA", "DSILVA", regex=False)
    df.loc[df["ESTUDIANTE"].str.lower() == "nan", "ESTUDIANTE"] = ""

    df = df[df["ESTUDIANTE"].notna()]
    df = df[df["ESTUDIANTE"] != ""]
    df = df[~df["ESTUDIANTE"].str.upper().str.contains("PROMEDIO", na=False)]
    df = df[~df["ESTUDIANTE"].str.upper().str.contains("TOTAL", na=False)]
    df = df[~df["ESTUDIANTE"].str.upper().str.contains("MEDIA", na=False)]
    df = df.drop_duplicates(subset=["ESTUDIANTE"], keep="first")

    return df.reset_index(drop=True)


def _try_read_file(path: Path) -> pd.DataFrame:
    readers = []
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        readers = [lambda: pd.read_excel(path, skiprows=1), lambda: pd.read_excel(path)]
    else:
        readers = [lambda: pd.read_csv(path, skiprows=1), lambda: pd.read_csv(path)]

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
    errores: List[str] = []
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        errores.append(f"Faltan las columnas requeridas: {', '.join(missing)}")

    for col in [c for c in REQUIRED_COLUMNS + OPTIONAL_NUMERIC if c not in ["ESTUDIANTE"] and c in df.columns]:
        try:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if df[col].isna().all():
                errores.append(f"La columna '{col}' no contiene valores numéricos válidos.")
        except Exception as exc:  # noqa: BLE001
            errores.append(f"No se pudo convertir la columna '{col}' a número ({exc}).")

    return errores


@st.cache_data
def load_all_simulacros() -> Tuple[List[Dict], Dict[str, Dict], List[str]]:
    """Carga todos los simulacros declarados en metadatos y devuelve los dataframes limpios."""
    if not METADATA_FILE.exists():
        bootstrap_metadata()
    metadatos = get_simulacros_metadata()
    data_map: Dict[str, Dict] = {}
    errores: List[str] = []

    for sim in metadatos:
        sim_id = sim.get("id")
        path = Path(sim.get("path", ""))
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            errores.append(f"{sim.get('nombre', sim_id)}: no se encontró el archivo en {path}.")
            mark_estado(sim_id, "missing", errores=[f"Archivo no encontrado: {path}"])
            continue
        try:
            raw_df = _try_read_file(path)
            df = _clean_student_frame(raw_df)
            schema_errors = _validate_schema(df)
            if schema_errors:
                errores.extend([f"{sim.get('nombre', sim_id)}: {msg}" for msg in schema_errors])
                mark_estado(sim_id, "failed", errores=schema_errors)
                continue
            sim["estado"] = "ready"
            sim["errores"] = []
            sim["path"] = str(path)
            mark_estado(sim_id, "ready", errores=[])
            data_map[sim_id] = {"meta": sim, "df": df}
        except Exception as exc:  # noqa: BLE001
            error_msg = f"{sim.get('nombre', sim_id)}: error al cargar -> {exc}"
            errores.append(error_msg)
            mark_estado(sim_id, "failed", errores=[str(exc)])
            continue
    return metadatos, data_map, errores


def ensure_template_file() -> Path:
    """Genera el archivo de plantilla (se reescribe siempre para incorporar cambios)."""
    if TEMPLATE_FILE.exists():
        TEMPLATE_FILE.unlink(missing_ok=True)

    from openpyxl import Workbook

    TEMPLATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    from openpyxl.utils import get_column_letter

    ws = wb.active
    ws.title = "Simulacro"
    headers = [
        "ESTUDIANTE",
        "GRADO",
        "LECTURA CRITICA",
        "MATEMATICAS",
        "SOCIALES Y CIUDADANAS",
        "CIENCIAS NATURALES",
        "INGLES",
        "PROMEDIO SIMPLE",
        "PROMEDIO PONDERADO",
        "DESV. ESTANDAR",
        "PP POR MATERIA",
    ]
    ws.append(headers)
    # Estudiantes prellenados sin valores numéricos
    estudiantes = [
        "ALVIAR MERCHAN JUAN NICOLAS",
        "BARBOSA REY MATEO",
        "CALDERON ARDILA GUIDO ARTURO",
        "CASTRO OSORIO JUAN DIEGO",
        "DELGADO ABRIL ALEJANDRO",
        "DSILVA ROSAS ALEJANDRO PABLO",
        "DURAN TORRES JUAN SEBASTIAN",
        "ESPITIA CASTRO NELSON ANDRES",
        "GARCIA ESCOBAR ESTEBAN",
        "GARCIA ZAMBRANO SAMUEL EDUARD",
        "HAZBON HERNANDEZ MANUEL FELIPE",
        "JACOME REYES ALEJANDRO",
        "MANOSALVA DURAN JUAN DIEGO",
        "MELCHIORE QUINTERO JUAN FERNANDO",
        "MUJICA ARDILA NELSON DAVID",
        "PALACIOS GOMEZ CAMILO",
        "PARRA LINARES DANIEL EDUARDO",
        "QUINTERO OROZCO SANTIAGO",
        "RANGEL CAMACHO JERONIMO",
        "REY ROJAS JUAN JOSE",
        "SALCEDO VALDIVIESO JUAN RAFAEL",
        "SANABRIA TORRES NICOLAS",
        "SERRANO MESA JERONIMO",
        "SUAREZ DURAN TOMAS",
        "TORRES ORDUZ TOMÁS",
        "TORRES RIOS EMMANUEL",
        "TORRES RODRIGUEZ ALVARO SEBASTIAN",
        "VALDERRAMA TORRES JUAN JOSE",
        "VILLAMIZAR NAVARRO JUAN JOSE",
        "VISBAL MONDRAGON NICOLAS",
    ]
    # Prellenamos estudiantes y agregamos fórmulas para promedios
    col_map = {name: get_column_letter(idx + 1) for idx, name in enumerate(headers)}
    for row_idx, est in enumerate(estudiantes, start=2):
        ws.append([est] + [""] * (len(headers) - 1))
        # Promedio simple: suma de las materias
        ws[f"{col_map['PROMEDIO SIMPLE']}{row_idx}"] = (
            f"=SUM({col_map['LECTURA CRITICA']}{row_idx}:{col_map['INGLES']}{row_idx})"
        )
        # Promedio ponderado por materia
        ws[f"{col_map['PP POR MATERIA']}{row_idx}"] = (
            f"=(({col_map['LECTURA CRITICA']}{row_idx}*3)"
            f"+({col_map['MATEMATICAS']}{row_idx}*3)"
            f"+({col_map['SOCIALES Y CIUDADANAS']}{row_idx}*3)"
            f"+({col_map['CIENCIAS NATURALES']}{row_idx}*3)"
            f"+({col_map['INGLES']}{row_idx}*1))/13"
        )
        # Promedio ponderado
        ws[f"{col_map['PROMEDIO PONDERADO']}{row_idx}"] = f"={col_map['PP POR MATERIA']}{row_idx}*5"
        # Desviación estándar de las materias
        ws[f"{col_map['DESV. ESTANDAR']}{row_idx}"] = (
            f"=STDEV.S({col_map['LECTURA CRITICA']}{row_idx}:{col_map['INGLES']}{row_idx})"
        )

    # Formato de tabla
    from openpyxl.worksheet.table import Table, TableStyleInfo

    total_rows = 1 + len(estudiantes)  # encabezado + filas
    table_ref = f"A1:K{total_rows}"
    table = Table(displayName="SimulacroTabla", ref=table_ref)
    style = TableStyleInfo(
        name="TableStyleMedium9",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    table.tableStyleInfo = style
    ws.add_table(table)

    ws_ins = wb.create_sheet("Instrucciones")
    ws_ins["A1"] = "Instrucciones"
    ws_ins["A2"] = "- No cambies los nombres de las columnas."
    ws_ins["A3"] = "- Ingresa un estudiante por fila."
    ws_ins["A4"] = "- Las materias y los promedios deben ser numéricos."
    ws_ins["A5"] = "- Puedes dejar PROMEDIO SIMPLE, DESV. ESTANDAR y PP POR MATERIA si no los calculas; el sistema usará PROMEDIO PONDERADO."

    wb.save(TEMPLATE_FILE)
    return TEMPLATE_FILE


def ingest_simulacro_excel(nombre: str, file_buffer: BytesIO, usuario: str) -> Tuple[bool, str, Dict]:
    """Valida y almacena un nuevo simulacro cargado por Excel."""
    if not nombre or not nombre.strip():
        return False, "Debes indicar un nombre para el simulacro.", {}

    file_buffer.seek(0, 2)
    size_mb = file_buffer.tell() / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        return False, f"El archivo excede el límite de {MAX_UPLOAD_MB} MB.", {}
    file_buffer.seek(0)

    try:
        df_raw = pd.read_excel(file_buffer)
    except Exception as exc:  # noqa: BLE001
        return False, f"No se pudo leer el Excel: {exc}", {}

    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    df = _clean_student_frame(df_raw)
    errores = _validate_schema(df)
    if errores:
        return False, "; ".join(errores), {}

    registro = register_simulacro(nombre.strip(), path=Path("pendiente"), creado_por=usuario)
    sim_id = registro["id"]
    destino = UPLOADS_DIR / f"{sim_id}.csv"
    try:
        df.to_csv(destino, index=False)
        update_simulacro(sim_id, path=str(destino))
        insights = generate_ai_insights(nombre.strip(), df, materias=MATERIAS)
        upsert_insights(sim_id, insights)
        mark_estado(sim_id, "ready", errores=[])
        if has_push_config():
            push_changes(destino, f"chore: add simulacro {nombre.strip()}")
        st.cache_data.clear()
        return True, "Simulacro cargado correctamente.", registro
    except Exception as exc:  # noqa: BLE001
        mark_estado(sim_id, "failed", errores=[str(exc)])
        return False, f"Error al guardar el archivo: {exc}", registro


def ordenar_simulacros(data_map: Dict[str, Dict]) -> List[Dict]:
    """Convierte el mapa de datos en una lista ordenada por fecha de creación."""
    simulacros = []
    for sim_id, payload in data_map.items():
        meta = payload.get("meta", {})
        meta.setdefault("id", sim_id)
        simulacros.append(
            {
                "id": sim_id,
                "nombre": meta.get("nombre", sim_id),
                "meta": meta,
                "df": payload.get("df"),
            }
        )
    simulacros.sort(key=lambda s: s["meta"].get("creado_en", s["nombre"]))
    return simulacros


def get_or_generate_insights(sim_entry: Dict) -> Dict:
    """Devuelve los insights guardados o los genera y persiste si no existen."""
    meta = sim_entry.get("meta", {})
    insights = meta.get("insights") or {}
    if insights:
        return insights
    df = sim_entry.get("df")
    nombre = meta.get("nombre", meta.get("id", "Simulacro"))
    nuevo = generate_ai_insights(nombre, df, materias=MATERIAS)
    upsert_insights(sim_entry.get("id"), nuevo)
    st.cache_data.clear()
    return nuevo
