import os
import re
import unicodedata
from io import BytesIO
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st
from dotenv import load_dotenv

from ..config import MATERIAS, MAX_UPLOAD_MB
from ..data import COLUMN_CANONICAL_MAP, _canonicalize_columns
from ..styles import render_inclusion_badge

load_dotenv()


def _get_db_connection():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        st.error("No se encontró la conexión a Supabase (SUPABASE_DB_URL).")
        st.stop()
    return psycopg2.connect(db_url)


def _normalize_str(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip().upper()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


@st.cache_data(ttl=60)
def load_promotion_data(promocion_id: str):
    """Carga promoción seleccionada, estudiantes, resultados de simulacros y resultados ICFES real desde Supabase."""
    if not promocion_id:
        return None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1. Datos de la promoción
            cur.execute("SELECT id::text, nombre, anio_graduacion FROM promociones WHERE id = %s;", (promocion_id,))
            p_row = cur.fetchone()
            if not p_row:
                return None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
            promo = {"id": p_row[0], "nombre": p_row[1], "anio_graduacion": p_row[2]}

            # 2. Estudiantes oficiales de la promoción
            cur.execute("""
                SELECT id::text, nombre, grado, es_inclusion 
                FROM estudiantes 
                WHERE promocion_id = %s;
            """, (promocion_id,))
            e_rows = cur.fetchall()
            df_estudiantes = pd.DataFrame(e_rows, columns=["id", "nombre", "grado", "es_inclusion"]) if e_rows else pd.DataFrame()

            # 3. Resultados de Simulacros
            cur.execute("""
                SELECT 
                    rs.simulacro_id::text,
                    s.nombre AS simulacro_nombre,
                    s.creado_en,
                    e.id::text AS estudiante_id,
                    e.nombre AS estudiante_nombre,
                    e.es_inclusion,
                    rs.lectura_critica AS "LECTURA CRÍTICA",
                    rs.matematicas AS "MATEMÁTICAS",
                    rs.sociales_ciudadanas AS "SOCIALES Y CIUDADANAS",
                    rs.ciencias_naturales AS "CIENCIAS NATURALES",
                    rs.ingles AS "INGLÉS",
                    rs.promedio_ponderado AS "PUNTAJE GLOBAL"
                FROM resultados_simulacro rs
                JOIN estudiantes e ON rs.estudiante_id = e.id
                JOIN simulacros s ON rs.simulacro_id = s.id
                WHERE e.promocion_id = %s
                ORDER BY s.creado_en ASC, e.nombre ASC;
            """, (promocion_id,))
            s_rows = cur.fetchall()
            cols_sims = ["simulacro_id", "simulacro_nombre", "creado_en", "estudiante_id", "estudiante_nombre", "es_inclusion",
                         "LECTURA CRÍTICA", "MATEMÁTICAS", "SOCIALES Y CIUDADANAS", "CIENCIAS NATURALES", "INGLÉS", "PUNTAJE GLOBAL"]
            df_simulacros = pd.DataFrame(s_rows, columns=cols_sims) if s_rows else pd.DataFrame()

            # 4. Resultados ICFES Real
            cur.execute("""
                SELECT 
                    e.id::text AS estudiante_id,
                    e.nombre AS estudiante_nombre,
                    e.es_inclusion,
                    rir.lectura_critica AS "LECTURA CRÍTICA",
                    rir.matematicas AS "MATEMÁTICAS",
                    rir.sociales_ciudadanas AS "SOCIALES Y CIUDADANAS",
                    rir.ciencias_naturales AS "CIENCIAS NATURALES",
                    rir.ingles AS "INGLÉS",
                    rir.puntaje_global AS "PUNTAJE GLOBAL"
                FROM resultados_icfes_real rir
                JOIN estudiantes e ON rir.estudiante_id = e.id
                WHERE rir.promocion_id = %s;
            """, (promocion_id,))
            r_rows = cur.fetchall()
            cols_real = ["estudiante_id", "estudiante_nombre", "es_inclusion",
                         "LECTURA CRÍTICA", "MATEMÁTICAS", "SOCIALES Y CIUDADANAS", "CIENCIAS NATURALES", "INGLÉS", "PUNTAJE GLOBAL"]
            df_icfes_real = pd.DataFrame(r_rows, columns=cols_real) if r_rows else pd.DataFrame()

            return promo, df_estudiantes, df_simulacros, df_icfes_real
    finally:
        conn.close()


def process_icfes_excel(file_buffer, promo: dict, df_estudiantes: pd.DataFrame) -> Tuple[bool, str, List[Dict], List[str]]:
    """Procesa el archivo de resultados ICFES real y cruza nombres con estudiantes de Supabase."""
    try:
        fname = file_buffer.name.lower()
        if fname.endswith(".csv"):
            df = pd.read_csv(file_buffer)
        else:
            df = pd.read_excel(file_buffer)
    except Exception as e:
        return False, f"Error leyendo el archivo: {e}", [], []

    df = _canonicalize_columns(df)
    if "ESTUDIANTE" not in df.columns:
        return False, "El archivo no contiene la columna 'ESTUDIANTE' o 'Nombre Completo'.", [], []

    if df_estudiantes.empty:
        return False, "La promoción activa no tiene estudiantes registrados en la base de datos.", [], []

    est_map = {_normalize_str(row["nombre"]): row["id"] for _, row in df_estudiantes.iterrows()}
    
    rows_to_insert = []
    unmatched_names = []

    for _, row in df.iterrows():
        est_name_raw = str(row.get("ESTUDIANTE", "")).strip()
        norm_name = _normalize_str(est_name_raw)
        if not norm_name:
            continue

        est_id = est_map.get(norm_name)
        if not est_id:
            unmatched_names.append(est_name_raw)
            continue

        def _val(col):
            v = row.get(col)
            try:
                val = float(v)
                return val if not np.isnan(val) else None
            except (ValueError, TypeError):
                return None

        rows_to_insert.append({
            "promocion_id": promo["id"],
            "estudiante_id": est_id,
            "lectura_critica": _val("LECTURA CRÍTICA"),
            "matematicas": _val("MATEMÁTICAS"),
            "sociales_ciudadanas": _val("SOCIALES Y CIUDADANAS"),
            "ciencias_naturales": _val("CIENCIAS NATURALES"),
            "ingles": _val("INGLÉS"),
            "puntaje_global": _val("PROMEDIO PONDERADO"),
        })

    return True, "", rows_to_insert, unmatched_names


def save_icfes_results(rows: List[Dict]):
    """Guarda o actualiza resultados en resultados_icfes_real usando UPSERT."""
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute("""
                    INSERT INTO resultados_icfes_real (
                        promocion_id, estudiante_id, lectura_critica, matematicas, 
                        sociales_ciudadanas, ciencias_naturales, ingles, puntaje_global, actualizado_en
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, now()
                    )
                    ON CONFLICT (promocion_id, estudiante_id) DO UPDATE SET
                        lectura_critica = EXCLUDED.lectura_critica,
                        matematicas = EXCLUDED.matematicas,
                        sociales_ciudadanas = EXCLUDED.sociales_ciudadanas,
                        ciencias_naturales = EXCLUDED.ciencias_naturales,
                        ingles = EXCLUDED.ingles,
                        puntaje_global = EXCLUDED.puntaje_global,
                        actualizado_en = now();
                """, (
                    r["promocion_id"], r["estudiante_id"], r["lectura_critica"], r["matematicas"],
                    r["sociales_ciudadanas"], r["ciencias_naturales"], r["ingles"], r["puntaje_global"]
                ))
        conn.commit()
    finally:
        conn.close()


def render(user_email: str):
    st.markdown("<h1 class='header-title'>Resultados Oficiales ICFES Real</h1>", unsafe_allow_html=True)
    st.markdown(
        """
        Monitoreo y comparación en tiempo real entre los simulacros de preparación y los resultados 
        oficiales del examen ICFES Saber 11 por estudiante y a nivel de promoción.
        """
    )

    promocion_activa_id = st.session_state.get("promocion_activa_id")
    promo, df_estudiantes, df_simulacros, df_icfes_real = load_promotion_data(promocion_activa_id)

    if not promo:
        st.error("No hay una promoción activa configurada en el sistema.")
        st.stop()

    st.info(f"Promoción activa: **{promo['nombre']}** (Año de graduación: {promo['anio_graduacion']})")

    # --- Sección 1: Carga de Archivo de Resultados Reales ---
    with st.expander("Cargar / Actualizar Resultados ICFES Reales (Excel/CSV)", expanded=df_icfes_real.empty):
        st.write("Sube el archivo Excel o CSV entregado por el ICFES o procesado institucionalmente.")
        file_upload = st.file_uploader("Seleccionar archivo ICFES", type=["xlsx", "xls", "csv"])
        if file_upload:
            if st.button("Procesar e Importar a Supabase", use_container_width=True, type="primary"):
                ok, msg, rows_to_insert, unmatched = process_icfes_excel(file_buffer=file_upload, promo=promo, df_estudiantes=df_estudiantes)
                if not ok:
                    st.error(msg)
                else:
                    if unmatched:
                        st.warning(f"Se encontraron {len(unmatched)} nombres que NO hicieron match exacto con la lista oficial de estudiantes:")
                        st.dataframe(pd.DataFrame(unmatched, columns=["Estudiante No Encontrado en DB"]), hide_index=True)
                        st.info("Nota: Los nombres que hicieron match correctamente continuarán con la importación.")

                    if rows_to_insert:
                        save_icfes_results(rows_to_insert)
                        st.success(f"Se guardaron/actualizaron exitosamente {len(rows_to_insert)} resultados ICFES en Supabase.")
                        st.cache_data.clear()
                        st.rerun()

    if df_icfes_real.empty:
        st.warning("Aún no se han cargado resultados oficiales de ICFES Real para esta promoción. Sube un archivo en la sección anterior cuando estén disponibles.")
        st.markdown("---")

    # --- Sección 2: Pestañas General vs Inclusión ---
    tab_general, tab_inclusion = st.tabs([
        "Promoción General (Excluye Inclusión)", 
        "Estudiantes en Condición de Inclusión"
    ])

    with tab_general:
        render_comparison_dashboard(
            df_simulacros=df_simulacros[df_simulacros["es_inclusion"] == False] if not df_simulacros.empty else pd.DataFrame(),
            df_icfes_real=df_icfes_real[df_icfes_real["es_inclusion"] == False] if not df_icfes_real.empty else pd.DataFrame(),
            df_estudiantes=df_estudiantes[df_estudiantes["es_inclusion"] == False] if not df_estudiantes.empty else pd.DataFrame(),
            is_inclusion=False
        )

    with tab_inclusion:
        render_comparison_dashboard(
            df_simulacros=df_simulacros[df_simulacros["es_inclusion"] == True] if not df_simulacros.empty else pd.DataFrame(),
            df_icfes_real=df_icfes_real[df_icfes_real["es_inclusion"] == True] if not df_icfes_real.empty else pd.DataFrame(),
            df_estudiantes=df_estudiantes[df_estudiantes["es_inclusion"] == True] if not df_estudiantes.empty else pd.DataFrame(),
            is_inclusion=True
        )


def render_comparison_dashboard(df_simulacros: pd.DataFrame, df_icfes_real: pd.DataFrame, df_estudiantes: pd.DataFrame, is_inclusion: bool):
    if df_estudiantes.empty:
        st.info("No hay estudiantes en este grupo.")
        return

    has_real_scores = not df_icfes_real.empty and "PUNTAJE GLOBAL" in df_icfes_real.columns and df_icfes_real["PUNTAJE GLOBAL"].dropna().count() > 0

    header_text = "### Tabla Maestra de Evaluaciones de la Promoción (Listado de Simulacros + Puntaje Final ICFES Real)" if has_real_scores else "### Tabla Maestra de Evaluaciones de la Promoción"
    st.markdown(header_text)

    # 1. Construir Tabla Maestra de Evaluaciones de la Promoción
    master_rows = []
    
    if not df_simulacros.empty:
        ordered_sims = df_simulacros[["simulacro_id", "simulacro_nombre", "creado_en"]].drop_duplicates().sort_values("creado_en")
        
        for _, s_info in ordered_sims.iterrows():
            s_id = s_info["simulacro_id"]
            s_name = s_info["simulacro_nombre"]
            sub_df = df_simulacros[df_simulacros["simulacro_id"] == s_id]
            
            n_est = sub_df["estudiante_id"].nunique()
            pg = sub_df["PUNTAJE GLOBAL"].mean()
            
            row_data = {
                "Evaluación": s_name,
                "Tipo": "Simulacro",
                "Estudiantes": n_est,
                "Puntaje Global": round(pg, 2) if pd.notna(pg) else None,
            }
            for mat in MATERIAS:
                val_m = sub_df[mat].mean() if mat in sub_df.columns else np.nan
                row_data[mat] = round(val_m, 2) if pd.notna(val_m) else None
            
            master_rows.append(row_data)

    if has_real_scores:
        n_est_real = df_icfes_real["estudiante_id"].nunique()
        pg_real = df_icfes_real["PUNTAJE GLOBAL"].mean()
        
        row_real = {
            "Evaluación": "ICFES Real (Definitivo)",
            "Tipo": "Resultado Oficial",
            "Estudiantes": n_est_real,
            "Puntaje Global": round(pg_real, 2) if pd.notna(pg_real) else None,
        }
        for mat in MATERIAS:
            val_m = df_icfes_real[mat].mean() if mat in df_icfes_real.columns else np.nan
            row_real[mat] = round(val_m, 2) if pd.notna(val_m) else None
        
        master_rows.append(row_real)

    if not master_rows:
        st.info("No hay simulacros ni resultados reales registrados aún para este grupo.")
        return

    df_maestro = pd.DataFrame(master_rows)

    # Calcular Δ vs Prueba Anterior
    deltas = [None]
    for i in range(1, len(df_maestro)):
        prev_pg = df_maestro.iloc[i-1]["Puntaje Global"]
        curr_pg = df_maestro.iloc[i]["Puntaje Global"]
        if prev_pg is not None and curr_pg is not None:
            deltas.append(round(curr_pg - prev_pg, 2))
        else:
            deltas.append(None)
    df_maestro["Δ vs Anterior"] = deltas

    # Mostrar la Tabla Maestra estilizada
    columnas_num = [c for c in df_maestro.columns if c not in ["Evaluación", "Tipo", "Estudiantes"]]
    st.dataframe(
        df_maestro.style.format({col: "{:+.2f}" if col == "Δ vs Anterior" else "{:.2f}" for col in columnas_num if col in df_maestro.columns})
        .background_gradient(subset=["Puntaje Global"], cmap="YlGnBu", vmin=250, vmax=450),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("### Gráficas Generadas a Partir de la Tabla Maestra de la Promoción")

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        # Gráfica 1: Progresión del Puntaje Global alimentada directamente de df_maestro
        fig_global = go.Figure()
        colors = ["#3B82F6", "#6366F1", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981"]

        for idx, r in df_maestro.iterrows():
            nombre_eval = r["Evaluación"]
            val_pg = r["Puntaje Global"]
            is_real = ("ICFES Real" in nombre_eval)
            bar_color = "#F59E0B" if is_real else colors[idx % len(colors)]

            fig_global.add_trace(go.Bar(
                x=[nombre_eval],
                y=[val_pg if val_pg is not None else 0],
                name=nombre_eval,
                marker_color=bar_color,
                text=[f"{val_pg:.1f}" if val_pg is not None else "-"],
                textposition="auto"
            ))

        fig_global.update_layout(
            title="1. Progresión Puntaje Global (Simulacros a Puntaje Final)",
            yaxis=dict(title="Puntaje Global (0-500)", range=[0, 500]),
            xaxis=dict(title="Evaluación"),
            showlegend=False,
            height=420,
            template="plotly_white"
        )
        st.plotly_chart(fig_global, use_container_width=True)

    with col_g2:
        # Gráfica 2: Variación Delta vs Prueba Anterior
        fig_delta = go.Figure()
        for idx, r in df_maestro.iterrows():
            nombre_eval = r["Evaluación"]
            d_val = r["Δ vs Anterior"]
            if d_val is None:
                continue
            d_color = "#10B981" if d_val >= 0 else "#EF4444"
            fig_delta.add_trace(go.Bar(
                x=[nombre_eval],
                y=[d_val],
                name=nombre_eval,
                marker_color=d_color,
                text=[f"{d_val:+.2f}"],
                textposition="outside"
            ))
        fig_delta.add_hline(y=0, line_color="black")
        fig_delta.update_layout(
            title="2. Variación en Puntos (Δ vs Evaluación Previa)",
            yaxis=dict(title="Diferencia de Puntos"),
            xaxis=dict(title="Evaluación"),
            showlegend=False,
            height=420,
            template="plotly_white"
        )
        st.plotly_chart(fig_delta, use_container_width=True)

    # Gráfica 3: Comparación por Materia Alimentada de df_maestro
    materia_rows = []
    for idx, r in df_maestro.iterrows():
        nombre_eval = r["Evaluación"]
        for mat in MATERIAS:
            materia_rows.append({
                "Evaluación": nombre_eval,
                "Materia": mat,
                "Promedio": r.get(mat) or 0
            })
    df_mat_chart = pd.DataFrame(materia_rows)

    fig_mat = px.bar(
        df_mat_chart,
        x="Materia",
        y="Promedio",
        color="Evaluación",
        barmode="group",
        title="3. Desglose Promedio por Materia (Simulacros vs Puntaje Final ICFES)",
        template="plotly_white",
        height=450
    )
    fig_mat.update_layout(yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig_mat, use_container_width=True)


    # 3. Vista Individual por Estudiante (Lado a Lado)
    st.markdown("---")
    st.markdown("### Análisis Individual por Estudiante (Simulacros vs. ICFES Real)")

    lista_estudiantes = sorted(df_estudiantes["nombre"].unique())
    est_seleccionado = st.selectbox(
        "Seleccionar Estudiante", 
        lista_estudiantes, 
        key=f"select_est_{is_inclusion}"
    )

    if est_seleccionado:
        st_sims = df_simulacros[df_simulacros["estudiante_nombre"] == est_seleccionado] if not df_simulacros.empty else pd.DataFrame()
        st_real = df_icfes_real[df_icfes_real["estudiante_nombre"] == est_seleccionado] if not df_icfes_real.empty else pd.DataFrame()

        # Construir tabla comparativa por estudiante
        rows_est = []
        if not st_sims.empty:
            for _, r in st_sims.iterrows():
                rows_est.append({
                    "Evaluación": r["simulacro_nombre"],
                    "PUNTAJE GLOBAL": r["PUNTAJE GLOBAL"],
                    "LECTURA CRÍTICA": r["LECTURA CRÍTICA"],
                    "MATEMÁTICAS": r["MATEMÁTICAS"],
                    "SOCIALES Y CIUDADANAS": r["SOCIALES Y CIUDADANAS"],
                    "CIENCIAS NATURALES": r["CIENCIAS NATURALES"],
                    "INGLÉS": r["INGLÉS"],
                })

        if not st_real.empty:
            r = st_real.iloc[0]
            rows_est.append({
                "Evaluación": "ICFES REAL (Oficial)",
                "PUNTAJE GLOBAL": r["PUNTAJE GLOBAL"],
                "LECTURA CRÍTICA": r["LECTURA CRÍTICA"],
                "MATEMÁTICAS": r["MATEMÁTICAS"],
                "SOCIALES Y CIUDADANAS": r["SOCIALES Y CIUDADANAS"],
                "CIENCIAS NATURALES": r["CIENCIAS NATURALES"],
                "INGLÉS": r["INGLÉS"],
            })

        if rows_est:
            df_est_comp = pd.DataFrame(rows_est)
            st.dataframe(df_est_comp, hide_index=True, use_container_width=True)

            # Gráfica individual de progresión
            fig_ind = go.Figure()
            for idx, r in df_est_comp.iterrows():
                is_real = (r["Evaluación"] == "ICFES REAL (Oficial)")
                color = "#10B981" if is_real else "#3B82F6"
                fig_ind.add_trace(go.Bar(
                    x=[r["Evaluación"]],
                    y=[r["PUNTAJE GLOBAL"]],
                    name=r["Evaluación"],
                    marker_color=color,
                    text=[f"{r['PUNTAJE GLOBAL']:.1f}" if pd.notna(r["PUNTAJE GLOBAL"]) else "-"],
                    textposition="auto"
                ))

            fig_ind.update_layout(
                title=f"Progresión Puntaje Global - {est_seleccionado}",
                yaxis=dict(title="Puntaje Global", range=[0, 500]),
                showlegend=False,
                template="plotly_dark",
                height=350
            )
            st.plotly_chart(fig_ind, use_container_width=True)
        else:
            st.info("Sin datos para este estudiante.")
