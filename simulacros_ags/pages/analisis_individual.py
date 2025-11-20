import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render(datos_actual, materias):
    st.markdown("<h1 class='header-title'>👤 Análisis Individual de Estudiantes</h1>", unsafe_allow_html=True)

    estudiante_seleccionado = st.selectbox("Seleccionar Estudiante", sorted(datos_actual["ESTUDIANTE"].unique()))
    datos_estudiante = datos_actual[datos_actual["ESTUDIANTE"] == estudiante_seleccionado].iloc[0]

    st.markdown(f"### 📊 Resultados de: **{estudiante_seleccionado}**")
    if "GRADO" in datos_estudiante:
        st.markdown(f"**Grado:** {datos_estudiante['GRADO']}")

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🎯 Promedio Ponderado", f"{datos_estudiante['PROMEDIO PONDERADO']:.1f}")
    with col2:
        percentil = (datos_actual["PROMEDIO PONDERADO"] < datos_estudiante["PROMEDIO PONDERADO"]).sum() / len(datos_actual) * 100
        st.metric("📊 Percentil", f"{percentil:.1f}%")
    with col3:
        ranking = datos_actual.sort_values("PROMEDIO PONDERADO", ascending=False).reset_index(drop=True)
        posicion = ranking[ranking["ESTUDIANTE"] == estudiante_seleccionado].index[0] + 1
        st.metric("🏆 Posición", f"{posicion} / {len(datos_actual)}")
    with col4:
        mejor_materia = max(materias, key=lambda m: datos_estudiante[m])
        st.metric("⭐ Mejor Materia", mejor_materia.split()[0])

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📊 Perfil de Competencias</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    valores_estudiante = [datos_estudiante[mat] for mat in materias]
    promedios_grupo = [datos_actual[mat].mean() for mat in materias]

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=valores_estudiante, theta=materias, fill="toself", name="Estudiante", line_color="#667eea"))
        fig.add_trace(
            go.Scatterpolar(r=promedios_grupo, theta=materias, fill="toself", name="Promedio Grupo", line_color="#e74c3c", opacity=0.6)
        )
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, height=450, title="Comparación con el Promedio del Grupo")
        st.plotly_chart(fig, width="stretch")

    with col2:
        colores = ["#27ae60" if v >= p else "#e74c3c" for v, p in zip(valores_estudiante, promedios_grupo)]
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=materias,
                y=valores_estudiante,
                marker_color=colores,
                text=[f"{v:.1f}" for v in valores_estudiante],
                textposition="outside",
                name="Puntajes",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=materias,
                y=promedios_grupo,
                mode="markers+lines",
                name="Promedio Grupo",
                line=dict(color="red", dash="dash"),
                marker=dict(size=10),
            )
        )
        fig.update_layout(title="Puntajes por Materia", yaxis_title="Puntaje", height=450, template="plotly_white")
        st.plotly_chart(fig, width="stretch")

    st.markdown("<h2 class='section-header'>📋 Detalle de Puntajes</h2>", unsafe_allow_html=True)
    detalle_df = pd.DataFrame(
        {"Materia": materias, "Puntaje": valores_estudiante, "Promedio Grupo": promedios_grupo, "Diferencia": [e - g for e, g in zip(valores_estudiante, promedios_grupo)]}
    ).round(2)
    columnas_num = detalle_df.select_dtypes(include=["float64", "int64"]).columns
    st.dataframe(
        detalle_df.style.format({col: "{:.2f}" for col in columnas_num}).background_gradient(
            subset=["Diferencia"],
            cmap="RdYlGn",
            vmin=-20,
            vmax=20,
        ),
        width="stretch",
    )
