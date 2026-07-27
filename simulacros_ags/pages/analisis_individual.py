import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..data import load_icfes_real_data


def render(datos_actual, materias):
    if datos_actual.empty or "ESTUDIANTE" not in datos_actual.columns:
        st.warning("No hay datos de simulacro disponibles.")
        return

    st.markdown("<h1 class='header-title'>Análisis Individual de Estudiantes</h1>", unsafe_allow_html=True)

    estudiantes_opt = sorted(datos_actual["ESTUDIANTE"].unique())
    estudiante_seleccionado = st.selectbox("Seleccionar Estudiante", estudiantes_opt)
    datos_estudiante = datos_actual[datos_actual["ESTUDIANTE"] == estudiante_seleccionado].iloc[0]

    promocion_id = st.session_state.get("promocion_activa_id")
    df_icfes_real = load_icfes_real_data(promocion_id)

    icfes_row = None
    has_icfes_real = False
    if not df_icfes_real.empty and "ESTUDIANTE" in df_icfes_real.columns:
        sub_real = df_icfes_real[df_icfes_real["ESTUDIANTE"].str.strip().str.upper() == estudiante_seleccionado.strip().upper()]
        if not sub_real.empty and pd.notna(sub_real.iloc[0].get("PROMEDIO PONDERADO")):
            icfes_row = sub_real.iloc[0]
            has_icfes_real = True

    st.markdown(f"### Resultados de: **{estudiante_seleccionado}**")
    if "GRADO" in datos_estudiante and pd.notna(datos_estudiante["GRADO"]):
        st.markdown(f"**Grado:** {datos_estudiante['GRADO']}")

    val_sim = datos_estudiante.get("PROMEDIO PONDERADO")
    no_presento = pd.isna(val_sim)

    if no_presento:
        st.warning(f"El estudiante **{estudiante_seleccionado}** NO presentó esta evaluación.")

    st.markdown("---")
    if has_icfes_real:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Simulacro Activo", f"{val_sim:.1f}" if pd.notna(val_sim) else "No presentó")
        with col2:
            st.metric("ICFES Real (Global)", f"{icfes_row['PROMEDIO PONDERADO']:.0f}")
        with col3:
            if pd.notna(val_sim):
                valid_proms = datos_actual["PROMEDIO PONDERADO"].dropna()
                percentil = (valid_proms < val_sim).sum() / len(valid_proms) * 100 if len(valid_proms) > 0 else 0
                st.metric("Percentil", f"{percentil:.1f}%")
            else:
                st.metric("Percentil", "N/A")
        with col4:
            if pd.notna(val_sim):
                ranking = datos_actual.dropna(subset=["PROMEDIO PONDERADO"]).sort_values("PROMEDIO PONDERADO", ascending=False).reset_index(drop=True)
                pos_sub = ranking[ranking["ESTUDIANTE"] == estudiante_seleccionado]
                posicion = pos_sub.index[0] + 1 if not pos_sub.empty else "N/A"
                st.metric("Posición", f"{posicion} / {len(ranking)}")
            else:
                st.metric("Posición", "No presentó")
        with col5:
            if pd.notna(val_sim):
                mejor_materia = max(materias, key=lambda m: datos_estudiante[m] if pd.notna(datos_estudiante[m]) else -1)
                st.metric("Mejor Materia", mejor_materia.split()[0])
            else:
                st.metric("Mejor Materia", "N/A")
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Simulacro Activo", f"{val_sim:.1f}" if pd.notna(val_sim) else "No presentó")
        with col2:
            if pd.notna(val_sim):
                valid_proms = datos_actual["PROMEDIO PONDERADO"].dropna()
                percentil = (valid_proms < val_sim).sum() / len(valid_proms) * 100 if len(valid_proms) > 0 else 0
                st.metric("Percentil", f"{percentil:.1f}%")
            else:
                st.metric("Percentil", "N/A")
        with col3:
            if pd.notna(val_sim):
                ranking = datos_actual.dropna(subset=["PROMEDIO PONDERADO"]).sort_values("PROMEDIO PONDERADO", ascending=False).reset_index(drop=True)
                pos_sub = ranking[ranking["ESTUDIANTE"] == estudiante_seleccionado]
                posicion = pos_sub.index[0] + 1 if not pos_sub.empty else "N/A"
                st.metric("Posición", f"{posicion} / {len(ranking)}")
            else:
                st.metric("Posición", "No presentó")
        with col4:
            if pd.notna(val_sim):
                mejor_materia = max(materias, key=lambda m: datos_estudiante[m] if pd.notna(datos_estudiante[m]) else -1)
                st.metric("Mejor Materia", mejor_materia.split()[0])
            else:
                st.metric("Mejor Materia", "N/A")

    st.markdown("---")
    st.markdown("<h2 class='section-header'>Perfil de Competencias</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    valores_estudiante = [datos_estudiante[mat] if pd.notna(datos_estudiante[mat]) else 0 for mat in materias]
    promedios_grupo = [datos_actual[mat].dropna().mean() if not datos_actual[mat].dropna().empty else 0 for mat in materias]
    valores_icfes_real = [icfes_row[mat] if (has_icfes_real and mat in icfes_row and pd.notna(icfes_row[mat])) else None for mat in materias]

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=valores_estudiante, theta=materias, fill="toself", name="Simulacro Activo", line_color="#667eea"))
        if has_icfes_real and any(v is not None for v in valores_icfes_real):
            fig.add_trace(go.Scatterpolar(r=[v if v is not None else 0 for v in valores_icfes_real], theta=materias, fill="toself", name="ICFES Real", line_color="#f1c40f", opacity=0.8))
        fig.add_trace(go.Scatterpolar(r=promedios_grupo, theta=materias, fill="toself", name="Promedio Grupo", line_color="#e74c3c", opacity=0.5))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, height=450, title="Radar de Competencias")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(x=materias, y=valores_estudiante, name="Simulacro", marker_color="#667eea"))
        if has_icfes_real and any(v is not None for v in valores_icfes_real):
            fig_bar.add_trace(go.Bar(x=materias, y=[v if v is not None else 0 for v in valores_icfes_real], name="ICFES Real", marker_color="#f1c40f"))
        fig_bar.add_trace(go.Scatter(x=materias, y=promedios_grupo, mode="markers+lines", name="Prom. Grupo", line=dict(color="#e74c3c", dash="dash"), marker=dict(size=10)))
        fig_bar.update_layout(barmode="group", title="Puntajes por Materia", yaxis_title="Puntaje", height=450, template="plotly_white")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("<h2 class='section-header'>Detalle Comparativo de Puntajes</h2>", unsafe_allow_html=True)
    tabla_dict = {
        "Materia": materias,
        "Simulacro Activo": [datos_estudiante[mat] for mat in materias],
    }
    if has_icfes_real and any(v is not None for v in valores_icfes_real):
        tabla_dict["ICFES Real"] = valores_icfes_real
        tabla_dict["Δ (ICFES - Sim)"] = [r - s if (r is not None and pd.notna(s)) else None for r, s in zip(valores_icfes_real, [datos_estudiante[mat] for mat in materias])]

    tabla_dict["Promedio Grupo"] = promedios_grupo

    detalle_df = pd.DataFrame(tabla_dict).round(2)
    st.dataframe(
        detalle_df.style.format(na_rep="No presentó"),
        use_container_width=True,
    )
