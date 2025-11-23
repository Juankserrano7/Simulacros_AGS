from functools import reduce

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render(simulacros, materias):
    if len(simulacros) < 2:
        st.warning("Carga al menos dos simulacros para ver el avance.")
        return

    st.markdown("<h1 class='header-title'>Análisis de Avance</h1>", unsafe_allow_html=True)

    frames = []
    for sim in simulacros:
        temp = sim["df"][["ESTUDIANTE", "PROMEDIO PONDERADO"]].copy()
        temp["ESTUDIANTE"] = temp["ESTUDIANTE"].str.strip().str.upper()
        temp = temp.rename(columns={"PROMEDIO PONDERADO": sim["nombre"]})
        frames.append(temp)

    progresion = reduce(lambda left, right: left.merge(right, on="ESTUDIANTE", how="outer"), frames)
    simulacro_cols = [col for col in progresion.columns if col != "ESTUDIANTE"]
    progresion["CAMBIO_TOTAL"] = progresion[simulacro_cols[-1]] - progresion[simulacro_cols[0]]
    if len(simulacro_cols) >= 2:
        progresion["CAMBIO_ULTIMO"] = progresion[simulacro_cols[-1]] - progresion[simulacro_cols[-2]]
    else:
        progresion["CAMBIO_ULTIMO"] = 0

    st.markdown(f"**Estudiantes encontrados:** {len(progresion)}")
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
            <p style='opacity:0.9;'>{simulacro_cols[-2]} → {simulacro_cols[-1]}</p>
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
            <p style='opacity:0.9;'>{simulacro_cols[-2]} → {simulacro_cols[-1]}</p>
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
    st.markdown("<h2 class='section-header'>📊 Avance por estudiante (última transición)</h2>", unsafe_allow_html=True)
    progresion_sorted = progresion.sort_values("CAMBIO_ULTIMO")
    colores = ["#27ae60" if c > 0 else "#e74c3c" for c in progresion_sorted["CAMBIO_ULTIMO"]]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=progresion_sorted["ESTUDIANTE"].str.split().str[0],
            x=progresion_sorted["CAMBIO_ULTIMO"],
            orientation="h",
            marker_color=colores,
            text=[f"{c:.1f}" for c in progresion_sorted["CAMBIO_ULTIMO"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=f"Cambio de rendimiento: {simulacro_cols[-2]} → {simulacro_cols[-1]}",
        xaxis_title="Cambio en Promedio Ponderado",
        yaxis_title="Estudiante",
        height=700,
        template="plotly_white",
    )
    fig.add_vline(x=0, line_dash="dash", line_color="black")
    st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📈 Evolución individual</h2>", unsafe_allow_html=True)
    estudiantes_mostrar = st.multiselect(
        "Seleccionar estudiantes para comparar",
        progresion["ESTUDIANTE"].tolist(),
        default=progresion.nlargest(5, simulacro_cols[-1])["ESTUDIANTE"].tolist()[:5],
    )
    if estudiantes_mostrar:
        fig = go.Figure()
        for estudiante in estudiantes_mostrar:
            datos_est = progresion[progresion["ESTUDIANTE"] == estudiante].iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=simulacro_cols,
                    y=[datos_est[col] for col in simulacro_cols],
                    mode="lines+markers",
                    name=estudiante.split()[0],
                    line=dict(width=3),
                    marker=dict(size=8),
                )
            )
        fig.update_layout(
            title="Evolución individual",
            xaxis_title="Simulacro",
            yaxis_title="Promedio Ponderado",
            height=500,
            template="plotly_white",
            hovermode="x unified",
        )
        st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📋 Tabla de avance</h2>", unsafe_allow_html=True)
    tabla_progresion = progresion[["ESTUDIANTE"] + simulacro_cols + ["CAMBIO_ULTIMO", "CAMBIO_TOTAL"]]
    tabla_progresion = tabla_progresion.sort_values("CAMBIO_TOTAL", ascending=False).round(2)
    columnas_num = tabla_progresion.select_dtypes(include=["float64", "int64"]).columns
    st.dataframe(
        tabla_progresion.style.format({col: "{:.2f}" for col in columnas_num}).background_gradient(
            subset=["CAMBIO_ULTIMO", "CAMBIO_TOTAL"], cmap="RdYlGn", vmin=-50, vmax=50
        ),
        width="stretch",
        height=600,
    )
