import streamlit as st

from simulacros_ags.auth import format_name_from_email, load_auth_users, verify_credentials
from simulacros_ags.config import MATERIAS
from simulacros_ags.data import load_datasets
from simulacros_ags.pages import (
    analisis_individual,
    avance,
    comparacion,
    estadisticas_detalladas,
    inicio,
    rankings,
    reporte_general,
)
from simulacros_ags.styles import inject_base_styles


st.set_page_config(
    page_title="Dashboard Simulacros PreIcfes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_base_styles()

# --- Autenticación ---
usuarios_auth = load_auth_users()
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if not usuarios_auth:
    st.stop()

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
                "📧 Correo institucional",
                placeholder="nombre.apellido@aspaen.edu.co",
                label_visibility="visible",
            ).strip().lower()
            password_input = st.text_input(
                "🔒 Contraseña",
                type="password",
                placeholder="••••••••••",
                label_visibility="visible",
            )
            st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
            login = st.form_submit_button("🚀 Ingresar al panel", use_container_width=True, type="primary")

        if login:
            if verify_credentials(email_input, password_input, usuarios_auth):
                st.session_state.authenticated = True
                st.session_state.user_email = email_input
                st.success("✅ Ingreso exitoso. Redirigiendo...")
                st.rerun()
            else:
                st.error("❌ Correo o contraseña inválidos. Por favor, intenta nuevamente.")

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

# --- Datos base ---
hp1, hp2, prep = load_datasets()
if hp1 is None or hp2 is None or prep is None:
    st.stop()

materias = MATERIAS
simulacros_map = {"Helmer Pardo 1": hp1, "Helmer Pardo 2": hp2, "AVANCEMOS": prep}

# --- Sidebar ---
with st.sidebar:
    st.sidebar.image("Logo.png", width="stretch")
    st.markdown(
        """
    <div style='text-align: center; padding: 1.5rem 0; margin-bottom: 1rem;'>
        <h2 style='color: white; font-weight: 800; font-size: 1.8rem; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
            📊 PreIcfes Dashboard
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
            <div class='sidebar-user-name'>{nombre_usuario}</div>
            <div class='sidebar-user-email'>{st.session_state.user_email}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Cerrar sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_email = ""
        st.rerun()

    st.markdown("<hr style='margin: 1rem 0; border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    st.markdown("### 🧭 NAVEGACIÓN")
    pagina = st.radio(
        "Navegación",
        [
            "🏠 Inicio",
            "🎖️ Rankings",
            "📊 Reporte General",
            "🔄 Comparación Simulacros",
            "👤 Análisis Individual",
            "📈 Avance",
            "📉 Estadísticas Detalladas",
        ],
        label_visibility="collapsed",
    )

    st.markdown("<hr style='margin: 1.5rem 0; border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    st.markdown("### 🎯 FILTROS")
    simulacro_seleccionado = st.selectbox("📋 Simulacro Activo", list(simulacros_map.keys()))

    st.markdown("<hr style='margin: 1.5rem 0; border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    st.markdown(
        """
    <div class='sidebar-footer'>
        <div style='margin-bottom: 1rem;'>
            <span style='font-size: 2rem;'>🎓</span>
        </div>
        <h4 style='color: white; font-weight: 700; font-size: 1rem; margin-bottom: 0.5rem;'>
            GRADO 11
        </h4>
        <p style='color: rgba(255,255,255,0.7); font-size: 0.85rem; margin: 0;'>
            Período 2025/2026
        </p>
        <div style='margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.1);'>
            <p style='color: rgba(255,255,255,0.6); font-size: 0.75rem; margin: 0;'>
                Sistema de Evaluación<br>y Seguimiento Académico
            </p>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    with st.expander("🔍 Diagnóstico de Datos"):
        st.write(f"**HP1:** {len(hp1)} estudiantes")
        st.write(f"**HP2:** {len(hp2)} estudiantes")
        st.write(f"**AVANCEMOS:** {len(prep)} estudiantes")

datos_actual = simulacros_map[simulacro_seleccionado]

page_handlers = {
    "🏠 Inicio": lambda: inicio.render(hp1, hp2, prep, materias),
    "🎖️ Rankings": lambda: rankings.render(hp1, hp2, prep, materias, simulacros_map),
    "📊 Reporte General": lambda: reporte_general.render(datos_actual, simulacro_seleccionado, materias),
    "🔄 Comparación Simulacros": lambda: comparacion.render(hp1, hp2, prep, materias),
    "👤 Análisis Individual": lambda: analisis_individual.render(datos_actual, materias),
    "📈 Avance": lambda: avance.render(hp1, hp2, prep, materias),
    "📉 Estadísticas Detalladas": lambda: estadisticas_detalladas.render(hp1, hp2, prep, materias, simulacro_seleccionado, simulacros_map),
}

page_handlers.get(pagina, lambda: None)()

st.markdown("---")
st.markdown(
    """
<div style='text-align: center; color: #6c757d; padding: 2rem;'>
    <p style='font-size: 0.9rem;'>
        <strong> Dashboard de Análisis de Simulacros PreIcfes</strong><br>
        Sistema de Evaluación y Seguimiento Académico - Grado 11<br>
        DIN HS JKS SSO Desarrallado con Streamlit, Pandas, Plotly y NumPy
    </p>
</div>
""",
    unsafe_allow_html=True,
)
