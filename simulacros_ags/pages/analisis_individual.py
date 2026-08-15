"""Módulo de análisis individual por estudiante con inferencia predictiva multi-output y radar de competencias."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..core_utils import get_db_connection
from ..data import load_icfes_real_data
from ..ml.prediccion_icfes import predecir_puntaje_final


def render(datos_actual, materias):
    if datos_actual.empty or "ESTUDIANTE" not in datos_actual.columns:
        st.warning("No hay datos de simulacro disponibles.")
        return

    st.markdown("<h1 class='header-title'>👤 Análisis Individual de Estudiantes</h1>", unsafe_allow_html=True)

    estudiantes_opt = sorted(datos_actual["ESTUDIANTE"].unique())
    estudiante_seleccionado = st.selectbox("Seleccionar Estudiante", estudiantes_opt)
    datos_estudiante = datos_actual[datos_actual["ESTUDIANTE"] == estudiante_seleccionado].iloc[0]

    promocion_id = st.session_state.get("promocion_activa_id")
    df_icfes_real = load_icfes_real_data(promocion_id)

    icfes_row = None
    has_icfes_real = False
    if not df_icfes_real.empty and "ESTUDIANTE" in df_icfes_real.columns:
        sub_real = df_icfes_real[df_icfes_real["ESTUDIANTE"].str.strip().str.upper() == estudiante_seleccionado.strip().upper()]
        if not sub_real.empty and pd.notna(sub_real.iloc[0].get("PROMEDIO PONDERADO")):
            icfes_row = sub_real.iloc[0]
            has_icfes_real = True

    st.markdown(f"### 📊 Resultados de: **{estudiante_seleccionado}**")
    if "GRADO" in datos_estudiante and pd.notna(datos_estudiante["GRADO"]):
        st.markdown(f"**Grado:** {datos_estudiante['GRADO']}")

    val_sim = datos_estudiante.get("PROMEDIO PONDERADO")
    no_presento = pd.isna(val_sim)

    # Tarjetas de resumen
    if has_icfes_real:
        col1, col2, col3, col4, col5 = st.columns(5)
        val_real = icfes_row["PROMEDIO PONDERADO"]
        with col1:
            st.metric("🎯 ICFES Real", f"{val_real:.1f}" if pd.notna(val_real) else "N/A")
        with col2:
            st.metric("📋 Simulacro Activo", f"{val_sim:.1f}" if pd.notna(val_sim) else "No presentó")
        with col3:
            if pd.notna(val_real) and pd.notna(val_sim):
                delta = val_real - val_sim
                st.metric("📈 Δ (ICFES - Sim)", f"{delta:+.1f}", delta_color="normal")
            else:
                st.metric("📈 Δ (ICFES - Sim)", "N/A")
        with col4:
            if pd.notna(val_sim):
                ranking = datos_actual.dropna(subset=["PROMEDIO PONDERADO"]).sort_values("PROMEDIO PONDERADO", ascending=False).reset_index(drop=True)
                pos_sub = ranking[ranking["ESTUDIANTE"] == estudiante_seleccionado]
                posicion = pos_sub.index[0] + 1 if not pos_sub.empty else "N/A"
                st.metric("🏆 Pos. Simulacro", f"{posicion} / {len(ranking)}")
            else:
                st.metric("🏆 Pos. Simulacro", "No presentó")
        with col5:
            if pd.notna(val_real):
                mejor_mat_real = max(materias, key=lambda m: icfes_row[m] if pd.notna(icfes_row.get(m)) else -1)
                st.metric("⭐ Mejor Materia (ICFES)", mejor_mat_real.split()[0])
            else:
                st.metric("⭐ Mejor Materia", "N/A")
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📋 Simulacro Activo", f"{val_sim:.1f}" if pd.notna(val_sim) else "No presentó")
        with col2:
            if pd.notna(val_sim):
                valid_proms = datos_actual["PROMEDIO PONDERADO"].dropna()
                percentil = (valid_proms < val_sim).sum() / len(valid_proms) * 100 if len(valid_proms) > 0 else 0
                st.metric("📊 Percentil", f"{percentil:.1f}%")
            else:
                st.metric("📊 Percentil", "N/A")
        with col3:
            if pd.notna(val_sim):
                ranking = datos_actual.dropna(subset=["PROMEDIO PONDERADO"]).sort_values("PROMEDIO PONDERADO", ascending=False).reset_index(drop=True)
                pos_sub = ranking[ranking["ESTUDIANTE"] == estudiante_seleccionado]
                posicion = pos_sub.index[0] + 1 if not pos_sub.empty else "N/A"
                st.metric("🏆 Posición", f"{posicion} / {len(ranking)}")
            else:
                st.metric("🏆 Posición", "No presentó")
        with col4:
            if pd.notna(val_sim):
                mejor_materia = max(materias, key=lambda m: datos_estudiante[m] if pd.notna(datos_estudiante[m]) else -1)
                st.metric("⭐ Mejor Materia", mejor_materia.split()[0])
            else:
                st.metric("⭐ Mejor Materia", "N/A")

    # =========================================================================
    # SECCIÓN DE PROGRESIÓN TEMPORAL Y PREDICCIÓN CON MACHINE LEARNING
    # =========================================================================
    st.markdown("<h2 class='section-header'>📈 Progresión Temporal de Simulacros y Pronóstico ICFES</h2>", unsafe_allow_html=True)

    res_pred = None
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, es_inclusion FROM estudiantes WHERE UPPER(TRIM(nombre)) = UPPER(TRIM(%s)) LIMIT 1;",
                    (estudiante_seleccionado,)
                )
                est_row = cur.fetchone()

            if est_row:
                est_id, es_inclusion = est_row[0], est_row[1]

                query_sims_hist = """
                SELECT 
                    s.id AS simulacro_id,
                    s.nombre AS simulacro_nombre,
                    rs.promedio_ponderado
                FROM resultados_simulacro rs
                JOIN simulacros s ON s.id = rs.simulacro_id
                WHERE rs.estudiante_id = %s
                ORDER BY s.creado_en ASC;
                """
                df_hist = pd.read_sql_query(query_sims_hist, conn, params=(est_id,))

                if not df_hist.empty:
                    x_hist = list(df_hist["simulacro_nombre"])
                    y_hist = list(df_hist["promedio_ponderado"])

                    fig_prog = go.Figure()

                    # 1. Serie histórica de simulacros
                    fig_prog.add_trace(go.Scatter(
                        x=x_hist,
                        y=y_hist,
                        mode="lines+markers+text",
                        name="Simulacros Históricos",
                        text=[f"{v:.1f}" if pd.notna(v) else "" for v in y_hist],
                        textposition="top center",
                        line=dict(color="#1A73E8", width=3),
                        marker=dict(size=9, color="#1A73E8")
                    ))

                    # 2. Inferencia predictiva (exclusiva para estudiantes no de inclusión)
                    if not es_inclusion:
                        res_pred = predecir_puntaje_final(conn, est_id)

                    if res_pred and res_pred.get("prediccion") is not None:
                        pred_val = res_pred["prediccion"]
                        intervalo = res_pred["intervalo"]
                        mae_loocv = res_pred.get("mae_loocv", 10.9)

                        ultimo_sim_nombre = x_hist[-1]
                        ultimo_sim_puntaje = y_hist[-1]

                        x_pred_segment = [ultimo_sim_nombre, "🔮 Predicción ICFES (Modelo)"]
                        y_pred_segment = [ultimo_sim_puntaje, pred_val]

                        fig_prog.add_trace(go.Scatter(
                            x=x_pred_segment,
                            y=y_pred_segment,
                            mode="lines+markers+text",
                            name="🔮 Predicción ICFES (Modelo)",
                            text=["", f"<b>{pred_val:.1f} pts</b>"],
                            textposition="top center",
                            line=dict(color="#8B5CF6", width=3, dash="dot"),
                            marker=dict(symbol="star", size=14, color="#8B5CF6"),
                            error_y=dict(
                                type='data',
                                symmetric=False,
                                array=[intervalo[1] - pred_val],
                                arrayminus=[pred_val - intervalo[0]],
                                color='#8B5CF6',
                                thickness=2,
                                width=8
                            )
                        ))

                        fig_prog.update_layout(
                            title=f"Trayectoria Educativa de {estudiante_seleccionado} + Proyección de Puntaje ICFES",
                            yaxis=dict(title="Puntaje Global / Ponderado", range=[0, 500]),
                            xaxis=dict(title="Evaluación Cronológica"),
                            height=430,
                            template="plotly_white",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        st.plotly_chart(fig_prog, use_container_width=True, key="fig_prog_ml_pred")

                        # Leyenda técnica explicativa docente
                        st.info(
                            f"💡 **Predicción Global del Modelo:** `{pred_val:.1f} pts` (Rango estimado: `[{intervalo[0]} - {intervalo[1]} pts]`). "
                            f"**MAE de validación cruzada:** `{mae_loocv:.1f}` pts. "
                            f"*El modelo evalúa la progresión de simulacros sin ver el resultado real del examen.*"
                        )

                        # Desglose de predicciones por asignatura
                        preds_subs = res_pred.get("predicciones_materias")
                        if preds_subs:
                            st.markdown("#### 🎯 Proyección de Puntajes por Asignatura (Escala 0-100)")
                            c_mat_cols = st.columns(5)
                            for idx_m, (m_nombre, m_info) in enumerate(preds_subs.items()):
                                with c_mat_cols[idx_m % 5]:
                                    st.metric(
                                        label=m_nombre,
                                        value=f"{m_info['puntaje']:.1f}",
                                        delta=f"[{m_info['intervalo'][0]} - {m_info['intervalo'][1]}]",
                                        delta_color="off"
                                    )

                        if res_pred.get("confiabilidad") == "baja" or res_pred.get("simulacros_incompletos"):
                            st.warning(
                                f"⚠️ **Advertencia de Confiabilidad Moderada:** El estudiante presenta menos de 4 simulacros. "
                                f"El rango estimado [{intervalo[0]} - {intervalo[1]} pts] se irá refinando conforme presente más pruebas."
                            )
                    else:
                        fig_prog.update_layout(
                            title=f"Trayectoria Educativa de {estudiante_seleccionado} (Simulacros)",
                            yaxis=dict(title="Puntaje Global / Ponderado", range=[0, 500]),
                            xaxis=dict(title="Evaluación Cronológica"),
                            height=400,
                            template="plotly_white"
                        )
                        st.plotly_chart(fig_prog, use_container_width=True, key="fig_prog_inc_hist")

                        if es_inclusion:
                            st.info(
                                "ℹ️ **Estudiante en Condición de Inclusión:** Conforme a los lineamientos pedagógicos e institucionales, "
                                "los estudiantes con adecuaciones curriculares no reciben una proyección numérica estandarizada del ICFES. "
                                "Se presenta únicamente su trayectoria descriptiva de simulacros para seguimiento formativo."
                            )

        except Exception as e:
            st.error(f"Error al cargar el gráfico de progresión y predicción: {e}")
        finally:
            conn.close()
    else:
        st.info("No hay conexión activa con la base de datos para cargar la trayectoria temporal.")

    # =========================================================================
    # SECCIÓN PERFIL DE COMPETENCIAS Y RADAR
    # =========================================================================
    st.markdown("<h2 class='section-header'>📊 Perfil de Competencias</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    valores_estudiante = [datos_estudiante[mat] if pd.notna(datos_estudiante[mat]) else 0 for mat in materias]
    promedios_grupo = [datos_actual[mat].dropna().mean() if not datos_actual[mat].dropna().empty else 0 for mat in materias]
    valores_icfes_real = [icfes_row[mat] if (has_icfes_real and mat in icfes_row and pd.notna(icfes_row[mat])) else None for mat in materias]

    # Extraer valores proyectados por materia si existen
    valores_proyectados = None
    if res_pred and res_pred.get("predicciones_materias"):
        sub_dict = res_pred["predicciones_materias"]
        valores_proyectados = [sub_dict.get(mat, {}).get("puntaje", 0.0) for mat in materias]

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=valores_estudiante, theta=materias, fill="toself", name="Simulacro Activo", line_color="#667eea"))
        if valores_proyectados:
            fig.add_trace(go.Scatterpolar(r=valores_proyectados, theta=materias, fill="toself", name="🔮 Proyección ICFES", line_color="#8B5CF6", opacity=0.7))
        if has_icfes_real and any(v is not None for v in valores_icfes_real):
            fig.add_trace(go.Scatterpolar(r=[v if v is not None else 0 for v in valores_icfes_real], theta=materias, fill="toself", name="🎯 ICFES Real", line_color="#f1c40f", opacity=0.8))
        fig.add_trace(go.Scatterpolar(r=promedios_grupo, theta=materias, fill="toself", name="Promedio Grupo", line_color="#e74c3c", opacity=0.5))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, height=450, title="Radar de Competencias")
        st.plotly_chart(fig, use_container_width=True, key="fig_radar_ind")

    with col2:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(x=materias, y=valores_estudiante, name="Simulacro", marker_color="#667eea"))
        if valores_proyectados:
            fig_bar.add_trace(go.Bar(x=materias, y=valores_proyectados, name="🔮 Proyección", marker_color="#8B5CF6"))
        if has_icfes_real and any(v is not None for v in valores_icfes_real):
            fig_bar.add_trace(go.Bar(x=materias, y=[v if v is not None else 0 for v in valores_icfes_real], name="🎯 ICFES Real", marker_color="#f1c40f"))
        fig_bar.add_trace(go.Scatter(x=materias, y=promedios_grupo, mode="markers+lines", name="Prom. Grupo", line=dict(color="#e74c3c", dash="dash"), marker=dict(size=10)))
        fig_bar.update_layout(barmode="group", title="Puntajes por Materia", yaxis_title="Puntaje", height=450, template="plotly_white")
        st.plotly_chart(fig_bar, use_container_width=True, key="fig_bar_ind")

    st.markdown("<h2 class='section-header'>📋 Detalle Comparativo de Puntajes</h2>", unsafe_allow_html=True)
    tabla_dict = {
        "Materia": materias,
        "Simulacro Activo": [datos_estudiante[mat] for mat in materias],
    }
    if valores_proyectados:
        tabla_dict["🔮 Proyección (Modelo)"] = valores_proyectados

    if has_icfes_real and any(v is not None for v in valores_icfes_real):
        tabla_dict["🎯 ICFES Real"] = valores_icfes_real
        tabla_dict["Δ (ICFES - Sim)"] = [r - s if (r is not None and pd.notna(s)) else None for r, s in zip(valores_icfes_real, [datos_estudiante[mat] for mat in materias])]

    tabla_dict["Promedio Grupo"] = promedios_grupo

    detalle_df = pd.DataFrame(tabla_dict).round(2)
    st.dataframe(
        detalle_df.style.format(na_rep="No presentó"),
        use_container_width=True,
    )
