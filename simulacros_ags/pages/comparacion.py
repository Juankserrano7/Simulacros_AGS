import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render(hp1, hp2, prep, materias):
    st.markdown("<h1 class='header-title'>🔬 Comparación entre Simulacros</h1>", unsafe_allow_html=True)
    st.markdown("<h2 class='section-header'>📊 Comparación de Promedios por Materia</h2>", unsafe_allow_html=True)

    promedios_hp1 = [hp1[mat].mean() for mat in materias]
    promedios_hp2 = [hp2[mat].mean() for mat in materias]
    promedios_avan = [prep[mat].mean() for mat in materias]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Helmer Pardo 1", x=materias, y=promedios_hp1, marker_color="#3498db"))
    fig.add_trace(go.Bar(name="Helmer Pardo 2", x=materias, y=promedios_hp2, marker_color="#2ecc71"))
    fig.add_trace(go.Bar(name="AVANCEMOS", x=materias, y=promedios_avan, marker_color="#e74c3c"))
    fig.update_layout(
        barmode="group", height=500, title="Comparación de Promedios por Materia", xaxis_title="Materia", yaxis_title="Puntaje Promedio", template="plotly_white"
    )
    st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📋 Tabla Comparativa</h2>", unsafe_allow_html=True)
    comp_df = pd.DataFrame(
        {
            "Materia": materias,
            "HP1": promedios_hp1,
            "HP2": promedios_hp2,
            "AVANCEMOS": promedios_avan,
            "Cambio HP1→HP2": [hp2 - hp1 for hp1, hp2 in zip(promedios_hp1, promedios_hp2)],
            "Cambio HP2→AVAN": [prep - hp2 for hp2, prep in zip(promedios_hp2, promedios_avan)],
        }
    ).round(2)
    columnas_numericas = comp_df.select_dtypes(include=["float64", "int64"]).columns
    st.dataframe(
        comp_df.style.format({col: "{:.2f}" for col in columnas_numericas}).background_gradient(
            subset=["Cambio HP1→HP2", "Cambio HP2→AVAN"], cmap="RdYlGn", vmin=-20, vmax=20
        ),
        width="stretch",
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📈 Evolución del Promedio General</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])

    promedios_generales = [hp1["PROMEDIO PONDERADO"].mean(), hp2["PROMEDIO PONDERADO"].mean(), prep["PROMEDIO PONDERADO"].mean()]
    with col1:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=["Helmer Pardo 1", "Helmer Pardo 2", "AVANCEMOS"],
                y=promedios_generales,
                mode="lines+markers+text",
                text=[f"{p:.2f}" for p in promedios_generales],
                textposition="top center",
                line=dict(color="#667eea", width=4),
                marker=dict(size=15, color=["#27ae60", "#f39c12", "#e74c3c"]),
            )
        )
        fig.update_layout(title="Tendencia del Promedio Ponderado", yaxis_title="Promedio Ponderado", height=600, template="plotly_white")
        st.plotly_chart(fig, width="stretch")

    with col2:
        cambio_1_2 = promedios_generales[1] - promedios_generales[0]
        cambio_2_3 = promedios_generales[2] - promedios_generales[1]
        st.markdown("### 📉 Cambios Registrados")
        st.markdown(
            f"""
        <div class='stats-box'>
            <h4>HP1 → HP2</h4>
            <h2>{cambio_1_2:.2f}</h2>
            <p>puntos</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        st.markdown(f"""<div style='margin: 1rem 0;'></div>""", unsafe_allow_html=True)
        st.markdown(
            f"""
        <div class='stats-box' style='background: linear-gradient(135deg, #00c6ff 0%, #0072ff 100%);'>
            <h4>HP2 → AVANCEMOS</h4>
            <h2>{cambio_2_3:.2f}</h2>
            <p>puntos</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
