import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from simulacros_ags.data import get_or_generate_insights


def render(simulacros, simulacro_actual, materias):
    datos_actual = simulacro_actual["df"]
    st.markdown(f"<h1 class='header-title'> Estadísticas Detalladas - {simulacro_actual['nombre']}</h1>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["📊 Correlaciones", "📈 Análisis por Grado", "🎯 Top Performers"])

    # --- Correlaciones ---
    with tab1:
        st.markdown("### 🔗 Matriz de Correlación entre Materias")
        # mostrar hasta 3 simulacros en columnas para mantener estética previa
        cols = st.columns(min(3, len(simulacros)))
        mostrar = simulacros[-3:] if len(simulacros) > 3 else simulacros
        for idx, sim in enumerate(mostrar):
            correlacion = sim["df"][materias].corr()
            with cols[idx]:
                st.markdown(f"#### {sim['nombre']}")
                fig = px.imshow(
                    correlacion,
                    text_auto=".2f",
                    color_continuous_scale="RdBu_r",
                    aspect="auto",
                    zmin=-1,
                    zmax=1,
                    labels=dict(color="Correlación"),
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, width="stretch")
        st.markdown("---")
        st.info(
            """
        **Correlación alta (>0.7):** materias fuertemente relacionadas.

        **Correlación media (0.4-0.7):** relación moderada.

        **Correlación baja (<0.4):** independencia relativa.
        """
        )
        # IA: resumen dinámico de correlaciones
        insights = get_or_generate_insights(simulacro_actual)
        st.markdown(
            """
        <div style='background: linear-gradient(135deg, #1f2a44 0%, #2b3a5e 100%); padding: 1.2rem; border-radius: 12px; color: white; margin-top: 1rem;'>
            <h4 style='margin: 0 0 0.5rem 0;'>🤖 Análisis automático (IA)</h4>
            <p style='margin: 0 0 0.5rem 0; opacity: 0.9;'>{resumen}</p>
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;'>
                <div>
                    <h5 style='margin: 0 0 0.4rem 0;'>Alertas / Prioridades</h5>
                    {alertas}
                </div>
                <div>
                    <h5 style='margin: 0 0 0.4rem 0;'>Fortalezas / Oportunidades</h5>
                    {fortalezas}
                </div>
            </div>
        </div>
        """.format(
                resumen=insights.get("resumen", "Análisis generado automáticamente."),
                alertas="<ul style='margin:0; padding-left:1.2rem;'>" + "".join([f"<li>{i}</li>" for i in insights.get("alertas", [])]) + "</ul>",
                fortalezas="<ul style='margin:0; padding-left:1.2rem;'>" + "".join([f"<li>{i}</li>" for i in insights.get("fortalezas", [])]) + "</ul>",
            ),
            unsafe_allow_html=True,
        )

    # --- Análisis por grado ---
    with tab2:
        st.markdown("### 📚 Análisis Comparativo por Grado")
        datos_grado = datos_actual
        if "GRADO" in datos_grado.columns:
            grados_disponibles = [str(g) for g in datos_grado["GRADO"].dropna().unique()]
            fig = go.Figure()
            for grado in sorted(grados_disponibles):
                datos_g = datos_grado[datos_grado["GRADO"].astype(str) == grado]
                promedios_g = [datos_g[mat].mean() for mat in materias]
                fig.add_trace(
                    go.Bar(
                        name=f"Grado {grado}",
                        x=materias,
                        y=promedios_g,
                        text=[f"{p:.1f}" for p in promedios_g],
                        textposition="outside",
                    )
                )
            fig.update_layout(
                title=f"Comparación de Promedios por Grado - {simulacro_actual['nombre']}",
                xaxis_title="Materia",
                yaxis_title="Puntaje Promedio",
                barmode="group",
                height=500,
                template="plotly_white",
            )
            st.plotly_chart(fig, width="stretch")

            st.markdown("---")
            tabla_grados = []
            for grado in sorted(grados_disponibles):
                datos_g = datos_grado[datos_grado["GRADO"].astype(str) == grado]
                fila = {"Grado": grado}
                for mat in materias:
                    fila[mat] = datos_g[mat].mean()
                fila["Promedio General"] = datos_g["PROMEDIO PONDERADO"].mean()
                tabla_grados.append(fila)
            df_grados = pd.DataFrame(tabla_grados).round(2)
            columnas_num = df_grados.select_dtypes(include=["float64", "int64"]).columns
            st.markdown("#### 📊 Tabla de Promedios por Grado")
            st.dataframe(
                df_grados.style.format({col: "{:.2f}" for col in columnas_num}).background_gradient(
                    cmap="YlGnBu", subset=materias + ["Promedio General"]
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.warning("No hay información de grado disponible en este simulacro.")

    # --- Top performers ---
    with tab3:
        st.markdown("### 🏆 Top Performers por Materia")
        n_top = st.slider("Número de estudiantes a mostrar", 5, 30, 15)
        cols = st.columns(2)
        for idx, materia in enumerate(materias):
            with cols[idx % 2]:
                st.markdown(f"#### {materia}")
                top_materia = datos_actual.nlargest(n_top, materia)[["ESTUDIANTE", materia]].reset_index(drop=True)
                top_materia.index = top_materia.index + 1
                custom_colorscale = [
                    [0.0, "#E74C3C"],
                    [0.4, "#D35400"],
                    [0.68, "#3498DB"],
                    [0.8, "#2ECC71"],
                    [1.0, "#27AE60"],
                ]
                fig = px.bar(
                    top_materia,
                    x=materia,
                    y="ESTUDIANTE",
                    orientation="h",
                    color=materia,
                    color_continuous_scale=custom_colorscale,
                    range_color=(0, 100),
                    text=materia,
                )
                fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
                fig.update_layout(height=400, showlegend=False, yaxis={"categoryorder": "total ascending"}, coloraxis_colorbar=dict(title="Puntaje"))
                st.plotly_chart(fig, width="stretch")

        st.markdown("---")
        st.markdown("### 🏆 Ranking General")
        ranking_general = datos_actual.nlargest(30, "PROMEDIO PONDERADO")[["ESTUDIANTE"] + materias + ["PROMEDIO PONDERADO"]].reset_index(drop=True)
        ranking_general.index = ranking_general.index + 1
        ranking_general = ranking_general.round(2)
        columnas_num = ranking_general.select_dtypes(include=["float64", "int64"]).columns
        st.dataframe(
            ranking_general.style.format({col: "{:.2f}" for col in columnas_num}).background_gradient(
                cmap="RdYlGn",
                subset=materias + ["PROMEDIO PONDERADO"],
                vmin=40,
                vmax=100,
            ),
            width="stretch",
            height=600,
        )
