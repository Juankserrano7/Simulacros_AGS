import colorsys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _hex_from_hsl(h: float, s: float = 0.65, l: float = 0.5) -> str:
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def _sim_colors(simulacros) -> dict:
    # Palette base + deterministic HSL fallback for scalability
    base = [
        "#27ae60",
        "#f39c12",
        "#e74c3c",
        "#667eea",
        "#9b59b6",
        "#16a085",
        "#2980b9",
        "#d35400",
        "#2c3e50",
        "#8e44ad",
        "#c0392b",
        "#1abc9c",
        "#34495e",
    ]
    colors = {}
    for idx, sim in enumerate(simulacros):
        if idx < len(base):
            colors[sim["nombre"]] = base[idx]
        else:
            # Golden ratio spacing for distinct hues
            h = (0.61803398875 * idx) % 1.0
            colors[sim["nombre"]] = _hex_from_hsl(h)
    return colors


def render(simulacros, materias):
    if len(simulacros) < 2:
        st.warning("Carga al menos dos simulacros para comparar.")
        return

    st.markdown("<h1 class='header-title'>🔬 Comparación entre Simulacros</h1>", unsafe_allow_html=True)

    seleccionados = st.multiselect(
        "Elige los simulacros a comparar",
        options=[sim["nombre"] for sim in simulacros],
        default=[sim["nombre"] for sim in simulacros[-3:]],
    )
    activos = [sim for sim in simulacros if sim["nombre"] in seleccionados]
    if len(activos) < 2:
        st.info("Selecciona al menos dos simulacros.")
        return

    st.markdown("<h2 class='section-header'>📊 Comparación de Promedios por Materia</h2>", unsafe_allow_html=True)
    color_map = _sim_colors(activos)
    fig = go.Figure()

    for sim in activos:
        fig.add_trace(
            go.Bar(
                name=sim["nombre"],
                x=materias,
                y=[sim["df"][mat].mean() for mat in materias],
                marker=dict(color=color_map.get(sim["nombre"], "#667eea")),
            )
        )

        fig.update_layout(
            barmode="group",
            height=450,
            title="Promedios por materia",
            xaxis_title="Materia",
            yaxis_title="Puntaje Promedio",
            template="plotly_white",
        )

    st.plotly_chart(fig, width="stretch")

    st.markdown("### 🔥 Variaciones clave")
    promedios_generales = [sim["df"]["PROMEDIO PONDERADO"].mean() for sim in simulacros]
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(
            f"""
        <div class='stats-box'>
            <h4>Último promedio</h4>
            <h2>{promedios_generales[-1]:.2f}</h2>
            <p>{simulacros[-1]['nombre']}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    if len(promedios_generales) > 1:
        delta = promedios_generales[-1] - promedios_generales[-2]
        with col_b:
            st.markdown(
                f"""
            <div class='stats-box' style='background: linear-gradient(135deg, #00c6ff 0%, #0072ff 100%);'>
                <h4>Δ último vs previo</h4>
                <h2>{delta:+.2f}</h2>
                <p>Puntos</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
    if len(promedios_generales) > 0:
        max_prom = max(promedios_generales)
        mejor = simulacros[promedios_generales.index(max_prom)]["nombre"]
        with col_c:
            st.markdown(
                f"""
            <div class='stats-box' style='background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);'>
                <h4>Mejor histórico</h4>
                <h2>{max_prom:.2f}</h2>
                <p>{mejor}</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    st.markdown("### 📋 Tabla comparativa")
    comp_df = pd.DataFrame(
        {
            "Materia": materias,
            **{sim["nombre"]: [sim["df"][mat].mean() for mat in materias] for sim in activos},
        }
    ).round(2)
    st.dataframe(
        comp_df.style.background_gradient(subset=[c for c in comp_df.columns if c != "Materia"], cmap="RdYlGn", vmin=40, vmax=90),
        hide_index=True,
        width="stretch",
    )

    st.markdown("---")
    st.markdown("<h2 class='section-header'>📈 Evolución del promedio general</h2>", unsafe_allow_html=True)
    fig_line = go.Figure()
    color_map_all = _sim_colors(simulacros)
    fig_line.add_trace(
        go.Scatter(
            x=[sim["nombre"] for sim in simulacros],
            y=promedios_generales,
            mode="lines+markers+text",
            text=[f"{p:.2f}" for p in promedios_generales],
            textposition="top center",
            line=dict(color="#667eea", width=4),
            marker=dict(
                size=15,
                color=[color_map_all.get(sim["nombre"], "#667eea") for sim in simulacros],
            ),
        )
    )
    fig_line.update_layout(title="Tendencia del Promedio Ponderado", yaxis_title="Promedio Ponderado", height=420, template="plotly_white")

    col_line, col_table = st.columns([2, 1])
    with col_line:
        st.plotly_chart(fig_line, width="stretch")
    with col_table:
        cambios = []
        for idx in range(1, len(simulacros)):
            actual = promedios_generales[idx]
            anterior = promedios_generales[idx - 1]
            delta = actual - anterior
            porcentaje = (delta / anterior * 100) if anterior else 0
            cambios.append(
                {
                    "Transición": f"{simulacros[idx - 1]['nombre']} → {simulacros[idx]['nombre']}",
                    "Δ puntos": round(delta, 2),
                    "%": f"{porcentaje:.2f}",
                }
            )
        if cambios:
            st.markdown("### 📉 Cambios Registrados")
            st.dataframe(pd.DataFrame(cambios), hide_index=True, width="stretch")
