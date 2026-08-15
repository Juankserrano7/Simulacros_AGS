"""Módulo para el seguimiento y comparación entre simulacros y resultados oficiales de ICFES Real con diagnóstico ML."""

import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ..config import MATERIAS
from ..core_utils import get_db_connection
from ..ml.prediccion_icfes import generar_analisis_diagnostico_cohorte, predecir_puntaje_final


def load_promotion_data(promocion_id: Optional[str] = None) -> Tuple[Optional[Dict], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carga promoción seleccionada, estudiantes, resultados de simulacros y resultados ICFES real desde Supabase."""
    conn = get_db_connection()
    if not conn:
        return None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    try:
        with conn.cursor() as cur:
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

            cur.execute("""
                SELECT id::text, nombre, grado, es_inclusion
                FROM estudiantes
                WHERE promocion_id = %s
                ORDER BY nombre ASC;
            """, (promocion_id,))
            estudiantes_rows = cur.fetchall()
            df_estudiantes = pd.DataFrame(estudiantes_rows, columns=["id", "nombre", "grado", "es_inclusion"]) if estudiantes_rows else pd.DataFrame(columns=["id", "nombre", "grado", "es_inclusion"])

            cur.execute("""
                SELECT 
                    rs.simulacro_id::text,
                    s.nombre AS simulacro_nombre,
                    s.creado_en AS simulacro_fecha,
                    rs.estudiante_id::text,
                    e.nombre AS estudiante_nombre,
                    e.grado AS estudiante_grado,
                    e.es_inclusion,
                    rs.lectura_critica,
                    rs.matematicas,
                    rs.sociales_ciudadanas,
                    rs.ciencias_naturales,
                    rs.ingles,
                    rs.promedio_ponderado
                FROM resultados_simulacro rs
                JOIN simulacros s ON s.id = rs.simulacro_id
                JOIN estudiantes e ON e.id = rs.estudiante_id
                WHERE s.promocion_id = %s
                ORDER BY s.creado_en ASC, e.nombre ASC;
            """, (promocion_id,))
            sims_rows = cur.fetchall()
            sim_cols = [
                "simulacro_id", "simulacro_nombre", "simulacro_fecha", "estudiante_id",
                "estudiante_nombre", "estudiante_grado", "es_inclusion",
                "LECTURA CRÍTICA", "MATEMÁTICAS", "SOCIALES Y CIUDADANAS",
                "CIENCIAS NATURALES", "INGLÉS", "PUNTAJE GLOBAL"
            ]
            df_simulacros = pd.DataFrame(sims_rows, columns=sim_cols) if sims_rows else pd.DataFrame(columns=sim_cols)

            cur.execute("""
                SELECT 
                    r.estudiante_id::text,
                    e.nombre AS estudiante_nombre,
                    e.grado AS estudiante_grado,
                    e.es_inclusion,
                    r.lectura_critica,
                    r.matematicas,
                    r.sociales_ciudadanas,
                    r.ciencias_naturales,
                    r.ingles,
                    r.puntaje_global
                FROM resultados_icfes_real r
                JOIN estudiantes e ON e.id = r.estudiante_id
                WHERE r.promocion_id = %s
                ORDER BY e.nombre ASC;
            """, (promocion_id,))
            real_rows = cur.fetchall()
            real_cols = [
                "estudiante_id", "estudiante_nombre", "estudiante_grado", "es_inclusion",
                "LECTURA CRÍTICA", "MATEMÁTICAS", "SOCIALES Y CIUDADANAS",
                "CIENCIAS NATURALES", "INGLÉS", "PUNTAJE GLOBAL"
            ]
            df_icfes_real = pd.DataFrame(real_rows, columns=real_cols) if real_rows else pd.DataFrame(columns=real_cols)

            return promo, df_estudiantes, df_simulacros, df_icfes_real
    finally:
        conn.close()


def render_diagnostico_ml_tab(promocion_id: str):
    """Pestaña de diagnóstico y calibración de la cohorte contra resultados oficiales."""
    st.markdown("### 🔬 Diagnóstico y Calibración de Precisión ML (Fine-Tuning)")
    st.markdown(
        """
        Esta sección compara sistemáticamente las predicciones generadas por el modelo frente a los 
        resultados reales del examen oficial del ICFES, permitiendo auditar el sesgo, los residuales y el margen de error.
        """
    )

    conn = get_db_connection()
    if not conn:
        st.error("No hay conexión a la base de datos.")
        return

    try:
        diag = generar_analisis_diagnostico_cohorte(conn, promocion_id=promocion_id)
        if "error" in diag:
            st.info(f"ℹ️ {diag['error']}")
            return

        df_comp = diag["df_comparativa"]

        # Métricas principales de calibración
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("👥 Estudiantes Evaluados", diag["n_estudiantes"])
        with m2:
            st.metric("🎯 MAE Global", f"{diag['mae_global']} pts")
        with m3:
            st.metric("📉 RMSE Global", f"{diag['rmse_global']} pts")
        with m4:
            st.metric("⚖️ Sesgo Medio (Bias)", f"{diag['sesgo_medio']:+.1f} pts")

        c_tol1, c_tol2, c_tol3 = st.columns(3)
        with c_tol1:
            st.metric("✅ Precisión dentro de ±10 pts", f"{diag['precision_10_pts']}%")
        with c_tol2:
            st.metric("✅ Precisión dentro de ±15 pts", f"{diag['precision_15_pts']}%")
        with c_tol3:
            st.metric("✅ Precisión dentro de ±20 pts", f"{diag['precision_20_pts']}%")

        st.markdown("---")
        st.markdown("#### 📊 Gráfico de Calibración: Puntaje Real vs. Predicción del Modelo")

        fig_calib = go.Figure()
        fig_calib.add_trace(go.Scatter(
            x=df_comp["Real Global"],
            y=df_comp["Predicción Global"],
            mode="markers",
            name="Estudiantes",
            text=df_comp["Estudiante"],
            marker=dict(size=10, color="#8B5CF6", opacity=0.85)
        ))

        # Línea de identidad ideal (y = x)
        min_v = min(df_comp["Real Global"].min(), df_comp["Predicción Global"].min()) - 15
        max_v = max(df_comp["Real Global"].max(), df_comp["Predicción Global"].max()) + 15
        fig_calib.add_trace(go.Scatter(
            x=[min_v, max_v],
            y=[min_v, max_v],
            mode="lines",
            name="Ajuste Perfecto (Ideal)",
            line=dict(color="#10B981", dash="dash", width=2)
        ))

        fig_calib.update_layout(
            xaxis_title="Puntaje Real Oficial ICFES",
            yaxis_title="Puntaje Proyectado por el Modelo",
            template="plotly_white",
            height=450
        )
        st.plotly_chart(fig_calib, use_container_width=True)

        st.markdown("#### 📋 Desglose de Precisión por Asignatura (Escala 0-100)")
        sub_metrics = diag.get("metricas_materias", {})
        if sub_metrics:
            sub_df = pd.DataFrame([
                {
                    "Asignatura": sub,
                    "MAE (pts)": info["mae"],
                    "RMSE (pts)": info["rmse"],
                    "Sesgo / Bias (pts)": f"{info['sesgo']:+.2f}",
                }
                for sub, info in sub_metrics.items()
            ])
            st.dataframe(sub_df, hide_index=True, use_container_width=True)

        st.markdown("#### 📑 Tabla Detallada por Estudiante")
        cols_mostrar = [
            "Estudiante", "Real Global", "Predicción Global", "Error (Pred - Real)",
            "Real LC", "Pred LC", "Real MAT", "Pred MAT", "Real SOC", "Pred SOC",
            "Real CN", "Pred CN", "Real ING", "Pred ING", "Simulacros"
        ]
        cols_valid = [c for c in cols_mostrar if c in df_comp.columns]
        st.dataframe(df_comp[cols_valid], hide_index=True, use_container_width=True)

    finally:
        conn.close()


def render_comparison_dashboard(df_simulacros: pd.DataFrame, df_icfes_real: pd.DataFrame, df_estudiantes: pd.DataFrame, is_inclusion: bool):
    if df_estudiantes.empty:
        st.info("No hay estudiantes en este grupo.")
        return

    has_real_scores = not df_icfes_real.empty and "PUNTAJE GLOBAL" in df_icfes_real.columns and df_icfes_real["PUNTAJE GLOBAL"].dropna().count() > 0

    st.markdown("### 📊 Métricas Globales de Rendimiento")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Estudiantes", len(df_estudiantes))

    with col2:
        if has_real_scores:
            prom_real = df_icfes_real["PUNTAJE GLOBAL"].dropna().mean()
            st.metric("Promedio ICFES Real", f"{prom_real:.1f} pts" if pd.notna(prom_real) else "-")
        else:
            st.metric("Promedio ICFES Real", "Pendiente")

    with col3:
        if not df_simulacros.empty and "PUNTAJE GLOBAL" in df_simulacros.columns:
            prom_sims = df_simulacros["PUNTAJE GLOBAL"].dropna().mean()
            st.metric("Promedio Simulacros", f"{prom_sims:.1f} pts" if pd.notna(prom_sims) else "-")
        else:
            st.metric("Promedio Simulacros", "-")

    with col4:
        if has_real_scores and not df_simulacros.empty:
            diff = prom_real - prom_sims
            st.metric("Diferencia (ICFES - Sim)", f"{diff:+.1f} pts", delta_color="normal")
        else:
            st.metric("Diferencia", "-")

    st.markdown("---")

    # Tabla Resumen Consolidada
    st.markdown("### 📋 Tabla Comparativa por Estudiante")
    nombres_estudiantes = sorted(df_estudiantes["nombre"].unique())
    registros_tabla = []

    for est in nombres_estudiantes:
        st_info = df_estudiantes[df_estudiantes["nombre"] == est].iloc[0]
        est_id = str(st_info["id"])
        grado = st_info["grado"]

        sub_sims = df_simulacros[df_simulacros["estudiante_id"] == est_id]
        sub_real = df_icfes_real[df_icfes_real["estudiante_id"] == est_id]

        row = {
            "Estudiante": est,
            "Grado": grado if pd.notna(grado) else "-",
            "Simulacros Presentados": len(sub_sims),
        }

        if not sub_sims.empty:
            row["Promedio Simulacros"] = round(sub_sims["PUNTAJE GLOBAL"].dropna().mean(), 1)
        else:
            row["Promedio Simulacros"] = None

        if not sub_real.empty and pd.notna(sub_real.iloc[0]["PUNTAJE GLOBAL"]):
            row["ICFES Real"] = round(float(sub_real.iloc[0]["PUNTAJE GLOBAL"]), 1)
            if row["Promedio Simulacros"] is not None:
                row["Diferencia"] = round(row["ICFES Real"] - row["Promedio Simulacros"], 1)
            else:
                row["Diferencia"] = None
        else:
            row["ICFES Real"] = None
            row["Diferencia"] = None

        registros_tabla.append(row)

    df_tabla = pd.DataFrame(registros_tabla)
    st.dataframe(df_tabla.style.format(na_rep="-"), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("### 👤 Análisis Individual por Estudiante")
    est_seleccionado = st.selectbox(
        "Seleccionar Estudiante",
        options=nombres_estudiantes,
        key=f"select_est_{is_inclusion}"
    )

    if est_seleccionado:
        st_sims = df_simulacros[df_simulacros["estudiante_nombre"] == est_seleccionado]
        st_real = df_icfes_real[df_icfes_real["estudiante_nombre"] == est_seleccionado]

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

        res_pred = None
        if not is_inclusion:
            est_id = None
            if not df_estudiantes.empty and "nombre" in df_estudiantes.columns:
                sub_e = df_estudiantes[df_estudiantes["nombre"] == est_seleccionado]
                if not sub_e.empty:
                    est_id = sub_e.iloc[0]["id"]

            try:
                conn_pred = get_db_connection()
                if conn_pred:
                    try:
                        if not est_id:
                            with conn_pred.cursor() as cur:
                                cur.execute("SELECT id FROM estudiantes WHERE UPPER(TRIM(nombre)) = UPPER(TRIM(%s)) LIMIT 1;", (est_seleccionado,))
                                r_db = cur.fetchone()
                                if r_db:
                                    est_id = r_db[0]

                        if est_id:
                            res_pred = predecir_puntaje_final(conn_pred, est_id)
                    finally:
                        conn_pred.close()
            except Exception:
                res_pred = None

        if res_pred and res_pred.get("prediccion") is not None:
            pred_subs = res_pred.get("predicciones_materias", {})
            rows_est.append({
                "Evaluación": "🔮 Predicción ICFES (Modelo)",
                "PUNTAJE GLOBAL": res_pred["prediccion"],
                "LECTURA CRÍTICA": pred_subs.get("LECTURA CRÍTICA", {}).get("puntaje"),
                "MATEMÁTICAS": pred_subs.get("MATEMÁTICAS", {}).get("puntaje"),
                "SOCIALES Y CIUDADANAS": pred_subs.get("SOCIALES Y CIUDADANAS", {}).get("puntaje"),
                "CIENCIAS NATURALES": pred_subs.get("CIENCIAS NATURALES", {}).get("puntaje"),
                "INGLÉS": pred_subs.get("INGLÉS", {}).get("puntaje"),
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

            fig_ind = go.Figure()
            for idx, r in df_est_comp.iterrows():
                eval_name = r["Evaluación"]
                is_real = (eval_name == "🎯 ICFES REAL (Oficial)")
                is_pred = (eval_name == "🔮 Predicción ICFES (Modelo)")

                if is_real:
                    color = "#10B981"
                elif is_pred:
                    color = "#8B5CF6"
                else:
                    color = "#3B82F6"

                val_pg = r["PUNTAJE GLOBAL"]
                bar_kwargs = dict(
                    x=[eval_name],
                    y=[val_pg],
                    name=eval_name,
                    marker_color=color,
                    text=[f"{val_pg:.1f}" if pd.notna(val_pg) else "-"],
                    textposition="auto"
                )

                if is_pred and res_pred and res_pred.get("intervalo"):
                    intervalo = res_pred["intervalo"]
                    bar_kwargs["error_y"] = dict(
                        type='data',
                        symmetric=False,
                        array=[intervalo[1] - val_pg],
                        arrayminus=[val_pg - intervalo[0]],
                        color='#8B5CF6',
                        thickness=2,
                        width=6
                    )

                fig_ind.add_trace(go.Bar(**bar_kwargs))

            fig_ind.update_layout(
                title=f"Progresión Puntaje Global - {est_seleccionado}",
                yaxis=dict(title="Puntaje Global", range=[0, 500]),
                showlegend=False,
                template="plotly_white",
                height=380
            )
            st.plotly_chart(fig_ind, use_container_width=True, key=f"fig_ind_{is_inclusion}")

            if res_pred and res_pred.get("prediccion") is not None:
                mae_loocv = res_pred.get("mae_loocv", 10.9)
                st.info(f"💡 **Predicción ICFES integrada:** Generada mediante Machine Learning (MAE LOOCV: `{mae_loocv:.1f}` pts).")
        else:
            st.info("Sin datos para este estudiante.")


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

    tab_general, tab_inclusion, tab_diagnostico = st.tabs([
        "🎓 Promoción General (Excluye Inclusión)", 
        "♿ Estudiantes en Condición de Inclusión",
        "🔬 Calibración y Diagnóstico ML (Fine-Tuning)"
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

    with tab_diagnostico:
        render_diagnostico_ml_tab(promocion_activa_id)
