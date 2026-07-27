import os
import unicodedata
from io import BytesIO
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import psycopg2
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from ..config import MATERIAS
from ..data import _canonicalize_columns, _clean_student_frame

load_dotenv()


def _get_db_connection():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        st.error("No se encontró la variable SUPABASE_DB_URL en el entorno.")
        st.stop()
    return psycopg2.connect(db_url)


def load_promotion_data(promocion_id: Optional[str] = None) -> Tuple[Optional[Dict], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carga promoción seleccionada, estudiantes, resultados de simulacros y resultados ICFES real desde Supabase."""
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1. Promoción seleccionada o por defecto
            if promocion_id:
                cur.execute("""
                    SELECT id::text, nombre, anio_graduacion
                    FROM promociones
                    WHERE id = %s;
                """, (promocion_id,))
            else:
                cur.execute("""
                    SELECT id::text, nombre, anio_graduacion
                    FROM promociones
                    WHERE activa = true
                    ORDER BY creado_en DESC
                    LIMIT 1;
                """)
            promo_row = cur.fetchone()
            if not promo_row:
                return None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
            
            promo = {
                "id": str(promo_row[0]),
                "nombre": promo_row[1],
                "anio_graduacion": promo_row[2]
            }
            promocion_id = promo["id"]


            # 2. Estudiantes
            cur.execute("""
                SELECT id::text, nombre, grado, es_inclusion
                FROM estudiantes
                WHERE promocion_id = %s;
            """, (promocion_id,))
            est_rows = cur.fetchall()
            df_estudiantes = pd.DataFrame(est_rows, columns=["estudiante_id", "nombre", "grado", "es_inclusion"])

            # 3. Resultados de simulacros
            cur.execute("""
                SELECT 
                    rs.simulacro_id,
                    s.nombre AS simulacro_nombre,
                    rs.estudiante_id::text,
                    e.nombre AS estudiante_nombre,
                    e.es_inclusion,
                    rs.lectura_critica,
                    rs.matematicas,
                    rs.sociales_ciudadanas,
                    rs.ciencias_naturales,
                    rs.ingles,
                    rs.promedio_ponderado,
                    s.creado_en
                FROM resultados_simulacro rs
                JOIN simulacros s ON rs.simulacro_id = s.id
                JOIN estudiantes e ON rs.estudiante_id = e.id
                WHERE s.promocion_id = %s
                ORDER BY s.creado_en ASC;
            """, (promocion_id,))
            sim_rows = cur.fetchall()
            df_simulacros = pd.DataFrame(
                sim_rows, 
                columns=[
                    "simulacro_id", "simulacro_nombre", "estudiante_id", "estudiante_nombre", 
                    "es_inclusion", "LECTURA CRÍTICA", "MATEMÁTICAS", "SOCIALES Y CIUDADANAS", 
                    "CIENCIAS NATURALES", "INGLÉS", "PUNTAJE GLOBAL", "creado_en"
                ]
            )

            # 4. Resultados ICFES Real
            cur.execute("""
                SELECT 
                    rir.estudiante_id::text,
                    e.nombre AS estudiante_nombre,
                    e.es_inclusion,
                    rir.anio_presentacion,
                    rir.puntaje_global,
                    rir.lectura_critica,
                    rir.matematicas,
                    rir.sociales_ciudadanas,
                    rir.ciencias_naturales,
                    rir.ingles
                FROM resultados_icfes_real rir
                JOIN estudiantes e ON rir.estudiante_id = e.id
                WHERE rir.promocion_id = %s;
            """, (promocion_id,))
            real_rows = cur.fetchall()
            df_icfes_real = pd.DataFrame(
                real_rows,
                columns=[
                    "estudiante_id", "estudiante_nombre", "es_inclusion", "anio_presentacion",
                    "PUNTAJE GLOBAL", "LECTURA CRÍTICA", "MATEMÁTICAS", "SOCIALES Y CIUDADANAS",
                    "CIENCIAS NATURALES", "INGLÉS"
                ]
            )

            num_cols = ["LECTURA CRÍTICA", "MATEMÁTICAS", "SOCIALES Y CIUDADANAS", "CIENCIAS NATURALES", "INGLÉS", "PUNTAJE GLOBAL"]
            for col in num_cols:
                if col in df_simulacros.columns:
                    df_simulacros[col] = pd.to_numeric(df_simulacros[col], errors="coerce")
                if col in df_icfes_real.columns:
                    df_icfes_real[col] = pd.to_numeric(df_icfes_real[col], errors="coerce")

            return promo, df_estudiantes, df_simulacros, df_icfes_real
    finally:
        conn.close()


def process_icfes_excel(file_buffer: BytesIO, promo: Dict, df_estudiantes: pd.DataFrame) -> Tuple[bool, str, List[Dict], List[str]]:
    """Procesa el archivo de resultados ICFES real y cruza nombres con estudiantes de Supabase."""
    file_buffer.seek(0)
    header = file_buffer.read(8)
    file_buffer.seek(0)

    # Validar firma MIME/Magic Bytes de archivo
    fname = file_buffer.name.lower()
    if fname.endswith(".xlsx") and not header.startswith(b"PK\x03\x04"):
        return False, "El archivo .xlsx no tiene una estructura válida de hoja de cálculo Excel.", [], []
    elif fname.endswith(".xls") and not header.startswith(b"\xd0\xcf\x11\xe0"):
        return False, "El archivo .xls no tiene la firma binaria válida de Excel legado.", [], []

    try:
        if fname.endswith(".csv"):
            df_raw = pd.read_csv(file_buffer)
        else:
            df_raw = pd.read_excel(file_buffer)
    except Exception as exc:
        return False, f"No se pudo leer el archivo: {exc}", [], []

    df_clean = _clean_student_frame(df_raw)
    
    # Mapa de nombres normalizados en DB -> estudiante_id
    db_student_map = {row["nombre"]: row["estudiante_id"] for _, row in df_estudiantes.iterrows()}
    
    rows_to_insert = []
    unmatched_names = []

    for _, r in df_clean.iterrows():
        st_name = r["ESTUDIANTE"]
        if st_name in db_student_map:
            st_id = db_student_map[st_name]
            
            def safe_num(val):
                if pd.isna(val):
                    return None
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None

            pg = safe_num(r.get("PROMEDIO PONDERADO") or r.get("PUNTAJE GLOBAL"))
            lc = safe_num(r.get("LECTURA CRÍTICA"))
            mat = safe_num(r.get("MATEMÁTICAS")) if "MATEMÁTICAS" in r else safe_num(r.get("MATEMATICAS"))
            soc = safe_num(r.get("SOCIALES Y CIUDADANAS"))
            cn = safe_num(r.get("CIENCIAS NATURALES"))
            ing = safe_num(r.get("INGLÉS") or r.get("INGLES"))


            rows_to_insert.append({
                "estudiante_id": st_id,
                "promocion_id": promo["id"],
                "anio_presentacion": promo["anio_graduacion"],
                "puntaje_global": pg,
                "lectura_critica": lc,
                "matematicas": mat,
                "sociales_ciudadanas": soc,
                "ciencias_naturales": cn,
                "ingles": ing
            })
        else:
            unmatched_names.append(st_name)

    return True, f"Procesados {len(rows_to_insert)} registros válidos.", rows_to_insert, unmatched_names


def save_icfes_results(rows_to_insert: List[Dict]):
    """Guarda los resultados reales de ICFES en Supabase."""
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            for row in rows_to_insert:
                cur.execute("""
                    INSERT INTO resultados_icfes_real (
                        estudiante_id, promocion_id, anio_presentacion, puntaje_global,
                        lectura_critica, matematicas, sociales_ciudadanas, ciencias_naturales, ingles
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (estudiante_id, anio_presentacion) DO UPDATE SET
                        puntaje_global = EXCLUDED.puntaje_global,
                        lectura_critica = EXCLUDED.lectura_critica,
                        matematicas = EXCLUDED.matematicas,
                        sociales_ciudadanas = EXCLUDED.sociales_ciudadanas,
                        ciencias_naturales = EXCLUDED.ciencias_naturales,
                        ingles = EXCLUDED.ingles;
                """, (
                    row["estudiante_id"], row["promocion_id"], row["anio_presentacion"],
                    row["puntaje_global"], row["lectura_critica"], row["matematicas"],
                    row["sociales_ciudadanas"], row["ciencias_naturales"], row["ingles"]
                ))
        conn.commit()
    finally:
        conn.close()


def render(user_email: str):
    st.markdown("<h1 class='header-title'>🎯 Resultados Oficiales ICFES Real</h1>", unsafe_allow_html=True)
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

    st.info(f"📌 Promoción activa: **{promo['nombre']}** (Año de graduación: {promo['anio_graduacion']})")

    # --- Sección 1: Carga de Archivo de Resultados Reales ---
    with st.expander("📤 Cargar / Actualizar Resultados ICFES Reales (Excel/CSV)", expanded=df_icfes_real.empty):
        st.write("Sube el archivo Excel o CSV entregado por el ICFES o procesado institucionalmente.")
        file_upload = st.file_uploader("Seleccionar archivo ICFES", type=["xlsx", "xls", "csv"])
        if file_upload:
            if st.button("🚀 Procesar e Importar a Supabase", use_container_width=True, type="primary"):
                ok, msg, rows_to_insert, unmatched = process_icfes_excel(file_buffer=file_upload, promo=promo, df_estudiantes=df_estudiantes)
                if not ok:
                    st.error(msg)
                else:
                    if unmatched:
                        st.warning(f"⚠️ Se encontraron {len(unmatched)} nombres que NO hicieron match exacto con la lista oficial de estudiantes:")
                        st.dataframe(pd.DataFrame(unmatched, columns=["Estudiante No Encontrado en DB"]), hide_index=True)
                        st.info("Nota: Los nombres que hicieron match correctamente continuarán con la importación.")

                    if rows_to_insert:
                        save_icfes_results(rows_to_insert)
                        st.success(f"✅ Se guardaron/actualizaron exitosamente {len(rows_to_insert)} resultados ICFES en Supabase.")
                        st.cache_data.clear()
                        st.rerun()

    if df_icfes_real.empty:
        st.warning("ℹ️ Aún no se han cargado resultados oficiales de ICFES Real para esta promoción. Sube un archivo en la sección anterior cuando estén disponibles.")
        st.markdown("---")

    # --- Sección 2: Pestañas General vs Inclusión ---
    tab_general, tab_inclusion = st.tabs([
        "🎓 Promoción General (Excluye Inclusión)", 
        "♿ Estudiantes en Condición de Inclusión"
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

    st.markdown("### 🏛️ Tabla Maestra de Evaluaciones de la Promoción (Listado de Simulacros + Puntaje Final ICFES Real)")

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

    if not df_icfes_real.empty:
        n_est_real = df_icfes_real["estudiante_id"].nunique()
        pg_real = df_icfes_real["PUNTAJE GLOBAL"].mean()
        
        row_real = {
            "Evaluación": "🎯 ICFES Real (Definitivo)",
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
    st.markdown("### 📊 Gráficas Generadas a Partir de la Tabla Maestra de la Promoción")

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
            title="1. Progresión Puntaje Global (Simulacros ➔ Puntaje Final)",
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
    st.markdown("### 👤 Análisis Individual por Estudiante (Simulacros vs. ICFES Real)")

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
                "Evaluación": "🎯 ICFES REAL (Oficial)",
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
                is_real = (r["Evaluación"] == "🎯 ICFES REAL (Oficial)")
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
