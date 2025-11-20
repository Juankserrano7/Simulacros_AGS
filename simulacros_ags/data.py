import pandas as pd
import streamlit as st

from .config import DATA_FILES


def _clean_student_frame(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip()
    df["ESTUDIANTE"] = df["ESTUDIANTE"].str.strip()

    df = df[df["ESTUDIANTE"].notna()]
    df = df[df["ESTUDIANTE"] != ""]
    df = df[~df["ESTUDIANTE"].str.upper().str.contains("PROMEDIO", na=False)]
    df = df[~df["ESTUDIANTE"].str.upper().str.contains("TOTAL", na=False)]
    df = df[~df["ESTUDIANTE"].str.upper().str.contains("MEDIA", na=False)]
    df = df.drop_duplicates(subset=["ESTUDIANTE"], keep="first")

    return df.reset_index(drop=True)


@st.cache_data
def load_datasets():
    """Carga y limpia los tres simulacros esperados."""
    try:
        datasets = {}
        for label, path in DATA_FILES.items():
            raw_df = pd.read_csv(path, skiprows=1)
            datasets[label] = _clean_student_frame(raw_df)
        return datasets.get("Helmer Pardo 1"), datasets.get("Helmer Pardo 2"), datasets.get("AVANCEMOS")
    except Exception as exc:
        st.error(f"Error al cargar los archivos: {exc}")
        st.info("Asegúrate de que los archivos CSV estén en el mismo directorio que el script.")
        return None, None, None
