import html
import time
import pandas as pd
import streamlit as st

from simulacros_ags.auth import format_name_from_email, get_user_role, load_auth_users, verify_credentials
from simulacros_ags.config import MATERIAS
from simulacros_ags.data import load_all_simulacros, ordenar_simulacros
from simulacros_ags.promociones import get_user_promotions
from simulacros_ags.pages import (
    admin,
    analisis_individual,
    avance,
    comparacion,
    estadisticas_detalladas,
    gestion,
    inicio,
    rankings,
    reporte_general,
    resultados_reales,
)
from simulacros_ags.styles import inject_base_styles


st.set_page_config(
    page_title="Dashboard Simulacros PreIcfes",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_base_styles()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "login_attempts" not in st.session_state:
    st.session_state.login_attempts = 0
if "lockout_until" not in st.session_state:
    st.session_state.lockout_until = 0

# --- Autenticación ---
usuarios_auth = load_auth_users()

if not st.session_state.authenticated:
    st.markdown(
        """
        <style>
            .stApp { background: #020c1d !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class='login-hero' style='margin-bottom: 2.5rem;'>
            <h1>PreIcfes AGS</h1>
            <p>Conecta con el tablero de simulacros para monitorear el progreso académico en tiempo real.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, col_login, _ = st.columns([1, 1.1, 1])
    with col_login:
        with st.form("login_profesores"):
            email_input = st.text_input(
                "Correo institucional",
                placeholder="nombre.apellido@aspaen.edu.co",
                label_visibility="visible",
            ).strip().lower()
            password_input = st.text_input(
                "Contraseña",
                type="password",
                placeholder="••••••••••",
                label_visibility="visible",
            )
            st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
            login = st.form_submit_button("Ingresar al panel", use_container_width=True, type="primary")

        if login:
            now_ts = time.time()
            if st.session_state.lockout_until > now_ts:
                wait_sec = int(st.session_state.lockout_until - now_ts)
                st.error(f"Demasiados intentos fallidos. Por seguridad, espera {wait_sec} segundos antes de reintentar.")
            else:
                if verify_credentials(email_input, password_input, usuarios_auth):
                    st.session_state.authenticated = True
                    st.session_state.user_email = email_input
                    st.session_state.login_attempts = 0
                    st.session_state.lockout_until = 0
                    st.success("Ingreso exitoso. Redirigiendo...")
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    if st.session_state.login_attempts >= 5:
                        st.session_state.lockout_until = now_ts + 30
                        st.error("Acceso bloqueado temporalmente por 30 segundos debido a 5 intentos fallidos.")
                    else:
                        st.error(f"Correo o contraseña inválidos. Intento {st.session_state.login_attempts} de 5.")

        st.markdown(
            """
            <div style='text-align: center; margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid rgba(255,255,255,0.1);'>
                <p style='color: #d1d5db; font-size: 0.9rem;'>
                    ¿Problemas para ingresar?<br>
                    Contacta al Director Integral:<br>
                    <a href='mailto:juan.serrano@aspaen.edu.co' 
                       style='color: #9fa8ff; text-decoration: none; font-weight: 600;'>
                        juan.serrano@aspaen.edu.co
                    </a>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.stop()

# --- Consultar Promociones Autorizadas ---
promociones_usuario = get_user_promotions(st.session_state.user_email)
if not promociones_usuario:
    st.error("No tienes promociones asignadas. Contacta al administrador para habilitar tu acceso.")
    st.stop()

promos_by_name = {p["nombre"]: p for p in promociones_usuario}

# --- Sidebar ---
with st.sidebar:
    st.sidebar.image("Logo.png", width="stretch")
    st.markdown(
        """
    <div style='text-align: center; padding: 1.5rem 0; margin-bottom: 1rem;'>
        <h2 style='color: white; font-weight: 800; font-size: 1.8rem; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
            PreIcfes Dashboard
        </h2>
        <p style='color: rgba(255,255,255,0.8); font-size: 0.85rem; margin-top: 0.5rem; letter-spacing: 1px;'>
            SISTEMA DE ANÁLISIS
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )
    nombre_usuario = format_name_from_email(st.session_state.user_email)
    st.markdown(
        f"""
        <div class='sidebar-user-card'>
            <div class='sidebar-user-name'>{html.escape(str(nombre_usuario or "Docente"))}</div>
            <div class='sidebar-user-email'>{html.escape(str(st.session_state.user_email or ""))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Cerrar sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_email = ""
        st.rerun()
    if st.sidebar.button("Sincronizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("<hr style='margin: 1.5rem 0; border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    st.markdown("### SELECCIÓN DE PROMOCIÓN")
    nombre_promo_sel = st.selectbox("Promoción Activa", list(promos_by_name.keys()), index=0)
    if nombre_promo_sel and nombre_promo_sel in promos_by_name:
        promo_activa = promos_by_name[nombre_promo_sel]
    else:
        promo_activa = list(promos_by_name.values())[0] if promos_by_name else {"id": "", "nombre": "Sin Promoción"}
    
    st.session_state.promocion_activa_id = promo_activa["id"]
    st.session_state.promocion_activa_nombre = promo_activa["nombre"]

    # --- Rol de Usuario ---
    user_role = get_user_role(st.session_state.user_email)

    st.markdown("<hr style='margin: 1rem 0; border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    st.markdown("### NAVEGACIÓN")
    opciones_paginas = [
        "Inicio",
        "Rankings",
        "Reporte General",
        "Comparación Simulacros",
        "Análisis Individual",
        "Avance",
        "Estadísticas Detalladas",
        "Resultados ICFES Real",
    ]
    if user_role == "admin":
        opciones_paginas.append("Panel de Administración")
        opciones_paginas.append("Gestión de Simulacros")

    pagina = st.radio("Navegación", opciones_paginas, label_visibility="collapsed")

# --- Cargar datos de la promoción seleccionada ---
metadatos, data_map, errores_carga = load_all_simulacros(st.session_state.promocion_activa_id)
simulacros = ordenar_simulacros(data_map)

if not simulacros:
    st.warning(f"La promoción '{promo_activa['nombre']}' no tiene simulacros registrados aún.")
    if user_role == "admin":
        st.info("Puedes subir simulacros desde la sección 'Gestión de Simulacros'.")
    if pagina not in ["Gestión de Simulacros", "Panel de Administración", "Resultados ICFES Real"]:
        st.stop()
    simulacro_por_nombre = {}
    opciones_simulacro = []
    datos_actual = pd.DataFrame()
    sim_actual_obj = {}
else:
    simulacro_por_nombre = {sim["nombre"]: sim for sim in simulacros}
    opciones_simulacro = list(simulacro_por_nombre.keys())

with st.sidebar:
    st.markdown("<hr style='margin: 1.5rem 0; border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    st.markdown("### SIMULACRO")
    if opciones_simulacro:
        simulacro_seleccionado = st.selectbox("Simulacro Activo", opciones_simulacro, index=len(opciones_simulacro) - 1)
        datos_actual = simulacro_por_nombre[simulacro_seleccionado]["df"]
        sim_actual_obj = simulacro_por_nombre[simulacro_seleccionado]
    else:
        simulacro_seleccionado = None
        datos_actual = pd.DataFrame()
        sim_actual_obj = {}

    with st.expander("Diagnóstico de Datos"):
        for sim in simulacros:
            st.write(f"**{sim['nombre']}:** {len(sim['df'])} estudiantes")
        if errores_carga:
            st.warning("Problemas detectados en algunos datos.")

if opciones_simulacro and simulacro_seleccionado in simulacro_por_nombre:
    datos_actual = simulacro_por_nombre[simulacro_seleccionado]["df"]
    sim_actual_obj = simulacro_por_nombre[simulacro_seleccionado]

page_handlers = {
    "Inicio": lambda: inicio.render(simulacros, MATERIAS),
    "Rankings": lambda: rankings.render(simulacros, MATERIAS),
    "Reporte General": lambda: reporte_general.render(datos_actual, simulacro_seleccionado, MATERIAS),
    "Comparación Simulacros": lambda: comparacion.render(simulacros, MATERIAS),
    "Análisis Individual": lambda: analisis_individual.render(datos_actual, MATERIAS),
    "Avance": lambda: avance.render(simulacros, MATERIAS),
    "Estadísticas Detalladas": lambda: estadisticas_detalladas.render(simulacros, sim_actual_obj, MATERIAS),
    "Resultados ICFES Real": lambda: resultados_reales.render(st.session_state.user_email),
}

if user_role == "admin":
    page_handlers["Panel de Administración"] = lambda: admin.render(st.session_state.user_email)
    page_handlers["Gestión de Simulacros"] = lambda: gestion.render(st.session_state.user_email)

page_handlers.get(pagina, lambda: None)()

st.markdown("---")
