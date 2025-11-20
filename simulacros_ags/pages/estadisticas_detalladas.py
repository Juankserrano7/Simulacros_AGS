import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def render(hp1, hp2, prep, materias, simulacro_seleccionado, simulacros_map):
    st.markdown("<h1 class='header-title'> Estadísticas Detalladas</h1>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["📊 Correlaciones", "📈 Análisis por Grado", "🎯 Top Performers"])

    with tab1:
        st.markdown("### 🔗 Matriz de Correlación entre Materias")
        col1, col2, col3 = st.columns(3)
        for idx, (nombre, datos) in enumerate([("HP1", hp1), ("HP2", hp2), ("Prep", prep)]):
            with [col1, col2, col3][idx]:
                st.markdown(f"#### {nombre}")
                correlacion = datos[materias].corr()
                fig = px.imshow(correlacion, text_auto=".2f", color_continuous_scale="RdBu_r", aspect="auto", zmin=-1, zmax=1)
                fig.update_layout(height=400)
                st.plotly_chart(fig, width="stretch")
        st.markdown("---")
        st.info(
            """
        **Correlación alta (>0.7):** Las materias están fuertemente relacionadas. 
        Un buen desempeño en una suele indicar buen desempeño en la otra.

        **Correlación Media (0.4-0.7):** Relación moderada entre las materias.

        **Correlación baja (<0.4):** Las materias son relativamente independientes.
        """
        )

    with tab2:
        st.markdown("### 📚 Análisis Comparativo por Grado")
        datos_grado = simulacros_map[simulacro_seleccionado]
        if "GRADO" in datos_grado.columns:
            grados_disponibles = [str(g) for g in datos_grado["GRADO"].dropna().unique()]
            fig = go.Figure()
            for grado in sorted(grados_disponibles):
                datos_g = datos_grado[datos_grado["GRADO"].astype(str) == grado]
                promedios_g = [datos_g[mat].mean() for mat in materias]
                fig.add_trace(
                    go.Bar(name=f"Grado {grado}", x=materias, y=promedios_g, text=[f"{p:.1f}" for p in promedios_g], textposition="outside")
                )
            fig.update_layout(
                title=f"Comparación de Promedios por Grado - {simulacro_seleccionado}",
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

    with tab3:
        st.markdown("### 🏆 Top Performers por Materia")
        datos_top = simulacros_map[simulacro_seleccionado]
        n_top = st.slider("Número de estudiantes a mostrar", 5, 30, 15)
        cols = st.columns(2)
        for idx, materia in enumerate(materias):
            with cols[idx % 2]:
                st.markdown(f"#### {materia}")
                top_materia = datos_top.nlargest(n_top, materia)[["ESTUDIANTE", materia]].reset_index(drop=True)
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
        ranking_general = datos_top.nlargest(30, "PROMEDIO PONDERADO")[["ESTUDIANTE"] + materias + ["PROMEDIO PONDERADO"]].reset_index(drop=True)
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
