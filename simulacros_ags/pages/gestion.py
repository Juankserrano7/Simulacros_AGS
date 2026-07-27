import os
import pandas as pd
import psycopg2
import streamlit as st

from ..auth import get_user_role
from ..config import MATERIAS
from ..data import load_all_simulacros, ordenar_simulacros, save_manual_simulacro_grid


def render(user_email: str):
    if get_user_role(user_email) != "admin":
        st.error("No tienes permisos de Administrador para gestionar simulacros.")
        st.stop()

    st.markdown("<h1 class='header-title'>📝 Captura de Simulacros</h1>", unsafe_allow_html=True)
    st.markdown(
        """
        Ingresa el nombre del simulacro y digita o pega las puntuaciones de cada asignatura para la promoción activa.
        El sistema aplicará automáticamente la **ponderación oficial del ICFES** y calculará los promedios y desviaciones.
        """
    )

    promocion_id = st.session_state.get("promocion_activa_id")
    promocion_nombre = st.session_state.get("promocion_activa_nombre", "Promoción Seleccionada")

    if not promocion_id:
        st.warning("⚠️ Selecciona una promoción activa en la barra lateral para continuar.")
        st.stop()

    st.info(f"📌 Registrando notas para la promoción: **{promocion_nombre}**")

    # 1. Cargar la lista de estudiantes registrados en Supabase para esta promoción
    db_url = os.getenv("SUPABASE_DB_URL")
    estudiantes_list = []
    if db_url:
        try:
            conn = psycopg2.connect(db_url)
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT nombre FROM estudiantes
                        WHERE promocion_id = %s
                        ORDER BY nombre ASC;
                    """, (promocion_id,))
                    estudiantes_list = [r[0] for r in cur.fetchall()]
            finally:
                conn.close()
        except Exception as exc:
            st.error(f"Error consultando estudiantes de la promoción: {exc}")

    if not estudiantes_list:
        st.warning(f"⚠️ La promoción **{promocion_nombre}** no tiene estudiantes registrados aún.")
        st.stop()

    st.markdown(f"**Estudiantes registrados ({len(estudiantes_list)}):**")

    # 2. Formulario con Grilla de Captura Interactiva
    nombre_simulacro = st.text_input("Nombre del Simulacro", placeholder="Ej: Simulacro Diagnóstico 1")

    # Construir DataFrame inicial con los estudiantes
    init_data = []
    for est in estudiantes_list:
        init_data.append({
            "ESTUDIANTE": est,
            "LECTURA CRÍTICA": 0.0,
            "MATEMÁTICAS": 0.0,
            "SOCIALES Y CIUDADANAS": 0.0,
            "CIENCIAS NATURALES": 0.0,
            "INGLÉS": 0.0,
            "PUNTAJE GLOBAL (0-500)": 0.0,
        })
    df_init = pd.DataFrame(init_data)

    st.markdown("##### ✏️ Grilla de Puntajes (Ingresa notas de 0 a 100 por asignatura):")
    st.caption("Si dejas 'PUNTAJE GLOBAL' en 0, el sistema lo calculará automáticamente usando la fórmula ponderada ICFES (Base 500).")

    edited_df = st.data_editor(
        df_init,
        disabled=["ESTUDIANTE"],
        column_config={
            "ESTUDIANTE": st.column_config.TextColumn("Estudiante", width="large"),
            "LECTURA CRÍTICA": st.column_config.NumberColumn("Lectura Crítica (0-100)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
            "MATEMÁTICAS": st.column_config.NumberColumn("Matemáticas (0-100)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
            "SOCIALES Y CIUDADANAS": st.column_config.NumberColumn("Sociales (0-100)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
            "CIENCIAS NATURALES": st.column_config.NumberColumn("Ciencias (0-100)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
            "INGLÉS": st.column_config.NumberColumn("Inglés (0-100)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
            "PUNTAJE GLOBAL (0-500)": st.column_config.NumberColumn("Puntaje Global (Opcional)", min_value=0.0, max_value=500.0, step=1.0, format="%.1f"),
        },
        hide_index=True,
        use_container_width=True,
        key=f"grid_sim_{promocion_id}"
    )

    if st.button("💾 Guardar Simulacro en Supabase", type="primary", use_container_width=True):
        if not nombre_simulacro or not nombre_simulacro.strip():
            st.error("⚠️ Debes ingresar un nombre válido para el simulacro.")
        else:
            with st.spinner("Guardando simulacro, aplicando fórmulas ICFES y calculando insights..."):
                ok, mensaje, _ = save_manual_simulacro_grid(
                    nombre=nombre_simulacro.strip(),
                    promocion_id=promocion_id,
                    df_editor=edited_df,
                    usuario=user_email
                )
            if ok:
                st.success(mensaje)
                st.balloons()
                st.rerun()
            else:
                st.error(mensaje)

    # 3. Estado de Simulacros Registrados
    st.markdown("---")
    st.markdown("### 📋 Simulacros Registrados en esta Promoción")
    metadatos, data_map, errores = load_all_simulacros(promocion_id)
    simulacros = ordenar_simulacros(data_map)

    if errores:
        st.warning("⚠️ Se detectaron algunas observaciones en los simulacros cargados.")

    estado_df = pd.DataFrame(
        [
            {
                "Simulacro": sim["nombre"],
                "Estado": sim["meta"].get("estado", "ready"),
                "Origen": sim["meta"].get("origen", "manual"),
                "Creado por": sim["meta"].get("creado_por", "-"),
                "Fecha": sim["meta"].get("creado_en", ""),
            }
            for sim in simulacros
        ]
    )
    if not estado_df.empty:
        st.dataframe(estado_df, hide_index=True, use_container_width=True)
    else:
        st.info("Aún no hay simulacros guardados para esta promoción.")
