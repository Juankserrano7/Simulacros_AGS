"""Módulo para la captura, edición, carga masiva y eliminación de simulacros y resultados oficiales ICFES Real."""

from typing import List

import pandas as pd
import streamlit as st

from ..auth import get_user_role
from ..core_utils import get_db_connection
from ..data import (
    delete_simulacro,
    generate_template_bytes,
    ingest_icfes_real_excel,
    ingest_simulacro_excel,
    load_all_simulacros,
    ordenar_simulacros,
    save_manual_icfes_real_grid,
    save_manual_simulacro_grid,
    update_manual_simulacro_grid,
    update_simulacro_nombre,
)

GRID_COLUMN_CONFIG = {
    "ESTUDIANTE": st.column_config.TextColumn("Estudiante", width="large"),
    "LECTURA CRÍTICA": st.column_config.NumberColumn("Lectura Crítica (0-100)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
    "MATEMÁTICAS": st.column_config.NumberColumn("Matemáticas (0-100)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
    "SOCIALES Y CIUDADANAS": st.column_config.NumberColumn("Sociales (0-100)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
    "CIENCIAS NATURALES": st.column_config.NumberColumn("Ciencias (0-100)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
    "INGLÉS": st.column_config.NumberColumn("Inglés (0-100)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
    "PUNTAJE GLOBAL (0-500)": st.column_config.NumberColumn("Puntaje Global", min_value=0.0, max_value=500.0, step=1.0, format="%.1f"),
}


def _get_promotion_students(promocion_id: str) -> List[str]:
    """Carga los nombres de los estudiantes registrados para la promoción activa."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT nombre FROM estudiantes
                WHERE promocion_id = %s
                ORDER BY nombre ASC;
            """, (promocion_id,))
            return [r[0] for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()


def _render_tab_crear(promocion_id: str, promocion_nombre: str, estudiantes_list: List[str], user_email: str) -> None:
    """Renderiza el flujo de creación de simulacro o ingesta de ICFES Real."""
    st.markdown("#### ⚙️ Selección de Tipo de Evaluación")
    tipo_eval = st.radio(
        "¿Qué deseas registrar?",
        options=["📋 Simulacro de Preparación", "🎯 Resultado Oficial ICFES Real"],
        horizontal=True,
        key="radio_tipo_eval_crear",
        help="Los simulacros alimentan la trayectoria y evolución temporal. Los resultados del ICFES Real marcan el cierre oficial de la cohorte y recalibran automáticamente los modelos de Machine Learning."
    )

    es_icfes_real = (tipo_eval == "🎯 Resultado Oficial ICFES Real")

    if es_icfes_real:
        st.info(
            "📌 **Modo: Resultados Oficiales ICFES Real.** Las notas ingresadas se guardarán en el registro "
            "oficial de la promoción, habilitando la pestaña de cotejo final y actualizando los parámetros de calibración de Machine Learning."
        )

    subtab_manual, subtab_archivo = st.tabs(["📝 Ingreso Manual por Grilla", "📁 Carga por Archivo Excel/CSV"])

    with subtab_manual:
        if not estudiantes_list:
            st.warning(f"⚠️ La promoción **{promocion_nombre}** no tiene estudiantes registrados aún.")
            return

        st.markdown(f"**Estudiantes registrados ({len(estudiantes_list)}):**")
        
        st.markdown("##### ✏️ Grilla de Puntajes (Notas de 0 a 100 por asignatura):")
        st.caption("Puedes ingresar todas las notas con fluidez. Los datos solo se guardarán cuando hagas clic en el botón de abajo.")

        init_data = [
            {
                "ESTUDIANTE": est,
                "LECTURA CRÍTICA": 0.0,
                "MATEMÁTICAS": 0.0,
                "SOCIALES Y CIUDADANAS": 0.0,
                "CIENCIAS NATURALES": 0.0,
                "INGLÉS": 0.0,
                "PUNTAJE GLOBAL (0-500)": 0.0,
            }
            for est in estudiantes_list
        ]
        df_init = pd.DataFrame(init_data)

        with st.form(key=f"form_sim_new_{promocion_id}_{es_icfes_real}", clear_on_submit=False):
            if not es_icfes_real:
                nombre_simulacro = st.text_input("Nombre del Nuevo Simulacro", placeholder="Ej: Simulacro Diagnóstico 1", key="new_sim_name")
            else:
                nombre_simulacro = "ICFES Real"

            edited_df = st.data_editor(
                df_init,
                disabled=["ESTUDIANTE"],
                column_config=GRID_COLUMN_CONFIG,
                hide_index=True,
                use_container_width=True,
                key=f"grid_sim_new_{promocion_id}_{es_icfes_real}"
            )

            btn_label = "💾 Guardar Resultados Oficiales ICFES Real" if es_icfes_real else "💾 Guardar Simulacro"
            submit_save = st.form_submit_button(btn_label, type="primary", use_container_width=True)

        if submit_save:
            if not es_icfes_real and (not nombre_simulacro or not nombre_simulacro.strip()):
                st.error("⚠️ Debes ingresar un nombre válido para el simulacro.")
            else:
                with st.spinner("Guardando resultados, aplicando fórmulas y actualizando modelos..."):
                    if es_icfes_real:
                        ok, mensaje, _ = save_manual_icfes_real_grid(
                            promocion_id=promocion_id,
                            df_editor=edited_df,
                            usuario=user_email
                        )
                    else:
                        ok, mensaje, _ = save_manual_simulacro_grid(
                            nombre=nombre_simulacro.strip(),
                            promocion_id=promocion_id,
                            df_editor=edited_df,
                            usuario=user_email
                        )

                if ok:
                    st.success(mensaje)
                    st.balloons()
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(mensaje)

    with subtab_archivo:
        st.markdown("##### 📥 Descargar Plantilla Excel Oficial")
        tmpl_bytes = generate_template_bytes()
        st.download_button(
            label="⬇️ Descargar Plantilla de Notas (.xlsx)",
            data=tmpl_bytes,
            file_name="plantilla_notas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("---")
        st.markdown(f"##### 📤 Cargar Archivo de {'Resultados ICFES Real' if es_icfes_real else 'Simulacro'} (Excel / CSV)")

        nombre_sim_file = ""
        if not es_icfes_real:
            nombre_sim_file = st.text_input("Nombre del Simulacro a Importar", placeholder="Ej: Helmer Pardo 1", key="sim_file_name")

        uploaded_file = st.file_uploader("Seleccionar archivo (.xlsx, .csv)", type=["xlsx", "xls", "csv"], key="sim_file_uploader")

        btn_upload_label = "🚀 Ingestar Resultados ICFES Real" if es_icfes_real else "🚀 Ingestar Simulacro"

        if uploaded_file and st.button(btn_upload_label, type="primary", use_container_width=True):
            if not es_icfes_real and (not nombre_sim_file or not nombre_sim_file.strip()):
                st.error("⚠️ Ingresa un nombre para el simulacro.")
            else:
                with st.spinner("Procesando archivo e importando notas..."):
                    if es_icfes_real:
                        ok, msg, _ = ingest_icfes_real_excel(uploaded_file, user_email, promocion_id=promocion_id)
                    else:
                        ok, msg, _ = ingest_simulacro_excel(nombre_sim_file.strip(), uploaded_file, user_email, promocion_id=promocion_id)

                if ok:
                    st.success(msg)
                    st.balloons()
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)


def _render_tab_editar(simulacros_existentes: List[dict], user_email: str) -> None:
    """Renderiza el flujo de edición de notas y nombre de simulacros existentes."""
    if not simulacros_existentes:
        st.info("ℹ️ No hay simulacros guardados aún para esta promoción.")
        return

    sim_map = {sim["id"]: sim for sim in simulacros_existentes}
    sim_ids = list(sim_map.keys())

    selected_sim_id = st.selectbox(
        "Seleccionar Simulacro a Modificar",
        options=sim_ids,
        format_func=lambda s_id: sim_map[s_id]["nombre"],
        key="select_sim_edit"
    )

    if not selected_sim_id:
        return

    sim_actual = sim_map[selected_sim_id]
    st.markdown("---")

    # 1. Renombrar
    st.markdown("##### ✏️ Renombrar Simulacro")
    c_ren1, c_ren2 = st.columns([3, 1])
    with c_ren1:
        nuevo_nombre = st.text_input("Nombre Actualizado", value=sim_actual["nombre"], key="input_rename_sim")
    with c_ren2:
        st.write("")
        st.write("")
        if st.button("Guardar Nombre", use_container_width=True, key="btn_rename_sim"):
            if nuevo_nombre.strip() == sim_actual["nombre"]:
                st.info("El nombre no ha cambiado.")
            else:
                with st.spinner("Actualizando nombre..."):
                    ok, msg = update_simulacro_nombre(selected_sim_id, nuevo_nombre.strip(), user_email)
                if ok:
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)

    st.markdown("---")

    # 2. Edición de Notas
    st.markdown("##### 📊 Editar Notas de Estudiantes")
    df_actual = sim_actual["df"].copy()
    if "ESTUDIANTE" not in df_actual.columns:
        st.error("Formato incompatible de simulacro.")
        return

    cols_grid = [c for c in ["ESTUDIANTE", "LECTURA CRÍTICA", "MATEMÁTICAS", "SOCIALES Y CIUDADANAS", "CIENCIAS NATURALES", "INGLÉS", "PUNTAJE GLOBAL (0-500)"] if c in df_actual.columns]
    if "PUNTAJE GLOBAL (0-500)" not in df_actual.columns and "PROMEDIO PONDERADO" in df_actual.columns:
        df_actual["PUNTAJE GLOBAL (0-500)"] = df_actual["PROMEDIO PONDERADO"]
        cols_grid.append("PUNTAJE GLOBAL (0-500)")

    df_edit_slice = df_actual[cols_grid]

    with st.form(key=f"form_grid_edit_{selected_sim_id}", clear_on_submit=False):
        edited_grid = st.data_editor(
            df_edit_slice,
            disabled=["ESTUDIANTE"],
            column_config=GRID_COLUMN_CONFIG,
            hide_index=True,
            use_container_width=True,
            key=f"grid_edit_{selected_sim_id}"
        )
        submit_edit = st.form_submit_button("💾 Guardar Cambios en Notas", type="primary", use_container_width=True)

    if submit_edit:
        with st.spinner("Actualizando notas, recalculando ponderaciones ICFES y reentrenando insights..."):
            ok, msg = update_manual_simulacro_grid(selected_sim_id, edited_grid, user_email)
        if ok:
            st.success(msg)
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(msg)


def _render_tab_eliminar(simulacros_existentes: List[dict], user_email: str) -> None:
    """Renderiza el flujo de eliminación segura de simulacros."""
    if not simulacros_existentes:
        st.info("ℹ️ No hay simulacros para eliminar en esta promoción.")
        return

    sim_map = {sim["id"]: sim for sim in simulacros_existentes}
    sim_ids = list(sim_map.keys())

    selected_sim_id = st.selectbox(
        "Seleccionar Simulacro a Eliminar",
        options=sim_ids,
        format_func=lambda s_id: sim_map[s_id]["nombre"],
        key="select_sim_delete"
    )

    if not selected_sim_id:
        return

    sim_actual = sim_map[selected_sim_id]
    st.markdown("---")
    st.warning(f"⚠️ **Atención:** Estás a punto de eliminar definitivamente el simulacro **'{sim_actual['nombre']}'** y todos los resultados asociados a sus estudiantes.")

    confirm_check = st.checkbox("Confirmo que deseo eliminar este simulacro de forma permanente.", key="chk_confirm_delete")

    if confirm_check:
        if st.button("🗑️ Eliminar Simulacro Definitivamente", type="primary", use_container_width=True, key="btn_confirm_delete"):
            with st.spinner("Eliminando simulacro del sistema..."):
                ok, msg = delete_simulacro(selected_sim_id, user_email)
            if ok:
                st.success(msg)
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(msg)


def render(user_email: str) -> None:
    role = get_user_role(user_email)
    if role != "admin":
        st.error("⛔ Acceso denegado: Esta sección es exclusiva para Administradores.")
        st.stop()

    st.markdown("<h1 class='header-title'>📝 Gestión de Simulacros y Resultados ICFES</h1>", unsafe_allow_html=True)
    st.markdown(
        """
        Panel de captura, carga masiva, edición y eliminación de simulacros de preparación 
        y registro de resultados oficiales del ICFES Saber 11.
        """
    )

    promocion_activa_id = st.session_state.get("promocion_activa_id")
    promocion_activa_nombre = st.session_state.get("promocion_activa_nombre", "Promoción Activa")

    if not promocion_activa_id:
        st.error("⚠️ No hay una promoción activa seleccionada en la sesión.")
        return

    st.info(f"📌 Promoción activa: **{promocion_activa_nombre}**")

    # Cargar estudiantes y simulacros existentes de la promoción activa
    estudiantes_list = _get_promotion_students(promocion_activa_id)
    _, data_map, _ = load_all_simulacros(promocion_id=promocion_activa_id)
    simulacros_existentes = ordenar_simulacros(data_map)

    tab_crear, tab_editar, tab_eliminar = st.tabs([
        "➕ Registrar Evaluación (Simulacro / ICFES Real)",
        "✏️ Editar Simulacro Existente",
        "🗑️ Eliminar Simulacro"
    ])

    with tab_crear:
        _render_tab_crear(promocion_activa_id, promocion_activa_nombre, estudiantes_list, user_email)

    with tab_editar:
        _render_tab_editar(simulacros_existentes, user_email)

    with tab_eliminar:
        _render_tab_eliminar(simulacros_existentes, user_email)
