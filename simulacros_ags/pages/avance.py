from functools import reduce
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..data import load_icfes_real_data


def render(simulacros, materias, simulacro_seleccionado: str = None):
    if len(simulacros) < 1:
        st.warning("⚠️ No hay simulacros cargados en esta promoción.")
        return

    promocion_id = st.session_state.get("promocion_activa_id")
    df_icfes_real = load_icfes_real_data(promocion_id)
    has_icfes_real = not df_icfes_real.empty

    title_text = "📈 Análisis de Avance hacia el ICFES Real" if has_icfes_real else "📈 Análisis de Avance de Simulacros"
    st.markdown(f"<h1 class='header-title'>{title_text}</h1>", unsafe_allow_html=True)

    frames = []
    seen_names = set()
    for sim in simulacros:
        sim_name = sim["nombre"]
        if sim_name in seen_names or sim.get("id") == "icfes_real" or sim_name == "🎯 ICFES Real":
            continue
        seen_names.add(sim_name)
        temp = sim["df"][["ESTUDIANTE", "PROMEDIO PONDERADO"]].copy()
        temp["ESTUDIANTE"] = temp["ESTUDIANTE"].str.strip().str.upper()
        temp = temp.rename(columns={"PROMEDIO PONDERADO": sim_name})
        frames.append(temp)

    if has_icfes_real and "🎯 ICFES Real" not in seen_names and "ESTUDIANTE" in df_icfes_real.columns:
        temp_real = df_icfes_real[["ESTUDIANTE", "PROMEDIO PONDERADO"]].copy()
        temp_real["ESTUDIANTE"] = temp_real["ESTUDIANTE"].str.strip().str.upper()
        temp_real = temp_real.rename(columns={"PROMEDIO PONDERADO": "🎯 ICFES Real"})
        frames.append(temp_real)
        seen_names.add("🎯 ICFES Real")

    progresion = reduce(lambda left, right: left.merge(right, on="ESTUDIANTE", how="outer"), frames)
    eval_cols = [col for col in progresion.columns if col != "ESTUDIANTE"]

    # --- CASO: Solo 1 evaluación registrada ---
    if len(eval_cols) < 2:
        st.warning(
            f"⚠️ **Atención: Solo hay 1 evaluación registrada en esta promoción ({eval_cols[0]}).**\n\n"
            "El análisis de avance compara el rendimiento entre evaluaciones consecutivas (ej: Simulacro anterior vs. Simulacro activo). "
            "Para generar la gráfica de progreso e indicadores de cambio, se requieren al menos 2 simulacros o contar con resultados de ICFES Real."
        )
        st.markdown(f"**Estudiantes registrados en '{eval_cols[0]}':** {len(progresion)}")
        col_s1, col_s2, col_s3 = st.columns(3)
        prom_val = progresion[eval_cols[0]].mean()
        max_val = progresion[eval_cols[0]].max()
        min_val = progresion[eval_cols[0]].min()
        with col_s1:
            st.metric("Promedio General", f"{prom_val:.2f}" if pd.notna(prom_val) else "-")
        with col_s2:
            st.metric("Puntaje Máximo", f"{max_val:.2f}" if pd.notna(max_val) else "-")
        with col_s3:
            st.metric("Puntaje Mínimo", f"{min_val:.2f}" if pd.notna(min_val) else "-")

        st.markdown("---")
        st.markdown(f"### 📋 Listado de Puntajes en {eval_cols[0]}")
        tabla_unica = progresion.sort_values(eval_cols[0], ascending=False)
        st.dataframe(tabla_unica, use_container_width=True, height=600)
        return

    # --- Determinar las evaluaciones a comparar (anterior vs seleccionado) ---
    idx = None
    if simulacro_seleccionado and simulacro_seleccionado in eval_cols:
        idx = eval_cols.index(simulacro_seleccionado)

    if idx is None:
        idx = len(eval_cols) - 1

    if idx == 0:
        idx_prev = 0
        idx_curr = 1
    else:
        idx_prev = idx - 1
        idx_curr = idx

    col_prev = eval_cols[idx_prev]
    col_curr = eval_cols[idx_curr]

    progresion["CAMBIO_PERIODO"] = progresion[col_curr] - progresion[col_prev]
    progresion["CAMBIO_TOTAL"] = progresion[eval_cols[-1]] - progresion[eval_cols[0]]

    st.markdown(f"**Estudiantes monitoreados:** {len(progresion)}")
    st.info(f"📍 **Comparativo activo:** `{col_prev}` ➔ `{col_curr}`")

    col1, col2, col3 = st.columns(3)
    mejoraron = (progresion["CAMBIO_PERIODO"] > 0).sum()
    empeoraron = (progresion["CAMBIO_PERIODO"] < 0).sum()
    cambio_prom = progresion["CAMBIO_PERIODO"].mean()

    with col1:
        st.markdown(
            f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); color: white;'>
            <h4>📈 Subieron</h4>
            <h2 style='margin:0;'>{mejoraron}</h2>
            <p style='opacity:0.9;'>{col_prev} → {col_curr}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); color: white;'>
            <h4>📉 Bajaron</h4>
            <h2 style='margin:0;'>{empeoraron}</h2>
            <p style='opacity:0.9;'>{col_prev} → {col_curr}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #00c6ff 0%, #0072ff 100%); color: white;'>
            <h4>📊 Cambio promedio</h4>
            <h2 style='margin:0;'>{cambio_prom:+.2f}</h2>
            <p style='opacity:0.9;'>Puntos ({col_prev} → {col_curr})</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown(f"<h2 class='section-header'>📊 Avance por estudiante ({col_prev} ➔ {col_curr})</h2>", unsafe_allow_html=True)

    progresion_valid = progresion.dropna(subset=["CAMBIO_PERIODO"]).copy()
    if progresion_valid.empty:
        st.info("No hay datos suficientes para generar la gráfica comparativa de avance.")
    else:
        progresion_sorted = progresion_valid.sort_values("CAMBIO_PERIODO")
        colores = ["#27ae60" if c > 0 else "#e74c3c" for c in progresion_sorted["CAMBIO_PERIODO"]]
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                y=progresion_sorted["ESTUDIANTE"].str.split().str[:2].str.join(" "),
                x=progresion_sorted["CAMBIO_PERIODO"],
                orientation="h",
                marker_color=colores,
                text=[f"{c:+.1f}" if pd.notna(c) else "-" for c in progresion_sorted["CAMBIO_PERIODO"]],
                textposition="outside",
            )
        )
        fig.update_layout(
            title=f"Diferencia de Rendimiento: {col_prev} ➔ {col_curr}",
            xaxis_title="Diferencia en Puntos (Puntaje Ponderado)",
            yaxis_title="Estudiante",
            height=max(500, len(progresion_sorted) * 22),
            template="plotly_white",
        )
        fig.add_vline(x=0, line_dash="dash", line_color="black")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<h2 class='section-header'>📈 Evolución Individual a lo largo de las Evaluaciones</h2>", unsafe_allow_html=True)
    estudiantes_mostrar = st.multiselect(
        "Seleccionar estudiantes para comparar la evolución histórica",
        progresion["ESTUDIANTE"].tolist(),
        default=progresion.nlargest(5, col_curr)["ESTUDIANTE"].tolist()[:5],
    )
    if estudiantes_mostrar:
        fig_ind = go.Figure()
        for estudiante in estudiantes_mostrar:
            sub_est = progresion[progresion["ESTUDIANTE"] == estudiante]
            if not sub_est.empty:
                datos_est = sub_est.iloc[0]
                fig_ind.add_trace(
                    go.Scatter(
                        x=eval_cols,
                        y=[datos_est[col] for col in eval_cols],
                        mode="lines+markers+text",
                        text=[f"{datos_est[col]:.0f}" if pd.notna(datos_est[col]) else "" for col in eval_cols],
                        textposition="top center",
                        name=estudiante.split()[0],
                        line=dict(width=3),
                        marker=dict(size=10),
                    )
                )
        fig_ind.update_layout(
            title="Evolución del Puntaje por Estudiante",
            xaxis_title="Evaluación / Prueba",
            yaxis_title="Puntaje Ponderado / Global",
            height=500,
            template="plotly_white",
            hovermode="x unified",
        )
        st.plotly_chart(fig_ind, use_container_width=True)

    st.markdown("<h2 class='section-header'>📋 Tabla Resumen de Avance</h2>", unsafe_allow_html=True)
    col_label_delta = f"Δ ({col_prev} → {col_curr})"
    tabla_progresion = progresion[["ESTUDIANTE"] + eval_cols + ["CAMBIO_PERIODO", "CAMBIO_TOTAL"]].copy()
    tabla_progresion = tabla_progresion.rename(columns={"CAMBIO_PERIODO": col_label_delta, "CAMBIO_TOTAL": "Δ Total (Global)"})
    tabla_progresion = tabla_progresion.sort_values(col_label_delta, ascending=False)
    
    columnas_num = tabla_progresion.select_dtypes(include=["float64", "int64"]).columns
    subset_grad = [c for c in [col_label_delta, "Δ Total (Global)"] if c in tabla_progresion.columns]

    st.dataframe(
        tabla_progresion.style.format(
            {col: (lambda x: f"{x:+.2f}" if (pd.notna(x) and ("Δ" in col)) else (f"{x:.2f}" if pd.notna(x) else "-")) for col in columnas_num},
            na_rep="No presentó"
        ).background_gradient(
            subset=subset_grad, cmap="RdYlGn", vmin=-40, vmax=40
        ),
        use_container_width=True,
        height=650,
    )
