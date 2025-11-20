import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def render(datos_actual, simulacro_seleccionado, materias):
    st.markdown(f"<h1 class='header-title'> Reporte General - {simulacro_seleccionado}</h1>", unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📚 Estudiantes", len(datos_actual))
    with col2:
        st.metric("📊 Promedio", f"{datos_actual['PROMEDIO PONDERADO'].mean():.1f}")
    with col3:
        st.metric("🏆 Máximo", f"{datos_actual['PROMEDIO PONDERADO'].max():.1f}")
    with col4:
        st.metric("📉 Mínimo", f"{datos_actual['PROMEDIO PONDERADO'].min():.1f}")
    with col5:
        st.metric("📈 Desv. Est.", f"{datos_actual['PROMEDIO PONDERADO'].std():.1f}")

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📊 Análisis Estadístico Completo</h2>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        medidas_df = pd.DataFrame(
            {
                "Estadístico": ["Promedio", "Mediana", "Moda", "Rango"],
                "Valor": [
                    datos_actual["PROMEDIO PONDERADO"].mean(),
                    datos_actual["PROMEDIO PONDERADO"].median(),
                    datos_actual["PROMEDIO PONDERADO"].mode().values[0]
                    if len(datos_actual["PROMEDIO PONDERADO"].mode()) > 0
                    else "N/A",
                    datos_actual["PROMEDIO PONDERADO"].max() - datos_actual["PROMEDIO PONDERADO"].min(),
                ],
            }
        )
        medidas_df["Valor"] = medidas_df["Valor"].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)
        st.dataframe(medidas_df, width="stretch", hide_index=True)

        rangos = {
            "Sobresaliente (≥350)": len(datos_actual[datos_actual["PROMEDIO PONDERADO"] >= 350]),
            "Satisfactorio (300-349)": len(
                datos_actual[(datos_actual["PROMEDIO PONDERADO"] >= 300) & (datos_actual["PROMEDIO PONDERADO"] < 350)]
            ),
            "Medio (250-299)": len(
                datos_actual[(datos_actual["PROMEDIO PONDERADO"] >= 250) & (datos_actual["PROMEDIO PONDERADO"] < 300)]
            ),
            "Básico (200-249)": len(
                datos_actual[(datos_actual["PROMEDIO PONDERADO"] >= 200) & (datos_actual["PROMEDIO PONDERADO"] < 250)]
            ),
            "Bajo (<200)": len(datos_actual[datos_actual["PROMEDIO PONDERADO"] < 200]),
        }
        rangos_df = pd.DataFrame(
            {
                "Categoría": list(rangos.keys()),
                "Cantidad": list(rangos.values()),
                "Porcentaje": [f"{(v/len(datos_actual)*100):.1f}%" for v in rangos.values()],
            }
        )
        st.dataframe(rangos_df, width="stretch", hide_index=True)

    with col2:
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=list(rangos.keys()),
                    values=list(rangos.values()),
                    hole=0.4,
                    marker_colors=["#27ae60", "#3498db", "#f39c12", "#e67e22", "#e74c3c"],
                )
            ]
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=600, width=600, title="Distribución del Rendimiento")
        st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📚 Análisis Detallado por Materia</h2>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        promedios_materias = [datos_actual[mat].mean() for mat in materias]
        fig = go.Figure(
            data=[
                go.Bar(
                    x=materias,
                    y=promedios_materias,
                    marker_color=["#3498db", "#2ecc71", "#f39c12", "#e74c3c", "#9b59b6"],
                    text=[f"{p:.1f}" for p in promedios_materias],
                    textposition="outside",
                )
            ]
        )
        fig.add_hline(y=np.mean(promedios_materias), line_dash="dash", line_color="red", annotation_text="Promedio General")
        fig.update_layout(
            title=f"Rendimiento por Área - {simulacro_seleccionado}",
            xaxis_title="Materia",
            yaxis_title="Puntaje Promedio",
            height=450,
            template="plotly_white",
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        promedio_general_materias = np.mean([datos_actual[mat].mean() for mat in materias])
        desempeno_relativo = [(datos_actual[mat].mean() - promedio_general_materias) for mat in materias]
        fig = go.Figure(
            data=[
                go.Bar(
                    x=materias,
                    y=desempeno_relativo,
                    marker_color=["#27ae60" if d > 0 else "#e74c3c" for d in desempeno_relativo],
                    text=[f"{d:+.1f}" for d in desempeno_relativo],
                    textposition="outside",
                )
            ]
        )
        fig.add_hline(y=0, line_color="black")
        fig.update_layout(title="Diferencia vs Promedio General", xaxis_title="Materia", yaxis_title="Puntos sobre/bajo el promedio", height=450, template="plotly_white")
        st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=datos_actual["PROMEDIO PONDERADO"], nbinsx=20, marker_color="#667eea", name="Frecuencia", opacity=0.7))
        fig.add_vline(
            x=datos_actual["PROMEDIO PONDERADO"].mean(),
            line_dash="dash",
            line_color="red",
            annotation_text=f"Promedio: {datos_actual['PROMEDIO PONDERADO'].mean():.1f}",
        )
        fig.add_vline(
            x=datos_actual["PROMEDIO PONDERADO"].median(),
            line_dash="dot",
            line_color="green",
            annotation_text=f"Mediana: {datos_actual['PROMEDIO PONDERADO'].median():.1f}",
        )
        fig.update_layout(height=400, showlegend=False, xaxis_title="Puntaje", yaxis_title="Frecuencia")
        st.plotly_chart(fig, width="stretch")

    with col2:
        fig = go.Figure()
        for i, mat in enumerate(materias):
            fig.add_trace(
                go.Box(
                    y=datos_actual[mat],
                    name=mat.split()[0],
                    marker_color=["#3498db", "#2ecc71", "#f39c12", "#e74c3c", "#9b59b6"][i],
                    boxmean="sd",
                )
            )
        fig.update_layout(height=400, showlegend=True, yaxis_title="Puntaje")
        st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    stats_df = pd.DataFrame(
        {
            "Materia": materias,
            "Promedio": [datos_actual[m].mean() for m in materias],
            "Mediana": [datos_actual[m].median() for m in materias],
            "Desv. Est.": [datos_actual[m].std() for m in materias],
            "Mínimo": [datos_actual[m].min() for m in materias],
            "Q1": [datos_actual[m].quantile(0.25) for m in materias],
            "Q3": [datos_actual[m].quantile(0.75) for m in materias],
            "Máximo": [datos_actual[m].max() for m in materias],
            "Rango": [datos_actual[m].max() - datos_actual[m].min() for m in materias],
            "CV (%)": [(datos_actual[m].std() / datos_actual[m].mean() * 100) for m in materias],
        }
    ).round(2)
    columnas_num = stats_df.select_dtypes(include=["float64", "int64"]).columns
    st.dataframe(
        stats_df.style.format({col: "{:.2f}" for col in columnas_num}).background_gradient(subset=["Promedio", "Mediana"], cmap="RdYlGn", vmin=40, vmax=90),
        width="stretch",
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("<h2 class='section-header'>🔗 Matriz de Correlación entre Materias</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        correlacion = datos_actual[materias].corr()
        fig = px.imshow(correlacion, text_auto=".2f", color_continuous_scale="RdBu_r", aspect="auto", zmin=-1, zmax=1, labels=dict(color="Correlación"))
        fig.update_layout(height=500, title="Correlación entre Materias")
        st.plotly_chart(fig, width="stretch")
    with col2:
        st.info(
            """
        **Correlación Alta (>0.7)**  
        Fuerte relación entre materias

        **Correlación Media (0.4-0.7)**  
        Relación moderada

        **Correlación Baja (<0.4)**  
        Independencia relativa
        """
        )
        corr_values = correlacion.values
        np.fill_diagonal(corr_values, -1)
        max_corr_idx = np.unravel_index(corr_values.argmax(), corr_values.shape)
        max_corr = corr_values[max_corr_idx]
        st.success(
            f"""
        **Mayor Correlación:**  
        {materias[max_corr_idx[0]].split()[0]} ↔️ {materias[max_corr_idx[1]].split()[0]}  
        Coeficiente: {max_corr:.2f}
        """
        )
