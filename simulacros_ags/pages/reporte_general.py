import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ..data import load_icfes_real_data


def render(datos_actual, simulacro_seleccionado, materias):
    st.markdown(f"<h1 class='header-title'> Reporte General - {simulacro_seleccionado}</h1>", unsafe_allow_html=True)

    promocion_id = st.session_state.get("promocion_activa_id")
    df_icfes_real = load_icfes_real_data(promocion_id)
    if not df_icfes_real.empty and "es_inclusion" in df_icfes_real.columns:
        df_icfes_regular = df_icfes_real[df_icfes_real["es_inclusion"] == False]
    else:
        df_icfes_regular = df_icfes_real

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📚 Estudiantes", len(datos_actual))
    with col2:
        st.metric("📊 Promedio Simulacro", f"{datos_actual['PROMEDIO PONDERADO'].mean():.1f}")
    with col3:
        if not df_icfes_regular.empty:
            st.metric("🎯 Promedio ICFES Real", f"{df_icfes_regular['PROMEDIO PONDERADO'].mean():.1f}")
        else:
            st.metric("🏆 Máximo Simulacro", f"{datos_actual['PROMEDIO PONDERADO'].max():.1f}")
    with col4:
        st.metric("📉 Mínimo Simulacro", f"{datos_actual['PROMEDIO PONDERADO'].min():.1f}")
    with col5:
        st.metric("📈 Desv. Est. Simulacro", f"{datos_actual['PROMEDIO PONDERADO'].std():.1f}")

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
        st.dataframe(medidas_df, use_container_width=True, hide_index=True)

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
        st.dataframe(rangos_df, use_container_width=True, hide_index=True)

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
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📚 Análisis Detallado por Materia (Simulacro vs ICFES Real)</h2>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        promedios_materias = [datos_actual[mat].mean() for mat in materias]
        fig = go.Figure(
            data=[
                go.Bar(
                    name=simulacro_seleccionado,
                    x=materias,
                    y=promedios_materias,
                    marker_color="#3498db",
                    text=[f"{p:.1f}" for p in promedios_materias],
                    textposition="outside",
                )
            ]
        )
        if not df_icfes_regular.empty:
            promedios_real = [df_icfes_regular[mat].mean() for mat in materias]
            fig.add_trace(
                go.Bar(
                    name="🎯 ICFES Real",
                    x=materias,
                    y=promedios_real,
                    marker_color="#f1c40f",
                    text=[f"{p:.1f}" for p in promedios_real],
                    textposition="outside",
                )
            )

        fig.add_hline(y=np.mean(promedios_materias), line_dash="dash", line_color="red", annotation_text="Promedio Simulacro")
        fig.update_layout(
            barmode="group",
            title=f"Rendimiento por Área - {simulacro_seleccionado} vs ICFES Real",
            xaxis_title="Materia",
            yaxis_title="Puntaje Promedio",
            height=450,
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

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
        fig.update_layout(title="Diferencia vs Promedio General en Simulacro", xaxis_title="Materia", yaxis_title="Puntos sobre/bajo el promedio", height=450, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("### 📋 Tabla Estadísticas Detalladas por Materia (Simulacro vs ICFES Real)")

    stats_dict = {
        "Materia": materias,
        "Prom. Simulacro": [datos_actual[m].mean() for m in materias],
    }
    if not df_icfes_regular.empty:
        stats_dict["🎯 Prom. ICFES Real"] = [df_icfes_regular[m].mean() for m in materias]
        stats_dict["Δ (ICFES - Sim)"] = [df_icfes_regular[m].mean() - datos_actual[m].mean() for m in materias]

    stats_dict.update({
        "Mediana": [datos_actual[m].median() for m in materias],
        "Desv. Est.": [datos_actual[m].std() for m in materias],
        "Mínimo": [datos_actual[m].min() for m in materias],
        "Máximo": [datos_actual[m].max() for m in materias],
        "CV (%)": [(datos_actual[m].std() / datos_actual[m].mean() * 100) for m in materias],
    })
    stats_df = pd.DataFrame(stats_dict).round(2)
    columnas_num = stats_df.select_dtypes(include=["float64", "int64"]).columns
    st.dataframe(
        stats_df.style.format({col: "{:.2f}" for col in columnas_num}).background_gradient(subset=["Prom. Simulacro"] + (["🎯 Prom. ICFES Real"] if "🎯 Prom. ICFES Real" in stats_df.columns else []), cmap="RdYlGn", vmin=40, vmax=90),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("<h2 class='section-header'>🔗 Matriz de Correlación entre Materias</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        correlacion = datos_actual[materias].corr()
        fig = px.imshow(correlacion, text_auto=".2f", color_continuous_scale="RdBu_r", aspect="auto", zmin=-1, zmax=1, labels=dict(color="Correlación"))
        fig.update_layout(height=500, title="Correlación entre Materias")
        st.plotly_chart(fig, use_container_width=True)
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
        corr_values = correlacion.values.copy()
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
