import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from simulacros_ags.data import get_or_generate_insights


def render(simulacros, materias):
    if not simulacros:
        st.error("No hay simulacros cargados.")
        return

    st.markdown("<h1 class='header-title'> Dashboard de Análisis de Simulacros PreIcfes</h1>", unsafe_allow_html=True)
    st.markdown("<p class='header-subtitle'>Sistema Integral de Evaluación y Seguimiento - Grado 11</p>", unsafe_allow_html=True)

    total_estudiantes = (
        pd.concat([sim["df"][["ESTUDIANTE"]] for sim in simulacros], ignore_index=True)["ESTUDIANTE"].str.strip().str.upper().nunique()
    )
    total_registros = sum(len(sim["df"]) for sim in simulacros)
    ultimo = simulacros[-1]
    insights_ultimo = get_or_generate_insights(ultimo)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;'>
            <h4>📝 Simulacros</h4>
            <h2 style='font-size: 3rem; margin: 0;'>{len(simulacros)}</h2>
            <p style='opacity: 0.9;'>Histórico listo</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #00c6ff 0%, #0072ff 100%); color: white;'>
            <h4>👥 Estudiantes únicos</h4>
            <h2 style='font-size: 3rem; margin: 0;'>{total_estudiantes}</h2>
            <p style='opacity: 0.9;'>Participantes</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white;'>
            <h4>📚 Áreas</h4>
            <h2 style='font-size: 3rem; margin: 0;'>{len(materias)}</h2>
            <p style='opacity: 0.9;'>Materias ICFES</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); color: white;'>
            <h4>📋 Registros</h4>
            <h2 style='font-size: 3rem; margin: 0;'>{total_registros}</h2>
            <p style='opacity: 0.9;'>Filas consolidadas</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📊 Análisis Comparativo de Simulacros</h2>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    # Evolución de promedios
    promedios_data = pd.DataFrame(
        {
            "Simulacro": [sim["nombre"] for sim in simulacros],
            "Promedio": [sim["df"]["PROMEDIO PONDERADO"].mean() for sim in simulacros],
            "Desv. Est.": [sim["df"]["PROMEDIO PONDERADO"].std() for sim in simulacros],
        }
    )

    with col_a:
        st.markdown("### 📈 Evolución de Promedios")
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=promedios_data["Simulacro"],
                y=promedios_data["Promedio"],
                marker_color=["#27ae60", "#f39c12", "#e74c3c", "#667eea", "#9b59b6"] * 5,
                text=[f"{p:.1f}" for p in promedios_data["Promedio"]],
                textposition="outside",
                name="Promedio",
            )
        )
        fig.update_layout(height=420, showlegend=False, yaxis_title="Puntaje Promedio", template="plotly_white")
        st.plotly_chart(fig, width="stretch")

        if len(promedios_data) > 1:
            cambios = []
            for idx in range(1, len(promedios_data)):
                actual = promedios_data.iloc[idx]
                anterior = promedios_data.iloc[idx - 1]
                cambio = actual["Promedio"] - anterior["Promedio"]
                pct = (cambio / anterior["Promedio"] * 100) if anterior["Promedio"] else 0
                cambios.append({"De": anterior["Simulacro"], "A": actual["Simulacro"], "Cambio": cambio, "%": pct})
            cambios_df = pd.DataFrame(cambios).round(2)
            st.markdown("#### 📉 Variaciones Detectadas")
            st.dataframe(cambios_df, width="stretch", hide_index=True)

    # Distribución de rendimiento
    categorias = ["Alto (≥300)", "Medio (250-299)", "Bajo (<250)"]

    def distribucion(df):
        return [
            len(df[df["PROMEDIO PONDERADO"] >= 300]),
            len(df[(df["PROMEDIO PONDERADO"] >= 250) & (df["PROMEDIO PONDERADO"] < 300)]),
            len(df[df["PROMEDIO PONDERADO"] < 250]),
        ]

    with col_b:
        st.markdown("### 📊 Distribución de Rendimiento por Simulacro")
        fig_dist = go.Figure()
        for sim in simulacros:
            fig_dist.add_trace(go.Bar(name=sim["nombre"], x=categorias, y=distribucion(sim["df"])))
        fig_dist.update_layout(barmode="group", height=420, yaxis_title="Número de estudiantes", template="plotly_white")
        st.plotly_chart(fig_dist, width="stretch")

        st.markdown("#### 📋 Resumen de Distribución")
        dist_df = pd.DataFrame(
            {
                "Nivel": categorias,
                **{sim["nombre"]: distribucion(sim["df"]) for sim in simulacros},
            }
        )
        st.dataframe(dist_df, width="stretch", hide_index=True)

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📚 Desempeño por materia</h2>", unsafe_allow_html=True)
    default_sel = [sim["nombre"] for sim in simulacros[-3:]]
    seleccionados = st.multiselect(
        "Simulacros a comparar",
        options=[sim["nombre"] for sim in simulacros],
        default=default_sel,
    )
    if seleccionados:
        fig = go.Figure()
        for sim in simulacros:
            if sim["nombre"] not in seleccionados:
                continue
            promedios = [sim["df"][mat].mean() for mat in materias]
            fig.add_trace(
                go.Scatterpolar(
                    r=promedios,
                    theta=materias,
                    fill="toself",
                    name=sim["nombre"],
                    opacity=0.7,
                )
            )
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, height=500)
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### 📊 Tabla Comparativa de Materias")
    comp_materias_df = pd.DataFrame({"Materia": materias})
    for sim in simulacros:
        comp_materias_df[sim["nombre"]] = [sim["df"][mat].mean() for mat in materias]
    comp_materias_df["Mejor"] = comp_materias_df.drop(columns=["Materia"]).max(axis=1)
    comp_materias_df["Menor"] = comp_materias_df.drop(columns=["Materia"]).min(axis=1)
    comp_materias_df["Rango"] = comp_materias_df["Mejor"] - comp_materias_df["Menor"]
    comp_materias_df = comp_materias_df.round(2)
    columnas_numericas = comp_materias_df.select_dtypes(include=["float64", "int64"]).columns
    columnas_simulacros = [c for c in comp_materias_df.columns if c not in ["Materia", "Mejor", "Menor", "Rango"]]
    st.dataframe(
        comp_materias_df.style.format({col: "{:.2f}" for col in columnas_numericas}).background_gradient(
            subset=columnas_simulacros,
            cmap="RdYlGn",
            vmin=40,
            vmax=90,
        ),
        width="stretch",
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("<h2 class='section-header'>🔍 Hallazgos Principales y Recomendaciones</h2>", unsafe_allow_html=True)
    # Recalcular referencias usando último simulacro y promedios dinámicos
    promedios_curr = [ultimo["df"][mat].mean() for mat in materias]
    cambio_general = (np.mean(promedios_curr) - np.mean(promedios_curr[:-1])) if len(promedios_curr) > 1 else 0
    variabilidades = {mat: ultimo["df"][mat].std() for mat in materias}
    mat_variable = max(variabilidades, key=variabilidades.get)
    # Comparar último contra penúltimo si existe
    if len(simulacros) > 1:
        penultimo = simulacros[-2]
        promedios_penultimo = [penultimo["df"][mat].mean() for mat in materias]
        cambios_materias = {mat: c - p for mat, c, p in zip(materias, promedios_curr, promedios_penultimo)}
        nombre_anterior = penultimo["nombre"]
    else:
        cambios_materias = {mat: 0 for mat in materias}
        nombre_anterior = "referencia previa"
    mat_mayor_caida = min(cambios_materias, key=cambios_materias.get)
    mat_mayor_mejora = max(cambios_materias, key=cambios_materias.get)
    mejor_materia = max(materias, key=lambda m: promedios_curr[materias.index(m)])
    peor_materia = min(materias, key=lambda m: promedios_curr[materias.index(m)])
    insights_alertas = insights_ultimo.get("alertas") or []
    insights_fort = insights_ultimo.get("fortalezas") or []

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
        <div class='alert-warning'>
            <h4>⚠️ Áreas de Atención Prioritaria</h4>
            <ul>
                {''.join([f'<li>{item}</li>' for item in insights_alertas])}
                <li><strong>Variación general:</strong> {cambio_general:+.1f} puntos vs {nombre_anterior}</li>
                <li><strong>Materia con mayor caída:</strong> {mat_mayor_caida} ({cambios_materias.get(mat_mayor_caida, 0):+.1f} pts)</li>
                <li><strong>Materia más variable:</strong> {mat_variable} (σ = {variabilidades[mat_variable]:.1f})</li>
                <li><strong>Puntaje promedio más bajo:</strong> {peor_materia} ({min(promedios_curr):.1f} pts)</li>
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
                {''.join([f'<li>{item}</li>' for item in insights_fort])}
                <li><strong>Mejor materia:</strong> {mejor_materia} ({max(promedios_curr):.1f} pts)</li>
                <li><strong>Materia con mayor mejora:</strong> {mat_mayor_mejora} ({cambios_materias.get(mat_mayor_mejora, 0):+.1f} pts)</li>
                <li><strong>Estudiantes ≥350:</strong> {len(ultimo["df"][ultimo["df"]["PROMEDIO PONDERADO"] >= 350])}</li>
                <li><strong>Potencial de mejora:</strong> {len(ultimo["df"][(ultimo["df"]["PROMEDIO PONDERADO"] >= 250) & (ultimo["df"]["PROMEDIO PONDERADO"] < 300)])} en rango medio</li>
            </ul>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.caption("Hallazgos generados automáticamente (IA + análisis de datos).")

    st.markdown("<h2 class='section-header'>💡 Recomendaciones generadas por IA</h2>", unsafe_allow_html=True)
    opciones_insights = [sim["nombre"] for sim in simulacros]
    elegido = st.selectbox("Selecciona el simulacro para ver recomendaciones", opciones_insights, index=len(opciones_insights) - 1)
    sim_obj = next(sim for sim in simulacros if sim["nombre"] == elegido)
    insights = insights_ultimo if sim_obj["id"] == ultimo["id"] else get_or_generate_insights(sim_obj)

    st.info(insights.get("resumen", "Resumen no disponible"))
    cols = st.columns(3)
    recs = insights.get("recomendaciones") or {}
    corto = recs.get("corto") or recs if isinstance(recs, list) else []
    mediano = recs.get("mediano") if isinstance(recs, dict) else []
    largo = recs.get("largo") if isinstance(recs, dict) else []
    with cols[0]:
        bloque = corto or ["Refuerzo focalizado en la materia con mayor caída.", "Sesiones cortas de práctica diagnóstica.", "Feedback semanal a estudiantes en riesgo."]
        st.markdown(
            """
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.2rem; border-radius: 12px; color: white;'>
            <h4 style='margin-top: 0;'>🎯 Corto Plazo</h4>
            <ul style='margin-bottom:0; padding-left:1.2rem;'>""" +
            "".join([f"<li>{rec}</li>" for rec in bloque[:3]]) +
            """</ul>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with cols[1]:
        bloque = mediano or ["Consolida rutinas semanales con énfasis en rango medio.", "Club de estudio guiado por materia.", "Monitoreo quincenal con rúbricas."]
        st.markdown(
            """
        <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.2rem; border-radius: 12px; color: white;'>
            <h4 style='margin-top: 0;'>📅 Mediano Plazo</h4>
            <ul style='margin-bottom:0; padding-left:1.2rem;'>""" +
            "".join([f"<li>{rec}</li>" for rec in bloque[:3]]) +
            """</ul>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with cols[2]:
        bloque = largo or ["Programa de mentorías cruzadas.", "Plan trimestral de repaso por objetivos ICFES.", "Simulacros completos con retroalimentación grupal."]
        st.markdown(
            """
        <div style='background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); padding: 1.2rem; border-radius: 12px; color: #333;'>
            <h4 style='margin-top: 0;'>🎓 Largo Plazo</h4>
            <ul style='margin-bottom:0; padding-left:1.2rem;'>""" +
            "".join([f"<li>{rec}</li>" for rec in bloque[:3]]) +
            """</ul>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.caption(f"Generado por: {insights.get('modelo', 'N/D')} el {insights.get('generado_en', '')}")
