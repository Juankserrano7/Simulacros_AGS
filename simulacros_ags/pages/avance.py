from functools import reduce
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..data import load_icfes_real_data


def render(simulacros, materias):
    if len(simulacros) < 1:
        st.warning("Carga al menos un simulacro para ver el avance.")
        return

    promocion_id = st.session_state.get("promocion_activa_id")
    df_icfes_real = load_icfes_real_data(promocion_id)
    has_icfes_real = not df_icfes_real.empty

    title_text = "📈 Análisis de Avance hacia el ICFES Real" if has_icfes_real else "📈 Análisis de Avance de Simulacros"
    st.markdown(f"<h1 class='header-title'>{title_text}</h1>", unsafe_allow_html=True)

    frames = []
    for sim in simulacros:
        temp = sim["df"][["ESTUDIANTE", "PROMEDIO PONDERADO"]].copy()
        temp["ESTUDIANTE"] = temp["ESTUDIANTE"].str.strip().str.upper()
        temp = temp.rename(columns={"PROMEDIO PONDERADO": sim["nombre"]})
        frames.append(temp)

    if has_icfes_real and "ESTUDIANTE" in df_icfes_real.columns:
        temp_real = df_icfes_real[["ESTUDIANTE", "PROMEDIO PONDERADO"]].copy()
        temp_real["ESTUDIANTE"] = temp_real["ESTUDIANTE"].str.strip().str.upper()
        temp_real = temp_real.rename(columns={"PROMEDIO PONDERADO": "🎯 ICFES Real"})
        frames.append(temp_real)

    progresion = reduce(lambda left, right: left.merge(right, on="ESTUDIANTE", how="outer"), frames)
    eval_cols = [col for col in progresion.columns if col != "ESTUDIANTE"]

    if len(eval_cols) >= 2:
        progresion["CAMBIO_TOTAL"] = progresion[eval_cols[-1]] - progresion[eval_cols[0]]
        progresion["CAMBIO_ULTIMO"] = progresion[eval_cols[-1]] - progresion[eval_cols[-2]]
    else:
        progresion["CAMBIO_TOTAL"] = 0
        progresion["CAMBIO_ULTIMO"] = 0

    st.markdown(f"**Estudiantes monitoreados:** {len(progresion)}")
    col1, col2, col3 = st.columns(3)
    mejoraron = (progresion["CAMBIO_ULTIMO"] > 0).sum()
    empeoraron = (progresion["CAMBIO_ULTIMO"] < 0).sum()
    cambio_prom = progresion["CAMBIO_ULTIMO"].mean()
    with col1:
        st.markdown(
            f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); color: white;'>
            <h4>📈 Subieron</h4>
            <h2 style='margin:0;'>{mejoraron}</h2>
            <p style='opacity:0.9;'>{eval_cols[-2] if len(eval_cols)>=2 else '-'} → {eval_cols[-1]}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); color: white;'>
            <h4>📉 Bajaron</h4>
            <h2 style='margin:0;'>{empeoraron}</h2>
            <p style='opacity:0.9;'>{eval_cols[-2] if len(eval_cols)>=2 else '-'} → {eval_cols[-1]}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #00c6ff 0%, #0072ff 100%); color: white;'>
            <h4>📊 Cambio promedio</h4>
            <h2 style='margin:0;'>{cambio_prom:.2f}</h2>
            <p style='opacity:0.9;'>Puntos</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown(f"<h2 class='section-header'>📊 Avance por estudiante ({eval_cols[-2] if len(eval_cols)>=2 else '-'} → {eval_cols[-1]})</h2>", unsafe_allow_html=True)
    progresion_sorted = progresion.sort_values("CAMBIO_ULTIMO")
    colores = ["#27ae60" if c > 0 else "#e74c3c" for c in progresion_sorted["CAMBIO_ULTIMO"]]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=progresion_sorted["ESTUDIANTE"].str.split().str[0],
            x=progresion_sorted["CAMBIO_ULTIMO"],
            orientation="h",
            marker_color=colores,
            text=[f"{c:.1f}" if pd.notna(c) else "-" for c in progresion_sorted["CAMBIO_ULTIMO"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=f"Cambio de rendimiento: {eval_cols[-2] if len(eval_cols)>=2 else '-'} → {eval_cols[-1]}",
        xaxis_title="Cambio en Puntos",
        yaxis_title="Estudiante",
        height=750,
        template="plotly_white",
    )
    fig.add_vline(x=0, line_dash="dash", line_color="black")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📈 Evolución Individual</h2>", unsafe_allow_html=True)
    estudiantes_mostrar = st.multiselect(
        "Seleccionar estudiantes para comparar la evolución histórica",
        progresion["ESTUDIANTE"].tolist(),
        default=progresion.nlargest(5, eval_cols[-1])["ESTUDIANTE"].tolist()[:5],
    )
    if estudiantes_mostrar:
        fig_ind = go.Figure()
        for estudiante in estudiantes_mostrar:
            sub_est = progresion[progresion["ESTUDIANTE"] == estudiante]
            if not sub_est.empty:
                datos_est = sub_est.iloc[0]
                fig_ind.add_trace(
                    go.Scatter(
                        x=eval_cols,
                        y=[datos_est[col] for col in eval_cols],
                        mode="lines+markers+text",
                        text=[f"{datos_est[col]:.0f}" if pd.notna(datos_est[col]) else "" for col in eval_cols],
                        textposition="top center",
                        name=estudiante.split()[0],
                        line=dict(width=3),
                        marker=dict(size=10),
                    )
                )
        fig_ind.update_layout(
            title="Evolución del Puntaje por Estudiante",
            xaxis_title="Evaluación / Prueba",
            yaxis_title="Puntaje Ponderado / Global",
            height=500,
            template="plotly_white",
            hovermode="x unified",
        )
        st.plotly_chart(fig_ind, use_container_width=True)

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📋 Tabla Resumen de Avance</h2>", unsafe_allow_html=True)
    tabla_progresion = progresion[["ESTUDIANTE"] + eval_cols + ["CAMBIO_ULTIMO", "CAMBIO_TOTAL"]].copy()
    tabla_progresion = tabla_progresion.sort_values("CAMBIO_TOTAL", ascending=False).round(2)
    columnas_num = tabla_progresion.select_dtypes(include=["float64", "int64"]).columns
    st.dataframe(
        tabla_progresion.style.format({col: "{:.2f}" for col in columnas_num}, na_rep="No presentó").background_gradient(
            subset=["CAMBIO_ULTIMO", "CAMBIO_TOTAL"], cmap="RdYlGn", vmin=-50, vmax=50
        ),
        use_container_width=True,
        height=650,
    )
