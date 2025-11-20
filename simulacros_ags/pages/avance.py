import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render(hp1, hp2, prep, materias):
    st.markdown("<h1 class='header-title'>Análisis de Avance</h1>", unsafe_allow_html=True)

    hp1_temp = hp1.copy()
    hp2_temp = hp2.copy()
    prep_temp = prep.copy()
    hp1_temp["ESTUDIANTE"] = hp1_temp["ESTUDIANTE"].str.strip().str.upper()
    hp2_temp["ESTUDIANTE"] = hp2_temp["ESTUDIANTE"].str.strip().str.upper()
    prep_temp["ESTUDIANTE"] = prep_temp["ESTUDIANTE"].str.strip().str.upper()

    progresion = pd.merge(
        hp1_temp[["ESTUDIANTE", "PROMEDIO PONDERADO"]],
        hp2_temp[["ESTUDIANTE", "PROMEDIO PONDERADO"]],
        on="ESTUDIANTE",
        suffixes=("_HP1", "_HP2"),
    )
    progresion = pd.merge(progresion, prep_temp[["ESTUDIANTE", "PROMEDIO PONDERADO"]], on="ESTUDIANTE")
    progresion.columns = ["ESTUDIANTE", "HP1", "HP2", "Avancemos"]
    progresion["CAMBIO_HP1_HP2"] = progresion["HP2"] - progresion["HP1"]
    progresion["CAMBIO_HP2AVAN"] = progresion["Avancemos"] - progresion["HP2"]
    progresion["CAMBIO_TOTAL"] = progresion["Avancemos"] - progresion["HP1"]

    st.markdown(f"**Estudiantes encontrados en los 3 simulacros:** {len(progresion)}")
    col1, col2, col3 = st.columns(3)
    with col1:
        mejoraron_hp2 = (progresion["CAMBIO_HP1_HP2"] > 0).sum()
        st.metric("📈 Mejoraron HP1→HP2", f"{mejoraron_hp2} ({mejoraron_hp2/len(progresion)*100:.1f}%)")
    with col2:
        empeoraron_hp2 = (progresion["CAMBIO_HP1_HP2"] < 0).sum()
        st.metric("📉 Empeoraron HP1→HP2", f"{empeoraron_hp2} ({empeoraron_hp2/len(progresion)*100:.1f}%)")
    with col3:
        st.metric("📊 Cambio Promedio HP1→HP2", f"{progresion['CAMBIO_HP1_HP2'].mean():.2f}")

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📊 Avance Individual (HP1 → HP2)</h2>", unsafe_allow_html=True)
    progresion_sorted = progresion.sort_values("CAMBIO_HP1_HP2")
    colores = ["#27ae60" if c > 0 else "#e74c3c" for c in progresion_sorted["CAMBIO_HP1_HP2"]]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=progresion_sorted["ESTUDIANTE"].str.split().str[0],
            x=progresion_sorted["CAMBIO_HP1_HP2"],
            orientation="h",
            marker_color=colores,
            text=[f"{c:.1f}" for c in progresion_sorted["CAMBIO_HP1_HP2"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Cambio de Rendimiento: Helmer Pardo 1 → Helmer Pardo 2",
        xaxis_title="Cambio en Promedio Ponderado",
        yaxis_title="Estudiante",
        height=800,
        template="plotly_white",
    )
    fig.add_vline(x=0, line_dash="dash", line_color="black")
    st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📈 Evolución de los 3 Simulacros</h2>", unsafe_allow_html=True)
    estudiantes_mostrar = st.multiselect(
        "Seleccionar estudiantes para comparar",
        progresion["ESTUDIANTE"].tolist(),
        default=progresion.nlargest(5, "Avancemos")["ESTUDIANTE"].tolist()[:5],
    )
    if estudiantes_mostrar:
        fig = go.Figure()
        for estudiante in estudiantes_mostrar:
            datos_est = progresion[progresion["ESTUDIANTE"] == estudiante].iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=["HP1", "HP2", "AVANCEMOS"],
                    y=[datos_est["HP1"], datos_est["HP2"], datos_est["Avancemos"]],
                    mode="lines+markers",
                    name=estudiante.split()[0],
                    line=dict(width=3),
                    marker=dict(size=10),
                )
            )
        fig.update_layout(
            title="Evolución Individual en los 3 Simulacros",
            xaxis_title="Simulacro",
            yaxis_title="Promedio Ponderado",
            height=500,
            template="plotly_white",
            hovermode="x unified",
        )
        st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📋 Tabla de Avance Completa</h2>", unsafe_allow_html=True)
    st.markdown("<div>", unsafe_allow_html=True)
    tabla_progresion = progresion[["ESTUDIANTE", "HP1", "HP2", "Avancemos", "CAMBIO_HP1_HP2", "CAMBIO_HP2AVAN", "CAMBIO_TOTAL"]]
    tabla_progresion = tabla_progresion.sort_values("CAMBIO_TOTAL", ascending=False).round(2)
    columnas_num = tabla_progresion.select_dtypes(include=["float64", "int64"]).columns
    st.dataframe(
        tabla_progresion.style.format({col: "{:.2f}" for col in columnas_num}).background_gradient(
            subset=["CAMBIO_HP1_HP2", "CAMBIO_HP2AVAN", "CAMBIO_TOTAL"], cmap="RdYlGn", vmin=-50, vmax=50
        ),
        width="stretch",
        height=600,
    )
