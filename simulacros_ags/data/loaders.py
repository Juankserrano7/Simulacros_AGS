"""Módulo de consultas de solo lectura y carga en caché de simulacros e ICFES Real desde Supabase."""

import json
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from ..ai import generate_ai_insights
from ..config import MATERIAS
from ..core_utils import get_db_connection
from .normalization import OPTIONAL_NUMERIC, REQUIRED_COLUMNS


@st.cache_data(ttl=60)
def load_all_simulacros(promocion_id: Optional[str] = None) -> Tuple[List[Dict], Dict[str, Dict], List[str]]:
    """Carga todos los simulacros e ICFES Real pertenecientes a la promoción activa desde Supabase."""
    metadatos: List[Dict] = []
    data_map: Dict[str, Dict] = {}
    errores: List[str] = []

    if not promocion_id:
        return metadatos, data_map, ["No se especificó la promoción activa."]

    conn = get_db_connection()
    if not conn:
        return metadatos, data_map, ["No hay conexión configurada a Supabase (SUPABASE_DB_URL)."]

    try:
        with conn.cursor() as cur:
            # 1. Consultar simulacros de la promoción
            cur.execute("""
                SELECT id, nombre, origen, estado, creado_por, creado_en, insights
                FROM simulacros
                WHERE promocion_id = %s
                ORDER BY creado_en ASC;
            """, (promocion_id,))
            simulacros_rows = cur.fetchall()

            if not simulacros_rows:
                # Verificar si existen notas de ICFES real aunque no haya simulacros de práctica
                df_icfes = load_icfes_real_data(promocion_id)
                if not df_icfes.empty:
                    data_map["icfes_real"] = {
                        "df": df_icfes,
                        "meta": {
                            "id": "icfes_real",
                            "nombre": "🎯 ICFES Real",
                            "origen": "oficial",
                            "estado": "ready",
                            "insights": {},
                            "creado_en": "2099-01-01"
                        }
                    }
                    metadatos.append(data_map["icfes_real"]["meta"])
                return metadatos, data_map, []

            # 2. Cargar resultados de cada simulacro
            for s_id, s_nom, s_orig, s_est, s_creadopor, s_creadoen, s_ins in simulacros_rows:
                meta = {
                    "id": str(s_id),
                    "nombre": s_nom,
                    "origen": s_orig,
                    "estado": s_est,
                    "creado_por": s_creadopor,
                    "creado_en": s_creadoen.isoformat() if hasattr(s_creadoen, "isoformat") else str(s_creadoen),
                    "insights": s_ins if isinstance(s_ins, dict) else (json.loads(s_ins) if s_ins else {})
                }
                metadatos.append(meta)

                cur.execute("""
                    SELECT 
                        e.nombre AS "ESTUDIANTE",
                        e.grado AS "GRADO",
                        e.es_inclusion,
                        rs.lectura_critica AS "LECTURA CRÍTICA",
                        rs.matematicas AS "MATEMÁTICAS",
                        rs.sociales_ciudadanas AS "SOCIALES Y CIUDADANAS",
                        rs.ciencias_naturales AS "CIENCIAS NATURALES",
                        rs.ingles AS "INGLÉS",
                        rs.promedio_simple AS "PROMEDIO SIMPLE",
                        rs.promedio_ponderado AS "PROMEDIO PONDERADO",
                        rs.desviacion_estandar AS "DESVIACIÓN ESTÁNDAR"
                    FROM estudiantes e
                    LEFT JOIN resultados_simulacro rs ON rs.estudiante_id = e.id AND rs.simulacro_id = %s
                    WHERE e.promocion_id = %s
                    ORDER BY e.nombre ASC;
                """, (s_id, promocion_id))
                res_rows = cur.fetchall()
                if res_rows:
                    cols = [
                        "ESTUDIANTE", "GRADO", "es_inclusion",
                        "LECTURA CRÍTICA", "MATEMÁTICAS", "SOCIALES Y CIUDADANAS",
                        "CIENCIAS NATURALES", "INGLÉS", "PROMEDIO SIMPLE",
                        "PROMEDIO PONDERADO", "DESVIACIÓN ESTÁNDAR"
                    ]
                    df_res = pd.DataFrame(res_rows, columns=cols)
                    for col in REQUIRED_COLUMNS + OPTIONAL_NUMERIC:
                        if col != "ESTUDIANTE" and col in df_res.columns:
                            df_res[col] = pd.to_numeric(df_res[col], errors="coerce")
                    data_map[str(s_id)] = {"df": df_res, "meta": meta}

            # 3. Incluir evaluación oficial ICFES Real si existe
            df_icfes = load_icfes_real_data(promocion_id)
            if not df_icfes.empty:
                data_map["icfes_real"] = {
                    "df": df_icfes,
                    "meta": {
                        "id": "icfes_real",
                        "nombre": "🎯 ICFES Real",
                        "origen": "oficial",
                        "estado": "ready",
                        "insights": {},
                        "creado_en": "2099-01-01"
                    }
                }
                metadatos.append(data_map["icfes_real"]["meta"])

            return metadatos, data_map, errores
    except Exception as exc:  # noqa: BLE001
        errores.append(f"Error consultando Supabase: {exc}")
        return metadatos, data_map, errores
    finally:
        conn.close()


@st.cache_data(ttl=60)
def load_icfes_real_data(promocion_id: Optional[str] = None) -> pd.DataFrame:
    """Carga los resultados reales del examen ICFES Saber 11 para la promoción activa."""
    if not promocion_id:
        return pd.DataFrame()

    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    e.nombre AS "ESTUDIANTE",
                    e.es_inclusion,
                    rir.lectura_critica AS "LECTURA CRÍTICA",
                    rir.matematicas AS "MATEMÁTICAS",
                    rir.sociales_ciudadanas AS "SOCIALES Y CIUDADANAS",
                    rir.ciencias_naturales AS "CIENCIAS NATURALES",
                    rir.ingles AS "INGLÉS",
                    rir.puntaje_global AS "PROMEDIO PONDERADO"
                FROM estudiantes e
                LEFT JOIN resultados_icfes_real rir ON rir.estudiante_id = e.id AND rir.promocion_id = %s
                WHERE e.promocion_id = %s
                ORDER BY e.nombre ASC;
            """, (promocion_id, promocion_id))
            rows = cur.fetchall()
            if not rows or not any(r[7] is not None for r in rows):
                return pd.DataFrame()

            cols = ["ESTUDIANTE", "es_inclusion", "LECTURA CRÍTICA", "MATEMÁTICAS", "SOCIALES Y CIUDADANAS", "CIENCIAS NATURALES", "INGLÉS", "PROMEDIO PONDERADO"]
            df = pd.DataFrame(rows, columns=cols)
            for col in cols[2:]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            if df["PROMEDIO PONDERADO"].dropna().empty:
                return pd.DataFrame()

            return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def ordenar_simulacros(data_map: Any = None) -> List[Dict]:
    """Convierte el mapa de datos (o la tupla retornada por load_all_simulacros) en una lista ordenada por fecha de creación."""
    if data_map is None:
        return []

    target_map = {}
    if isinstance(data_map, (tuple, list)):
        if len(data_map) >= 2 and isinstance(data_map[1], dict):
            target_map = data_map[1]
        elif len(data_map) > 0 and isinstance(data_map[0], dict) and "df" in data_map[0]:
            return list(data_map)
        else:
            return []
    elif isinstance(data_map, dict):
        target_map = data_map
    else:
        return []

    simulacros = []
    for sim_id, payload in target_map.items():
        if not isinstance(payload, dict):
            continue
        meta = payload.get("meta")
        if isinstance(meta, dict):
            meta_clean = dict(meta)
            meta_clean.setdefault("id", str(sim_id))
        else:
            meta_clean = {"id": str(sim_id), "nombre": str(sim_id)}
        simulacros.append({
            "id": str(sim_id),
            "nombre": str(meta_clean.get("nombre", sim_id)),
            "meta": meta_clean,
            "df": payload.get("df"),
        })

    def _sort_key(s):
        meta = s.get("meta") or {}
        return str(meta.get("creado_en") or s.get("nombre") or s.get("id") or "")

    simulacros.sort(key=_sort_key)
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
    
    sim_id = sim_entry.get("id")
    conn = get_db_connection()
    if conn and sim_id:
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE simulacros SET insights = %s::jsonb WHERE id = %s;", (json.dumps(nuevo), str(sim_id)))
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    st.cache_data.clear()
    return nuevo
