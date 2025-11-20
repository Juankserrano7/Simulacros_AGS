import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render(hp1, hp2, prep, materias):
    st.markdown("<h1 class='header-title'> Dashboard de Análisis de Simulacros PreIcfes</h1>", unsafe_allow_html=True)
    st.markdown("<p class='header-subtitle'>Sistema Integral de Evaluación y Seguimiento - Grado 11</p>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div class='metric-card'>
            <h3 style='color: #667eea;'>📝Simulacros</h3>
            <h2 style='font-size: 3rem; color: #764ba2;'>3</h2>
            <p style='color: #6c757d;'>HP1, HP2, AVANCEMOS</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        total_estudiantes = len(hp1)
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='color: #667eea;'>👥Estudiantes</h3>
            <h2 style='font-size: 3rem; color: #764ba2;'>{total_estudiantes}</h2>
            <p style='color: #6c757d;'>Evaluados</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='color: #667eea;'>📚Áreas</h3>
            <h2 style='font-size: 3rem; color: #764ba2;'>5</h2>
            <p style='color: #6c757d;'>Materias ICFES</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        total_datos = len(hp1) + len(hp2) + len(prep)
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='color: #667eea;'>📋Registros</h3>
            <h2 style='font-size: 3rem; color: #764ba2;'>{total_datos}</h2>
            <p style='color: #6c757d;'>Datos totales</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("<h2 class='section-header'>📊 Análisis Comparativo de Simulacros</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    promedios_generales = [
        hp1["PROMEDIO PONDERADO"].mean(),
        hp2["PROMEDIO PONDERADO"].mean(),
        prep["PROMEDIO PONDERADO"].mean(),
    ]

    with col1:
        st.markdown("### 📈 Evolución de Promedios")

        promedios_data = pd.DataFrame(
            {
                "Simulacro": ["Helmer Pardo 1", "Helmer Pardo 2", "AVANCEMOS"],
                "Promedio": promedios_generales,
                "Desv. Est.": [
                    hp1["PROMEDIO PONDERADO"].std(),
                    hp2["PROMEDIO PONDERADO"].std(),
                    prep["PROMEDIO PONDERADO"].std(),
                ],
            }
        )

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=promedios_data["Simulacro"],
                y=promedios_data["Promedio"],
                marker_color=["#27ae60", "#f39c12", "#e74c3c"],
                text=[f"{p:.1f}" for p in promedios_data["Promedio"]],
                textposition="outside",
                name="Promedio",
            )
        )
        fig.update_layout(
            height=500,
            showlegend=False,
            yaxis_title="Puntaje Promedio",
            template="plotly_white",
        )
        st.plotly_chart(fig, width="stretch")

        cambio_1_2 = promedios_generales[1] - promedios_generales[0]
        cambio_2_3 = promedios_generales[2] - promedios_generales[1]
        cambio_total = promedios_generales[2] - promedios_generales[0]

        st.markdown("#### 📉 Variaciones Detectadas")
        cambios_df = pd.DataFrame(
            {
                "Transición": ["HP1 → HP2", "HP2 → Avan", "HP1 → Avan"],
                "Cambio": [cambio_1_2, cambio_2_3, cambio_total],
                "Porcentaje": [
                    (cambio_1_2 / promedios_generales[0] * 100),
                    (cambio_2_3 / promedios_generales[1] * 100),
                    (cambio_total / promedios_generales[0] * 100),
                ],
            }
        )
        cambios_df["Cambio"] = cambios_df["Cambio"].round(2)
        cambios_df["Porcentaje"] = cambios_df["Porcentaje"].round(2).astype(str) + "%"
        st.dataframe(cambios_df, width="stretch", hide_index=True)

    with col2:
        st.markdown("### 📊 Distribución de Rendimiento por Simulacro")

        def calcular_distribucion(df):
            alto = len(df[df["PROMEDIO PONDERADO"] >= 300])
            medio = len(df[(df["PROMEDIO PONDERADO"] >= 250) & (df["PROMEDIO PONDERADO"] < 300)])
            bajo = len(df[df["PROMEDIO PONDERADO"] < 250])
            return [alto, medio, bajo]

        dist_hp1 = calcular_distribucion(hp1)
        dist_hp2 = calcular_distribucion(hp2)
        dist_avan = calcular_distribucion(prep)

        fig = go.Figure()
        categorias = ["Alto (≥300)", "Medio (250-299)", "Bajo (<250)"]

        fig.add_trace(go.Bar(name="HP1", x=categorias, y=dist_hp1, marker_color="#27ae60"))
        fig.add_trace(go.Bar(name="HP2", x=categorias, y=dist_hp2, marker_color="#f39c12"))
        fig.add_trace(go.Bar(name="AVAN", x=categorias, y=dist_avan, marker_color="#e74c3c"))

        fig.update_layout(
            barmode="group",
            height=475,
            yaxis_title="Número de Estudiantes",
            template="plotly_white",
        )
        st.plotly_chart(fig, width="stretch")

        st.markdown("#### 📋 Resumen de Distribución")
        dist_df = pd.DataFrame({"Nivel": categorias, "HP1": dist_hp1, "HP2": dist_hp2, "Avancemos": dist_avan})
        st.dataframe(dist_df, width="stretch", hide_index=True)

    st.markdown("---")

    st.markdown("<h2 class='section-header'>📚 Análisis Detallado por Materia</h2>", unsafe_allow_html=True)

    promedios_hp1 = [hp1[mat].mean() for mat in materias]
    promedios_hp2 = [hp2[mat].mean() for mat in materias]
    promedios_avan = [prep[mat].mean() for mat in materias]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=promedios_hp1, theta=materias, fill="toself", name="HP1", line_color="#27ae60"))
    fig.add_trace(
        go.Scatterpolar(r=promedios_hp2, theta=materias, fill="toself", name="HP2", line_color="#f39c12", opacity=0.7)
    )
    fig.add_trace(
        go.Scatterpolar(r=promedios_avan, theta=materias, fill="toself", name="Avancemos", line_color="#e74c3c", opacity=0.7)
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=500,
        title="Comparación de Rendimiento por Materia",
    )
    st.plotly_chart(fig, width="stretch")

    st.markdown("#### 📊 Tabla Comparativa de Materias")

    comp_materias_df = pd.DataFrame(
        {
            "Materia": materias,
            "HP1": promedios_hp1,
            "HP2": promedios_hp2,
            "Avancemos": promedios_avan,
            "Mejor": [max(a, b, c) for a, b, c in zip(promedios_hp1, promedios_hp2, promedios_avan)],
            "Menor": [min(a, b, c) for a, b, c in zip(promedios_hp1, promedios_hp2, promedios_avan)],
            "Rango": [max(a, b, c) - min(a, b, c) for a, b, c in zip(promedios_hp1, promedios_hp2, promedios_avan)],
        }
    )
    comp_materias_df = comp_materias_df.round(2).replace(0, "")
    columnas_numericas = comp_materias_df.select_dtypes(include=["float64", "int64"]).columns

    st.dataframe(
        comp_materias_df.style.format({col: "{:.2f}" for col in columnas_numericas}).background_gradient(
            subset=["HP1", "HP2", "Avancemos"], cmap="RdYlGn", vmin=40, vmax=90
        ),
        width="stretch",
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("<h2 class='section-header'>🔍 Hallazgos Principales y Recomendaciones</h2>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    cambio_hp1_hp2 = hp2["PROMEDIO PONDERADO"].mean() - hp1["PROMEDIO PONDERADO"].mean()
    mejor_materia = max(materias, key=lambda m: hp1[m].mean())
    peor_materia = min(materias, key=lambda m: hp1[m].mean())

    variabilidades = {mat: hp1[mat].std() for mat in materias}
    mat_variable = max(variabilidades, key=variabilidades.get)

    cambios_materias = {mat: hp2[mat].mean() - hp1[mat].mean() for mat in materias}
    mat_mayor_caida = min(cambios_materias, key=cambios_materias.get)
    mat_mayor_mejora = max(cambios_materias, key=cambios_materias.get)

    with col1:
        st.markdown(
            f"""
        <div class='alert-warning'>
            <h4>⚠️ Áreas de Atención Prioritaria</h4>
            <ul>
                <li><strong>Caída General:</strong> {abs(cambio_hp1_hp2):.1f} puntos entre HP1 y HP2 ({abs(cambio_hp1_hp2/promedios_generales[0]*100):.1f}%)</li>
                <li><strong>Materia con Mayor Caída:</strong> {mat_mayor_caida} ({cambios_materias[mat_mayor_caida]:.1f} puntos)</li>
                <li><strong>Materia más Variable:</strong> {mat_variable} (σ = {variabilidades[mat_variable]:.1f})</li>
                <li><strong>Puntaje Promedio más Bajo:</strong> {peor_materia} ({min(promedios_hp1):.1f} puntos)</li>
                <li><strong>Estudiantes en Riesgo:</strong> {len(hp1[hp1['PROMEDIO PONDERADO'] < 250])} ({len(hp1[hp1['PROMEDIO PONDERADO'] < 250])/len(hp1)*100:.1f}%)</li>
            </ul>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
        <div class='alert-success'>
            <h4>✅ Fortalezas y Oportunidades</h4>
            <ul>
                <li><strong>Mejor Materia:</strong> {mejor_materia} ({max(promedios_hp1):.1f} puntos promedio)</li>
                <li><strong>Materia con Mayor Mejora:</strong> {mat_mayor_mejora} (+{cambios_materias[mat_mayor_mejora]:.1f} puntos)</li>
                <li><strong>Estudiantes Destacados:</strong> {len(hp1[hp1['PROMEDIO PONDERADO'] >= 350])} con puntaje ≥350</li>
                <li><strong>Consistencia:</strong> {materias[np.argmin([hp1[m].std() for m in materias])]} es la más consistente</li>
                <li><strong>Potencial de Mejora:</strong> Identificados {len(hp1[(hp1['PROMEDIO PONDERADO'] >= 250) & (hp1['PROMEDIO PONDERADO'] < 300)])} estudiantes en rango medio</li>
            </ul>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("<h2 class='section-header'>💡 Recomendaciones Estratégicas</h2>", unsafe_allow_html=True)
    st.markdown("<div></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 10px; color: white;'>
            <h4>🎯 Corto Plazo</h4>
            <ul style='font-size: 0.9rem;'>
                <li>Refuerzo intensivo en materia con mayor caída</li>
                <li>Talleres de nivelación para estudiantes en riesgo</li>
                <li>Simulacros adicionales focalizados</li>
            </ul>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
        <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                    padding: 1.5rem; border-radius: 10px; color: white;'>
            <h4>📅 Mediano Plazo</h4>
            <ul style='font-size: 0.9rem;'>
                <li>Grupos de estudio por niveles</li>
                <li>Seguimiento personalizado semanal</li>
                <li>Banco de ejercicios por materia</li>
            </ul>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
        <div style='background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); 
                    padding: 1.5rem; border-radius: 10px; color: #333;'>
            <h4>🎓 Largo Plazo</h4>
            <ul style='font-size: 0.9rem;'>
                <li>Programa de tutorías entre pares</li>
                <li>Preparación psicológica pre-examen</li>
                <li>Sistema de recompensas por mejora</li>
            </ul>
        </div>
        """,
            unsafe_allow_html=True,
        )
