import colorsys
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..data import get_regular_presented_df, load_icfes_real_data


def _hex_from_hsl(h: float, s: float = 0.65, l: float = 0.5) -> str:
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def _sim_colors(simulacros) -> dict:
    base = [
        "#27ae60", "#f39c12", "#e74c3c", "#667eea", "#9b59b6",
        "#16a085", "#2980b9", "#d35400", "#2c3e50", "#8e44ad",
        "#c0392b", "#1abc9c", "#34495e",
    ]
    colors = {}
    for idx, sim in enumerate(simulacros):
        if idx < len(base):
            colors[sim["nombre"]] = base[idx]
        else:
            h = (0.61803398875 * idx) % 1.0
            colors[sim["nombre"]] = _hex_from_hsl(h)
    colors["🎯 ICFES Real"] = "#f1c40f"
    return colors


def render(simulacros, materias):
    if len(simulacros) < 1:
        st.warning("Carga al menos un simulacro para comparar.")
        return

    st.markdown("<h1 class='header-title'>🔬 Comparación entre Simulacros</h1>", unsafe_allow_html=True)

    promocion_id = st.session_state.get("promocion_activa_id")
    df_icfes_real = load_icfes_real_data(promocion_id)
    df_icfes_regular = get_regular_presented_df(df_icfes_real)
    has_icfes_real = not df_icfes_regular.empty

    seleccionados = st.multiselect(
        "Elige los simulacros a comparar",
        options=[sim["nombre"] for sim in simulacros],
        default=[sim["nombre"] for sim in simulacros],
    )
    activos = [sim for sim in simulacros if sim["nombre"] in seleccionados]
    if len(activos) < 1:
        st.info("Selecciona al menos un simulacro.")
        return

    st.markdown("<h2 class='section-header'>📊 Comparación de Promedios por Materia</h2>", unsafe_allow_html=True)
    color_map = _sim_colors(simulacros)
    fig = go.Figure()

    for sim in activos:
        if sim.get("id") == "icfes_real" or sim.get("nombre") == "🎯 ICFES Real":
            continue
        df_reg = get_regular_presented_df(sim["df"])
        fig.add_trace(
            go.Bar(
                name=sim["nombre"],
                x=materias,
                y=[df_reg[mat].mean() for mat in materias if mat in df_reg.columns],
                marker=dict(color=color_map.get(sim["nombre"], "#667eea")),
            )
        )

    if has_icfes_real:
        fig.add_trace(
            go.Bar(
                name="🎯 ICFES Real",
                x=materias,
                y=[df_icfes_regular[mat].mean() for mat in materias if mat in df_icfes_regular.columns],
                marker=dict(color="#f1c40f", line=dict(color="#d35400", width=2)),
            )
        )

    fig.update_layout(
        barmode="group",
        height=450,
        title="Promedios por materia (Excluyendo inclusión)",
        xaxis_title="Materia",
        yaxis_title="Puntaje Promedio",
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Resumen de Variaciones Clave ---
    st.markdown("### 🔥 Variaciones clave")
    sims_practica = [s for s in simulacros if s.get("id") != "icfes_real" and s.get("nombre") != "🎯 ICFES Real"]
    promedios_generales = []
    for sim in sims_practica:
        df_reg = get_regular_presented_df(sim["df"])
        promedios_generales.append(df_reg["PROMEDIO PONDERADO"].mean())

    icfes_real_prom = df_icfes_regular["PROMEDIO PONDERADO"].mean() if has_icfes_real else None

    if has_icfes_real:
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.markdown(
                f"""
                <div class='stats-box'>
                    <h4>Último Simulacro</h4>
                    <h2>{promedios_generales[-1]:.2f}</h2>
                    <p>{simulacros[-1]['nombre']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_b:
            st.markdown(
                f"""
                <div class='stats-box' style='background: linear-gradient(135deg, #f1c40f 0%, #f39c12 100%); color: #000;'>
                    <h4>🎯 ICFES Real</h4>
                    <h2>{icfes_real_prom:.2f}</h2>
                    <p>Resultado Oficial Definitivo</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_c:
            delta = icfes_real_prom - promedios_generales[-1] if promedios_generales else 0
            st.markdown(
                f"""
                <div class='stats-box' style='background: linear-gradient(135deg, #00c6ff 0%, #0072ff 100%);'>
                    <h4>Δ ICFES vs Últ. Simulacro</h4>
                    <h2>{delta:+.2f}</h2>
                    <p>Puntos de diferencia</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_d:
            max_prom = max(promedios_generales) if promedios_generales else 0
            mejor_sim = simulacros[promedios_generales.index(max_prom)]["nombre"] if promedios_generales else "-"
            st.markdown(
                f"""
                <div class='stats-box' style='background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);'>
                    <h4>Mejor en Simulacros</h4>
                    <h2>{max_prom:.2f}</h2>
                    <p>{mejor_sim}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown(
                f"""
                <div class='stats-box'>
                    <h4>Último Simulacro</h4>
                    <h2>{promedios_generales[-1]:.2f}</h2>
                    <p>{simulacros[-1]['nombre']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_b:
            delta = (promedios_generales[-1] - promedios_generales[-2]) if len(promedios_generales) > 1 else 0
            st.markdown(
                f"""
                <div class='stats-box' style='background: linear-gradient(135deg, #00c6ff 0%, #0072ff 100%);'>
                    <h4>Δ Último vs Previo</h4>
                    <h2>{delta:+.2f}</h2>
                    <p>Puntos de diferencia</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_c:
            max_prom = max(promedios_generales) if promedios_generales else 0
            mejor_sim = simulacros[promedios_generales.index(max_prom)]["nombre"] if promedios_generales else "-"
            st.markdown(
                f"""
                <div class='stats-box' style='background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);'>
                    <h4>Mejor en Simulacros</h4>
                    <h2>{max_prom:.2f}</h2>
                    <p>{mejor_sim}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # --- Tabla comparativa por materia ---
    st.markdown("### 📋 Tabla Comparativa por Materia")
    comp_dict = {"Materia": materias}
    for sim in activos:
        df_reg = get_regular_presented_df(sim["df"])
        comp_dict[sim["nombre"]] = [df_reg[mat].mean() for mat in materias]

    if has_icfes_real:
        comp_dict["🎯 ICFES Real"] = [df_icfes_regular[mat].mean() for mat in materias]

    comp_df = pd.DataFrame(comp_dict).round(2)
    st.dataframe(
        comp_df.style.background_gradient(subset=[c for c in comp_df.columns if c != "Materia"], cmap="RdYlGn", vmin=40, vmax=90),
        hide_index=True,
        use_container_width=True,
    )

    # --- Evolución del promedio general ---
    st.markdown("<h2 class='section-header'>📈 Evolución del Promedio General</h2>", unsafe_allow_html=True)

    x_labels = [sim["nombre"] for sim in simulacros]
    y_values = list(promedios_generales)
    marker_colors = [color_map.get(sim["nombre"], "#667eea") for sim in simulacros]

    if has_icfes_real and icfes_real_prom is not None:
        x_labels.append("🎯 ICFES Real")
        y_values.append(icfes_real_prom)
        marker_colors.append("#f1c40f")

    fig_line = go.Figure()
    fig_line.add_trace(
        go.Scatter(
            x=x_labels,
            y=y_values,
            mode="lines+markers+text",
            text=[f"{p:.2f}" if pd.notna(p) else "-" for p in y_values],
            textposition="top center",
            line=dict(color="#667eea", width=4),
            marker=dict(size=16, color=marker_colors, line=dict(color="#ffffff", width=2)),
        )
    )
    fig_line.update_layout(title="Tendencia del Promedio Ponderado General", yaxis_title="Promedio Ponderado / Global", height=420, template="plotly_white")
    st.plotly_chart(fig_line, use_container_width=True)

    # --- Tabla Comparativa Lado a Lado por Estudiante ---
    st.markdown("---")
    st.markdown("### 👤 Tabla Comparativa Lado a Lado por Estudiante")

    estudiantes_set = set()
    for sim in simulacros:
        if "ESTUDIANTE" in sim["df"].columns:
            estudiantes_set.update(sim["df"]["ESTUDIANTE"].dropna().tolist())

    if has_icfes_real and "ESTUDIANTE" in df_icfes_real.columns:
        estudiantes_set.update(df_icfes_real["ESTUDIANTE"].dropna().tolist())

    est_list = sorted(list(estudiantes_set))
    rows_est = []

    icfes_map = {}
    if has_icfes_real:
        for _, r in df_icfes_real.iterrows():
            icfes_map[r["ESTUDIANTE"]] = (r.get("PROMEDIO PONDERADO"), r.get("es_inclusion", False))

    for est in est_list:
        row = {"Estudiante": est}
        sim_vals = []
        is_inc = False

        for sim in simulacros:
            sub = sim["df"][sim["df"]["ESTUDIANTE"] == est]
            if not sub.empty:
                val = sub.iloc[0].get("PROMEDIO PONDERADO")
                row[sim["nombre"]] = round(val, 2) if pd.notna(val) else None
                if pd.notna(val):
                    sim_vals.append(val)
                if sub.iloc[0].get("es_inclusion"):
                    is_inc = True
            else:
                row[sim["nombre"]] = None

        prom_sims = np.nanmean(sim_vals) if sim_vals else None
        row["Prom. Simulacros"] = round(prom_sims, 2) if prom_sims is not None and not np.isnan(prom_sims) else None

        if has_icfes_real:
            real_tuple = icfes_map.get(est)
            if real_tuple:
                real_val, inc_flag = real_tuple
                if inc_flag:
                    is_inc = True
                row["🎯 ICFES Real"] = round(real_val, 2) if real_val is not None and not np.isnan(real_val) else None
            else:
                row["🎯 ICFES Real"] = None

            if row["Prom. Simulacros"] is not None and row.get("🎯 ICFES Real") is not None:
                row["Δ (ICFES - Prom)"] = round(row["🎯 ICFES Real"] - row["Prom. Simulacros"], 2)
            else:
                row["Δ (ICFES - Prom)"] = None

        row["Inclusión"] = "Sí" if is_inc else "No"
        rows_est.append(row)

    df_est_comp = pd.DataFrame(rows_est)
    if not df_est_comp.empty:
        cols_order = ["Estudiante", "Inclusión"] + [c for c in df_est_comp.columns if c not in ["Estudiante", "Inclusión"]]
        df_est_comp = df_est_comp[cols_order]

        subset_grad = [c for c in ["Prom. Simulacros", "🎯 ICFES Real"] if c in df_est_comp.columns]
        st.dataframe(
            df_est_comp.style.format(na_rep="No presentó").background_gradient(subset=subset_grad, cmap="YlGnBu", vmin=250, vmax=450),
            hide_index=True,
            use_container_width=True,
        )
