import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..auth import get_user_role
from ..config import MATERIAS
from ..data import get_regular_presented_df, load_all_simulacros, ordenar_simulacros
from ..promociones import get_user_promotions


def _format_num(val: Optional[float], decimals: int = 1) -> str:
    if val is None or pd.isna(val):
        return "-"
    return f"{val:.{decimals}f}"


def _build_single_metric_card(
    title: str,
    val_a: Optional[float],
    val_b: Optional[float],
    unit: str = "pts",
    decimals: int = 1
) -> str:
    """Genera una tarjeta métrica responsiva que no se desborda en ninguna resolución."""
    str_a = _format_num(val_a, decimals)
    str_b = _format_num(val_b, decimals)

    delta_str = "Δ: -"
    delta_color = "#64748b"
    delta_bg = "rgba(100, 116, 139, 0.12)"

    if val_a is not None and val_b is not None and pd.notna(val_a) and pd.notna(val_b):
        diff = val_b - val_a
        sign = "+" if diff > 0 else ""
        delta_str = f"Δ: {sign}{diff:.{decimals}f} {unit}".strip()
        if diff > (0.1 if decimals > 0 else 0):
            delta_color = "#059669"
            delta_bg = "rgba(16, 185, 129, 0.14)"
        elif diff < (-0.1 if decimals > 0 else 0):
            delta_color = "#dc2626"
            delta_bg = "rgba(239, 68, 68, 0.14)"

    return f"""
    <div style="
        background: #ffffff;
        border-radius: 14px;
        padding: 1.1rem 1rem;
        border: 1px solid rgba(26, 115, 232, 0.12);
        border-top: 3px solid #1a73e8;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04), 0 6px 16px rgba(26,115,232,0.06);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-width: 0;
        box-sizing: border-box;
    ">
        <div style="
            font-size: 0.82rem;
            font-weight: 700;
            color: #1e3a5f;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            margin-bottom: 0.75rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        " title="{title}">
            {title}
        </div>
        <div style="
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            align-items: center;
            margin-bottom: 0.75rem;
        ">
            <div style="
                text-align: center;
                border-right: 1px solid rgba(0,0,0,0.08);
                padding-right: 0.25rem;
                min-width: 0;
            ">
                <div style="
                    font-size: 0.7rem;
                    font-weight: 700;
                    color: #1a73e8;
                    text-transform: uppercase;
                    margin-bottom: 0.2rem;
                ">
                    Lado A
                </div>
                <div style="
                    font-size: clamp(1.2rem, 1.8vw, 1.55rem);
                    font-weight: 800;
                    color: #0f172a;
                    line-height: 1.1;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                ">
                    {str_a}
                </div>
            </div>
            <div style="
                text-align: center;
                padding-left: 0.25rem;
                min-width: 0;
            ">
                <div style="
                    font-size: 0.7rem;
                    font-weight: 700;
                    color: #8b5cf6;
                    text-transform: uppercase;
                    margin-bottom: 0.2rem;
                ">
                    Lado B
                </div>
                <div style="
                    font-size: clamp(1.2rem, 1.8vw, 1.55rem);
                    font-weight: 800;
                    color: #0f172a;
                    line-height: 1.1;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                ">
                    {str_b}
                </div>
            </div>
        </div>
        <div style="text-align: center; margin-top: auto;">
            <span style="
                display: inline-block;
                max-width: 100%;
                font-size: 0.78rem;
                font-weight: 700;
                color: {delta_color};
                background: {delta_bg};
                padding: 0.25rem 0.65rem;
                border-radius: 9999px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            ">
                {delta_str}
            </span>
        </div>
    </div>
    """


def render(user_email: str):
    # Verificación de Rol Administrador
    if get_user_role(user_email) != "admin":
        st.error("🔒 No tienes permisos de Administrador para acceder a esta sección.")
        st.stop()

    st.markdown("<h1 class='header-title'>⚖️ Comparación Simulacro vs. Promoción</h1>", unsafe_allow_html=True)
    st.markdown(
        """
        <p class='header-subtitle'>
            Herramienta administrativa de análisis cruzado en vista dividida (Split-View): 
            compara el desempeño global, promedios por área del ICFES y rankings de estudiantes 
            entre dos evaluaciones cualesquiera, sin importar la cohorte o el año.
        </p>
        """,
        unsafe_allow_html=True,
    )

    # 1. Cargar lista de promociones disponibles
    promociones_disponibles = get_user_promotions(user_email)
    if not promociones_disponibles:
        st.warning("⚠️ No hay promociones registradas en la base de datos.")
        st.stop()

    promos_dict = {f"{p['nombre']} ({p['anio_graduacion']})": p for p in promociones_disponibles}
    promo_keys = list(promos_dict.keys())

    # --- Controles Globales de Filtro ---
    c_flt1, c_flt2 = st.columns([2, 1])
    with c_flt1:
        excluir_inclusion = st.checkbox(
            "♿ Excluir estudiantes en condición de inclusión (Protocolo Institucional)",
            value=True,
            help="Al activar esta opción, los promedios y estadísticas se calculan únicamente con los estudiantes regulares.",
            key="cmp_excluir_inc"
        )
    with c_flt2:
        top_n_rank = st.selectbox(
            "Visualización de Ranking",
            options=[10, 20, 30, 50, 0],
            format_func=lambda x: f"Top {x} Estudiantes" if x > 0 else "Todos los Estudiantes",
            index=1,
            key="cmp_top_n_select"
        )

    st.markdown("---")

    # =========================================================================
    # SELECTORES EN SPLIT-VIEW (COLUMNA A vs COLUMNA B)
    # =========================================================================
    col_sel_a, col_sel_b = st.columns(2)

    # --- SELECCIÓN LADO A ---
    with col_sel_a:
        st.markdown(
            """
            <div style="background: rgba(26, 115, 232, 0.08); border-left: 4px solid #1a73e8; padding: 0.8rem 1rem; border-radius: 8px; margin-bottom: 1rem;">
                <h4 style="margin: 0; color: #1a73e8; font-weight: 700;">🔵 Evaluación Base (Lado A)</h4>
            </div>
            """,
            unsafe_allow_html=True
        )
        default_a_idx = 0
        sel_promo_label_a = st.selectbox(
            "Seleccionar Promoción A",
            options=promo_keys,
            index=default_a_idx,
            key="cmp_promo_sel_a"
        )
        promo_a = promos_dict[sel_promo_label_a]
        _, data_map_a, _ = load_all_simulacros(promo_a["id"])
        sims_a = ordenar_simulacros(data_map_a)

        if not sims_a:
            st.info(f"ℹ️ La promoción '{promo_a['nombre']}' no tiene simulacros registrados.")
            sim_a_selected = None
        else:
            sims_a_map = {s["nombre"]: s for s in sims_a}
            sel_sim_nombre_a = st.selectbox(
                "Seleccionar Simulacro A",
                options=list(sims_a_map.keys()),
                index=0,
                key="cmp_sim_sel_a"
            )
            sim_a_selected = sims_a_map[sel_sim_nombre_a]

    # --- SELECCIÓN LADO B ---
    with col_sel_b:
        st.markdown(
            """
            <div style="background: rgba(139, 92, 246, 0.08); border-left: 4px solid #8b5cf6; padding: 0.8rem 1rem; border-radius: 8px; margin-bottom: 1rem;">
                <h4 style="margin: 0; color: #8b5cf6; font-weight: 700;">🟣 Evaluación de Contraste (Lado B)</h4>
            </div>
            """,
            unsafe_allow_html=True
        )
        default_b_idx = 1 if len(promo_keys) > 1 else 0
        sel_promo_label_b = st.selectbox(
            "Seleccionar Promoción B",
            options=promo_keys,
            index=default_b_idx,
            key="cmp_promo_sel_b"
        )
        promo_b = promos_dict[sel_promo_label_b]
        _, data_map_b, _ = load_all_simulacros(promo_b["id"])
        sims_b = ordenar_simulacros(data_map_b)

        if not sims_b:
            st.info(f"ℹ️ La promoción '{promo_b['nombre']}' no tiene simulacros registrados.")
            sim_b_selected = None
        else:
            sims_b_map = {s["nombre"]: s for s in sims_b}
            default_sim_b_idx = min(1, len(sims_b_map) - 1) if (promo_a["id"] == promo_b["id"] and len(sims_b_map) > 1) else 0
            sel_sim_nombre_b = st.selectbox(
                "Seleccionar Simulacro B",
                options=list(sims_b_map.keys()),
                index=default_sim_b_idx,
                key="cmp_sim_sel_b"
            )
            sim_b_selected = sims_b_map[sel_sim_nombre_b]

    if not sim_a_selected or not sim_b_selected:
        st.warning("⚠️ Selecciona simulacros válidos en ambos lados para generar la comparación.")
        return

    # Extraer DataFrames procesados
    df_raw_a = sim_a_selected["df"].copy() if sim_a_selected["df"] is not None else pd.DataFrame()
    df_raw_b = sim_b_selected["df"].copy() if sim_b_selected["df"] is not None else pd.DataFrame()

    df_a = get_regular_presented_df(df_raw_a) if excluir_inclusion else df_raw_a.copy()
    df_b = get_regular_presented_df(df_raw_b) if excluir_inclusion else df_raw_b.copy()

    # Sanitizar columnas numéricas
    for col in MATERIAS + ["PROMEDIO PONDERADO", "PROMEDIO SIMPLE"]:
        if col in df_a.columns:
            df_a[col] = pd.to_numeric(df_a[col], errors="coerce")
        if col in df_b.columns:
            df_b[col] = pd.to_numeric(df_b[col], errors="coerce")

    tag_a = f"{promo_a['nombre']} — {sim_a_selected['nombre']}"
    tag_b = f"{promo_b['nombre']} — {sim_b_selected['nombre']}"

    # =========================================================================
    # RESUMEN GENERAL Y MÉTRICAS CLAVE (TOP LEVEL)
    # =========================================================================
    st.markdown("<h2 class='section-header'>📊 Comparación de Promedios Generales y Dimensiones</h2>", unsafe_allow_html=True)

    # Banner informativo de leyenda A vs B
    st.markdown(
        f"""
        <div style="
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 0.8rem 1.2rem;
            margin-bottom: 1.2rem;
            gap: 0.8rem;
        ">
            <div style="display: flex; align-items: center; gap: 0.6rem; min-width: 220px; flex: 1;">
                <span style="display: inline-block; width: 14px; height: 14px; background: #1a73e8; border-radius: 50%; flex-shrink: 0;"></span>
                <span style="font-size: 0.9rem; color: #1e293b; font-weight: 500;">
                    Lado A: <strong style="color: #1a73e8; font-weight: 700;">{tag_a}</strong>
                </span>
            </div>
            <div style="font-weight: 800; color: #94a3b8; font-size: 0.85rem; padding: 0 0.5rem;">
                VS
            </div>
            <div style="display: flex; align-items: center; gap: 0.6rem; min-width: 220px; flex: 1; justify-content: flex-end;">
                <span style="display: inline-block; width: 14px; height: 14px; background: #8b5cf6; border-radius: 50%; flex-shrink: 0;"></span>
                <span style="font-size: 0.9rem; color: #1e293b; font-weight: 500;">
                    Lado B: <strong style="color: #8b5cf6; font-weight: 700;">{tag_b}</strong>
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    prom_gen_a = df_a["PROMEDIO PONDERADO"].dropna().mean() if not df_a.empty and "PROMEDIO PONDERADO" in df_a.columns else None
    prom_gen_b = df_b["PROMEDIO PONDERADO"].dropna().mean() if not df_b.empty and "PROMEDIO PONDERADO" in df_b.columns else None

    n_est_a = len(df_a["PROMEDIO PONDERADO"].dropna()) if not df_a.empty and "PROMEDIO PONDERADO" in df_a.columns else 0
    n_est_b = len(df_b["PROMEDIO PONDERADO"].dropna()) if not df_b.empty and "PROMEDIO PONDERADO" in df_b.columns else 0

    max_a = df_a["PROMEDIO PONDERADO"].dropna().max() if not df_a.empty and "PROMEDIO PONDERADO" in df_a.columns else None
    max_b = df_b["PROMEDIO PONDERADO"].dropna().max() if not df_b.empty and "PROMEDIO PONDERADO" in df_b.columns else None

    std_a = df_a["PROMEDIO PONDERADO"].dropna().std() if not df_a.empty and "PROMEDIO PONDERADO" in df_a.columns and len(df_a.dropna(subset=["PROMEDIO PONDERADO"])) > 1 else None
    std_b = df_b["PROMEDIO PONDERADO"].dropna().std() if not df_b.empty and "PROMEDIO PONDERADO" in df_b.columns and len(df_b.dropna(subset=["PROMEDIO PONDERADO"])) > 1 else None

    # Renderizado en Grid CSS Responsivo fluido (se auto-ajusta a 4, 2 o 1 columna según pantalla)
    card_promedio = _build_single_metric_card("🏆 Promedio General", prom_gen_a, prom_gen_b, unit="pts", decimals=1)
    card_evaluados = _build_single_metric_card("👥 Evaluados", float(n_est_a), float(n_est_b), unit="est", decimals=0)
    card_maximo = _build_single_metric_card("🔝 Puntaje Máximo", max_a, max_b, unit="pts", decimals=1)
    card_desviacion = _build_single_metric_card("📉 Desviación Estándar", std_a, std_b, unit="σ", decimals=1)

    cards_grid_html = f"""
    <div style="
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    ">
        {card_promedio}
        {card_evaluados}
        {card_maximo}
        {card_desviacion}
    </div>
    """
    st.markdown(cards_grid_html, unsafe_allow_html=True)

    # =========================================================================
    # COMPARACIÓN DETALLADA DE PROMEDIOS POR MATERIA
    # =========================================================================
    st.markdown("<h2 class='section-header'>📈 Desempeño Comparativo por Asignatura ICFES</h2>", unsafe_allow_html=True)

    mats_a_means = [df_a[m].dropna().mean() if (m in df_a.columns and not df_a[m].dropna().empty) else 0.0 for m in MATERIAS]
    mats_b_means = [df_b[m].dropna().mean() if (m in df_b.columns and not df_b[m].dropna().empty) else 0.0 for m in MATERIAS]

    # Gráfico de barras agrupadas comparativo
    fig_comp = go.Figure()
    fig_comp.add_trace(
        go.Bar(
            name=f"🔵 Lado A: {tag_a}",
            x=MATERIAS,
            y=mats_a_means,
            marker_color="#1a73e8",
            text=[f"{v:.1f}" if v > 0 else "-" for v in mats_a_means],
            textposition="auto",
        )
    )
    fig_comp.add_trace(
        go.Bar(
            name=f"🟣 Lado B: {tag_b}",
            x=MATERIAS,
            y=mats_b_means,
            marker_color="#8b5cf6",
            text=[f"{v:.1f}" if v > 0 else "-" for v in mats_b_means],
            textposition="auto",
        )
    )

    fig_comp.update_layout(
        barmode="group",
        height=420,
        title="Comparación Directa de Notas Medias por Asignatura (Escala 0 - 100)",
        yaxis=dict(title="Puntaje Medio", range=[0, 100]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
    )
    st.plotly_chart(fig_comp, use_container_width=True, key="fig_comp_mats_prom")

    # Tabla resumen de variación por materia con nombres de columna limpios
    tabla_mats = []
    for mat, va, vb in zip(MATERIAS, mats_a_means, mats_b_means):
        diff = vb - va
        diff_str = f"{'+' if diff > 0 else ''}{diff:.2f} pts"
        estado = "📈 Superior en B" if diff > 0.5 else ("📉 Superior en A" if diff < -0.5 else "⚖️ Similar")
        tabla_mats.append({
            "Materia ICFES": mat,
            "🔵 Promedio Lado A": round(va, 2),
            "🟣 Promedio Lado B": round(vb, 2),
            "Diferencia (B - A)": diff_str,
            "Diagnóstico": estado
        })
    df_tabla_mats = pd.DataFrame(tabla_mats)
    st.dataframe(df_tabla_mats, hide_index=True, use_container_width=True)

    # =========================================================================
    # RANKINGS EN SPLIT-VIEW (COLUMNA A vs COLUMNA B)
    # =========================================================================
    st.markdown("<h2 class='section-header'>🏆 Rankings de Estudiantes por Simulacro (Split-View)</h2>", unsafe_allow_html=True)
    st.caption("Visualiza lado a lado las posiciones, notas globales y desempeño por estudiante de cada simulacro seleccionado.")

    c_rank_a, c_rank_b = st.columns(2)

    def _build_ranking_table(df_input: pd.DataFrame, limit: int) -> pd.DataFrame:
        if df_input.empty or "ESTUDIANTE" not in df_input.columns or "PROMEDIO PONDERADO" not in df_input.columns:
            return pd.DataFrame()
        
        df_rank = df_input.dropna(subset=["PROMEDIO PONDERADO"]).copy()
        df_rank = df_rank.sort_values(by="PROMEDIO PONDERADO", ascending=False).reset_index(drop=True)
        
        # Asignar posición e íconos para podio
        puestos = []
        for i in range(len(df_rank)):
            if i == 0:
                puestos.append("🥇 1")
            elif i == 1:
                puestos.append("🥈 2")
            elif i == 2:
                puestos.append("🥉 3")
            else:
                puestos.append(str(i + 1))
        df_rank["Puesto"] = puestos

        cols_select = ["Puesto", "ESTUDIANTE"]
        if "GRADO" in df_rank.columns:
            cols_select.append("GRADO")
        cols_select.append("PROMEDIO PONDERADO")
        for m in MATERIAS:
            if m in df_rank.columns:
                cols_select.append(m)

        df_res = df_rank[cols_select].copy()
        if limit > 0:
            df_res = df_res.head(limit)
        return df_res

    # --- RANKING LADO A ---
    with c_rank_a:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%); color: white; padding: 0.6rem 1rem; border-radius: 8px; font-weight: 700; margin-bottom: 0.8rem; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{tag_a}">
                🔵 Ranking A: {tag_a} ({len(df_a)} est.)
            </div>
            """,
            unsafe_allow_html=True
        )
        search_a = st.text_input("🔍 Buscar estudiante en Lado A", key="search_rank_a", placeholder="Nombre...")
        df_display_a = df_a.copy()
        if search_a and search_a.strip():
            df_display_a = df_display_a[df_display_a["ESTUDIANTE"].astype(str).str.contains(search_a.strip(), case=False, na=False)]

        table_a = _build_ranking_table(df_display_a, top_n_rank)
        if table_a.empty:
            st.info("No se encontraron registros para mostrar en el ranking de A.")
        else:
            st.dataframe(
                table_a.style.format({
                    "PROMEDIO PONDERADO": "{:.1f}",
                    **{m: "{:.1f}" for m in MATERIAS if m in table_a.columns}
                }),
                hide_index=True,
                use_container_width=True,
                height=480
            )

    # --- RANKING LADO B ---
    with c_rank_b:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); color: white; padding: 0.6rem 1rem; border-radius: 8px; font-weight: 700; margin-bottom: 0.8rem; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{tag_b}">
                🟣 Ranking B: {tag_b} ({len(df_b)} est.)
            </div>
            """,
            unsafe_allow_html=True
        )
        search_b = st.text_input("🔍 Buscar estudiante en Lado B", key="search_rank_b", placeholder="Nombre...")
        df_display_b = df_b.copy()
        if search_b and search_b.strip():
            df_display_b = df_display_b[df_display_b["ESTUDIANTE"].astype(str).str.contains(search_b.strip(), case=False, na=False)]

        table_b = _build_ranking_table(df_display_b, top_n_rank)
        if table_b.empty:
            st.info("No se encontraron registros para mostrar en el ranking de B.")
        else:
            st.dataframe(
                table_b.style.format({
                    "PROMEDIO PONDERADO": "{:.1f}",
                    **{m: "{:.1f}" for m in MATERIAS if m in table_b.columns}
                }),
                hide_index=True,
                use_container_width=True,
                height=480
            )
