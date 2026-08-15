import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..core_utils import get_db_connection
from ..data import get_or_generate_insights, get_regular_presented_df


def render(simulacros, materias):
    if not simulacros:
        st.error("No hay simulacros cargados.")
        return

    st.markdown("<h1 class='header-title'>📊 Dashboard de Análisis de Simulacros PreIcfes</h1>", unsafe_allow_html=True)
    st.markdown("<p class='header-subtitle'>Sistema de Evaluación y Seguimiento Académico</p>", unsafe_allow_html=True)

    promocion_id = st.session_state.get("promocion_activa_id")
    total_estudiantes_promo = None
    if promocion_id:
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM estudiantes WHERE promocion_id = %s;", (promocion_id,))
                    total_estudiantes_promo = cur.fetchone()[0]
            except Exception:
                pass
            finally:
                conn.close()

    estudiantes_con_notas = (
        pd.concat([sim["df"][["ESTUDIANTE"]] for sim in simulacros], ignore_index=True)["ESTUDIANTE"].str.strip().str.upper().nunique()
    )
    total_estudiantes = total_estudiantes_promo if (total_estudiantes_promo and total_estudiantes_promo > 0) else estudiantes_con_notas
    total_registros = sum(len(sim["df"]) for sim in simulacros)
    ultimo = simulacros[-1]
    insights_ultimo = get_or_generate_insights(ultimo)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
        <div class='metric-card'>
            <h4 style='color:#1565c0; margin:0 0 0.5rem;'>📝 Simulacros</h4>
            <div style='font-size:2.6rem; font-weight:800; color:#1a73e8; line-height:1;'>{len(simulacros)}</div>
            <p style='margin:0.5rem 0 0; color:#6b7a99; font-size:0.85rem;'>Histórico listo</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
        <div class='metric-card'>
            <h4 style='color:#1565c0; margin:0 0 0.5rem;'>👥 Estudiantes Únicos</h4>
            <div style='font-size:2.6rem; font-weight:800; color:#1a73e8; line-height:1;'>{total_estudiantes}</div>
            <p style='margin:0.5rem 0 0; color:#6b7a99; font-size:0.85rem;'>Registro oficial</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
        <div class='metric-card'>
            <h4 style='color:#1565c0; margin:0 0 0.5rem;'>📚 Áreas</h4>
            <div style='font-size:2.6rem; font-weight:800; color:#1a73e8; line-height:1;'>{len(materias)}</div>
            <p style='margin:0.5rem 0 0; color:#6b7a99; font-size:0.85rem;'>Materias ICFES</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""
        <div class='metric-card'>
            <h4 style='color:#1565c0; margin:0 0 0.5rem;'>📋 Registros</h4>
            <div style='font-size:2.6rem; font-weight:800; color:#1a73e8; line-height:1;'>{total_registros}</div>
            <p style='margin:0.5rem 0 0; color:#6b7a99; font-size:0.85rem;'>Filas consolidadas</p>
        </div>
        """,
            unsafe_allow_html=True,
        )


    st.markdown("<h2 class='section-header'>📊 Análisis Comparativo de Simulacros</h2>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    # Evolución de promedios (Aplicando protocolo: Excluye inclusión y no presentados)
    promedios_data = pd.DataFrame(
        {
            "Simulacro": [sim["nombre"] for sim in simulacros],
            "Promedio": [get_regular_presented_df(sim["df"])["PROMEDIO PONDERADO"].mean() for sim in simulacros],
            "Desv. Est.": [get_regular_presented_df(sim["df"])["PROMEDIO PONDERADO"].std() for sim in simulacros],
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
                text=[f"{p:.1f}" if pd.notna(p) else "-" for p in promedios_data["Promedio"]],
                textposition="outside",
                name="Promedio",
            )
        )
        fig.update_layout(height=420, showlegend=False, yaxis_title="Puntaje Promedio", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

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
            st.dataframe(cambios_df, use_container_width=True, hide_index=True)

    # Distribución de rendimiento (Excluyendo inclusión y ausentes)
    categorias = ["Alto (≥300)", "Medio (250-299)", "Bajo (<250)"]

    def distribucion(df):
        reg = get_regular_presented_df(df)
        return [
            len(reg[reg["PROMEDIO PONDERADO"] >= 300]),
            len(reg[(reg["PROMEDIO PONDERADO"] >= 250) & (reg["PROMEDIO PONDERADO"] < 300)]),
            len(reg[reg["PROMEDIO PONDERADO"] < 250]),
        ]

    with col_b:
        st.markdown("### 📊 Distribución de Rendimiento por Simulacro")
        fig_dist = go.Figure()
        for sim in simulacros:
            fig_dist.add_trace(go.Bar(name=sim["nombre"], x=categorias, y=distribucion(sim["df"])))
        fig_dist.update_layout(barmode="group", height=420, yaxis_title="Número de estudiantes", template="plotly_white")
        st.plotly_chart(fig_dist, use_container_width=True)

        st.markdown("#### 📋 Resumen de Distribución")
        dist_df = pd.DataFrame(
            {
                "Nivel": categorias,
                **{sim["nombre"]: distribucion(sim["df"]) for sim in simulacros},
            }
        )
        st.dataframe(dist_df, use_container_width=True, hide_index=True)


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
            reg = get_regular_presented_df(sim["df"])
            promedios = [reg[mat].mean() for mat in materias]
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
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 📊 Tabla Comparativa de Materias")
    comp_materias_df = pd.DataFrame({"Materia": materias})
    for sim in simulacros:
        reg = get_regular_presented_df(sim["df"])
        comp_materias_df[sim["nombre"]] = [reg[mat].mean() for mat in materias]

    sim_cols = [c for c in comp_materias_df.columns if c != "Materia"]
    comp_materias_df["Mejor"] = comp_materias_df[sim_cols].max(axis=1)
    comp_materias_df["Menor"] = comp_materias_df[sim_cols].min(axis=1)
    comp_materias_df["Rango"] = comp_materias_df["Mejor"] - comp_materias_df["Menor"]
    comp_materias_df = comp_materias_df.round(2)

    columnas_numericas = comp_materias_df.select_dtypes(include=["float64", "int64"]).columns
    formatters = {col: (lambda x: f"{x:.2f}" if (pd.notna(x) and x is not None) else "-") for col in columnas_numericas}
    styler = comp_materias_df.style.format(formatters, na_rep="-")
    if sim_cols and not comp_materias_df[sim_cols].dropna(how="all").empty:
        styler = styler.background_gradient(subset=sim_cols, cmap="RdYlGn", vmin=40, vmax=90)
    st.dataframe(
        styler,
        use_container_width=True,
        hide_index=True,
    )


    st.markdown("<h2 class='section-header'>🔍 Hallazgos Principales y Recomendaciones</h2>", unsafe_allow_html=True)
    promedios_curr = [ultimo["df"][mat].mean() for mat in materias]
    cambio_general = (np.mean(promedios_curr) - np.mean(promedios_curr[:-1])) if len(promedios_curr) > 1 else 0
    variabilidades = {mat: ultimo["df"][mat].std() for mat in materias}
    mat_variable = max(variabilidades, key=variabilidades.get)
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
            "<div class='rec-card rec-card-short'>"
            "<h4>🎯 Corto Plazo</h4>"
            "<ul>" + "".join([f"<li>{rec}</li>" for rec in bloque[:3]]) + "</ul>"
            "</div>",
            unsafe_allow_html=True,
        )
    with cols[1]:
        bloque = mediano or ["Consolida rutinas semanales con énfasis en rango medio.", "Club de estudio guiado por materia.", "Monitoreo quincenal con rúbricas."]
        st.markdown(
            "<div class='rec-card rec-card-medium'>"
            "<h4>📅 Mediano Plazo</h4>"
            "<ul>" + "".join([f"<li>{rec}</li>" for rec in bloque[:3]]) + "</ul>"
            "</div>",
            unsafe_allow_html=True,
        )
    with cols[2]:
        bloque = largo or ["Programa de mentorías cruzadas.", "Plan trimestral de repaso por objetivos ICFES.", "Simulacros completos con retroalimentación grupal."]
        st.markdown(
            "<div class='rec-card rec-card-long'>"
            "<h4>🎓 Largo Plazo</h4>"
            "<ul>" + "".join([f"<li>{rec}</li>" for rec in bloque[:3]]) + "</ul>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.caption(f"Generado por: {insights.get('modelo', 'N/D')} el {insights.get('generado_en', '')}")
