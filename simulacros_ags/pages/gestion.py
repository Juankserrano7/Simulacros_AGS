from io import BytesIO

import pandas as pd
import streamlit as st

from ..auth import get_user_role
from ..config import MAX_UPLOAD_MB
from ..data import generate_template_bytes, ingest_simulacro_excel, load_all_simulacros, ordenar_simulacros


def render(user_email: str):
    if get_user_role(user_email) != "admin":
        st.error("No tienes permisos para cargar nuevos simulacros.")
        st.stop()

    st.markdown("<h1 class='header-title'>📤 Cargar nuevo simulacro</h1>", unsafe_allow_html=True)
    st.markdown(
        """
    Usa la plantilla estandarizada para evitar errores de formato. El sistema validará columnas básicas, guardará el archivo
    y recalculará métricas y recomendaciones de forma automática.
    """
    )

    plantilla_bytes = generate_template_bytes()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.download_button(
            "📥 Descargar plantilla Excel",
            data=plantilla_bytes,
            file_name="plantilla_simulacro.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col2:
        st.info(f"Límite de archivo: {MAX_UPLOAD_MB} MB. Incluye columnas: ESTUDIANTE, GRADO, materias y PROMEDIO PONDERADO.")


    with st.form("form_cargar_simulacro"):
        nombre = st.text_input("Nombre del simulacro", placeholder="Ej: Simulacro Octubre")
        archivo = st.file_uploader("Selecciona el Excel del simulacro", type=["xlsx", "xls"])
        procesar = st.form_submit_button("Subir y procesar", width="stretch")

    if procesar:
        if not archivo:
            st.error("Debes adjuntar un archivo en formato Excel.")
        else:
            buffer = BytesIO(archivo.getbuffer())
            with st.spinner("Procesando archivo, validando columnas y generando insights..."):
                ok, mensaje, registro = ingest_simulacro_excel(nombre, buffer, user_email)
            if ok:
                st.success(mensaje)
                st.balloons()
                st.rerun()
            else:
                st.error(mensaje)

    st.markdown("---")
    st.markdown("### Estado de simulacros")
    metadatos, data_map, errores = load_all_simulacros(st.session_state.get("promocion_activa_id"))

    simulacros = ordenar_simulacros(data_map)
    if errores:
        st.warning("⚠️ Hay archivos con problemas de formato o lectura. Revisa el detalle debajo.")
    estado_df = pd.DataFrame(
        [
            {
                "Simulacro": sim["nombre"],
                "Estado": sim["meta"].get("estado", "desconocido"),
                "Origen": sim["meta"].get("origen", "-"),
                "Creado por": sim["meta"].get("creado_por", "-"),
                "Fecha": sim["meta"].get("creado_en", ""),
                "Errores": "; ".join(sim["meta"].get("errores", []) or []),
            }
            for sim in simulacros
        ]
    )
    st.dataframe(estado_df, hide_index=True, width="stretch")
    if errores:
        st.write("Detalle de errores encontrados:")
        for err in errores:
            st.write(f"- {err}")
