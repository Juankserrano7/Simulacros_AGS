import html
import time
import pandas as pd
import streamlit as st

from simulacros_ags.auth import format_name_from_email, get_user_role, load_auth_users, load_logo_base64, verify_credentials, registrar_inicio_sesion
from simulacros_ags.config import MATERIAS
from simulacros_ags.data import load_all_simulacros, ordenar_simulacros
from simulacros_ags.promociones import get_user_promotions
from simulacros_ags.pages import (
    admin,
    analisis_individual,
    avance,
    comparacion,
    comparacion_simulacro_promocion,
    estadisticas_detalladas,
    gestion,
    inicio,
    rankings,
    reporte_general,
    resultados_reales,
)
from simulacros_ags.styles import inject_base_styles, load_login_css, load_sidebar_css


st.set_page_config(
    page_title="PreIcfes AGS — Panel docente",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    st.markdown(f"<style>{load_login_css()}</style>", unsafe_allow_html=True)

    logo_b64 = load_logo_base64("Logo.png")
    img_tag = f'<img src="data:image/png;base64,{logo_b64}" alt="Escudo del colegio Saucará Aspaen">' if logo_b64 else '<img src="Logo.png" alt="Escudo del colegio Saucará Aspaen">'

    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.markdown(
            f"""
            <div class="stage">
              <div class="brand">
                {img_tag}
                <h1>PreIcfes AGS</h1>
                <div class="accent-rule"></div>
                <p class="subtitle">Consulta el progreso de tus estudiantes frente a los simulacros en tiempo real.</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_profesores"):
            login_error_msg = None
            now_ts = time.time()
            if st.session_state.lockout_until > now_ts:
                wait_sec = int(st.session_state.lockout_until - now_ts)
                login_error_msg = f"Demasiados intentos fallidos. Espera {wait_sec} segundos antes de reintentar."
            elif st.session_state.get("last_login_failed"):
                if st.session_state.login_attempts >= 5:
                    login_error_msg = "Acceso bloqueado temporalmente por 30 segundos debido a 5 intentos fallidos."
                else:
                    login_error_msg = f"Correo o contraseña inválidos. Intento {st.session_state.login_attempts} de 5."

            if login_error_msg:
                st.markdown(
                    f"""
                    <div class="status">
                        <i class="bi bi-exclamation-triangle-fill"></i>
                        <span>{login_error_msg}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown('<label class="custom-label"><i class="bi bi-envelope"></i> Correo institucional</label>', unsafe_allow_html=True)
            email_input = st.text_input(
                "Correo institucional",
                placeholder="nombre.apellido@aspaen.edu.co",
                label_visibility="collapsed",
                key="login_email_input"
            ).strip().lower()

            st.markdown('<label class="custom-label" style="margin-top: 14px;"><i class="bi bi-shield-lock"></i> Contraseña</label>', unsafe_allow_html=True)
            password_input = st.text_input(
                "Contraseña",
                type="password",
                placeholder="••••••••••",
                label_visibility="collapsed",
                key="login_pwd_input"
            )

            login_submitted = st.form_submit_button("Ingresar al panel ➔", use_container_width=True)

            st.markdown(
                """
                <hr class="divider">
                <p class="helper">
                    ¿Problemas para ingresar?<br>
                    Contacta al Director Integral<br>
                    <a href="mailto:juan.serrano@aspaen.edu.co">juan.serrano@aspaen.edu.co</a>
                </p>
                <br>
                """,
                unsafe_allow_html=True,
            )

        if login_submitted:
            if st.session_state.lockout_until > now_ts:
                st.session_state.last_login_failed = True
                st.rerun()
            else:
                if verify_credentials(email_input, password_input, usuarios_auth):
                    st.session_state.authenticated = True
                    st.session_state.user_email = email_input
                    st.session_state.login_attempts = 0
                    st.session_state.lockout_until = 0
                    st.session_state.last_login_failed = False
                    registrar_inicio_sesion(email_input, exitoso=True, detalles="Inicio de sesión exitoso")
                    st.success("✅ Ingreso exitoso. Redirigiendo...")
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    st.session_state.last_login_failed = True
                    registrar_inicio_sesion(email_input, exitoso=False, detalles=f"Credenciales inválidas (Intento {st.session_state.login_attempts})")
                    if st.session_state.login_attempts >= 5:
                        st.session_state.lockout_until = now_ts + 30
                    st.rerun()
    st.stop()

# --- Post-autenticación (Dashboard Base Styles) ---
inject_base_styles()

# --- Consultar Promociones Autorizadas ---
promociones_usuario = get_user_promotions(st.session_state.user_email)
if not promociones_usuario:
    st.error("🔒 No tienes promociones asignadas. Contacta al administrador para habilitar tu acceso.")
    st.stop()

promos_by_name = {p["nombre"]: p for p in promociones_usuario}

# --- Sidebar ---
with st.sidebar:
    import time
    sidebar_css_code = load_sidebar_css()
    if sidebar_css_code:
        st.markdown(f"<style>/* sidebar_inline_v={time.time()} */\n{sidebar_css_code}</style>", unsafe_allow_html=True)

    logo_b64 = load_logo_base64("Logo.png")
    img_brand = f'<img src="data:image/png;base64,{logo_b64}" alt="Logo Saucará Aspaen">' if logo_b64 else '<img src="Logo.png" alt="Logo Saucará Aspaen">'
    st.markdown(
        f"""
        <div class="sb-brand-block">
          {img_brand}
          <p class="sb-brand-title">PreIcfes AGS</p>
          <p class="sb-brand-caption">Panel de seguimiento académico</p>
        </div>
        <hr class="sb-divider">
        """,
        unsafe_allow_html=True,
    )

    # 3. Selección de Promoción
    st.markdown('<p class="sb-section-label"><i class="bi bi-mortarboard"></i> Promoción activa</p>', unsafe_allow_html=True)
    nombre_promo_sel = st.selectbox("Promoción Activa", list(promos_by_name.keys()), index=0, label_visibility="collapsed")
    if nombre_promo_sel and nombre_promo_sel in promos_by_name:
        promo_activa = promos_by_name[nombre_promo_sel]
    else:
        promo_activa = list(promos_by_name.values())[0] if promos_by_name else {"id": "", "nombre": "Sin Promoción"}
    
    st.session_state.promocion_activa_id = promo_activa["id"]
    st.session_state.promocion_activa_nombre = promo_activa["nombre"]

    metadatos, data_map, errores_carga = load_all_simulacros(st.session_state.promocion_activa_id)
    simulacros = ordenar_simulacros(data_map)
    user_role = get_user_role(st.session_state.user_email)

    if not simulacros:
        simulacro_por_nombre = {}
        opciones_simulacro = []
        datos_actual = pd.DataFrame()
        sim_actual_obj = {}
        simulacro_seleccionado = None
    else:
        simulacro_por_nombre = {sim["nombre"]: sim for sim in simulacros}
        opciones_simulacro = list(simulacro_por_nombre.keys())

    # 4. Simulacro
    st.markdown('<p class="sb-section-label" style="margin-top: 14px;"><i class="bi bi-file-earmark-bar-graph"></i> Simulacro activo</p>', unsafe_allow_html=True)
    if opciones_simulacro:
        simulacro_seleccionado = st.selectbox("Simulacro Activo", opciones_simulacro, index=len(opciones_simulacro) - 1, label_visibility="collapsed")
        datos_actual = simulacro_por_nombre[simulacro_seleccionado]["df"]
        sim_actual_obj = simulacro_por_nombre[simulacro_seleccionado]
    else:
        st.caption("Sin simulacros registrados en esta promoción.")

    st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

    # 5. Navegación
    st.markdown('<p class="sb-section-label"><i class="bi bi-compass"></i> Navegación</p>', unsafe_allow_html=True)
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
        opciones_paginas.append("Comparación Simulacro-Promoción")
        opciones_paginas.append("Panel de Administración")
        opciones_paginas.append("Gestión de Simulacros")

    pagina = st.radio("Navegación", opciones_paginas, label_visibility="collapsed")

    # 6. Usuario / Footer
    nombre_usuario = format_name_from_email(st.session_state.user_email)
    raw_name = (nombre_usuario or "Docente").strip()
    name_parts = raw_name.split()
    if len(name_parts) >= 2:
        initials = (name_parts[0][0] + name_parts[1][0]).upper()
    elif len(name_parts) == 1 and name_parts[0]:
        initials = name_parts[0][:2].upper()
    else:
        initials = "JS"

    st.markdown(
        f"""
        <div class="sb-user-card">
            <div class="sb-avatar">{initials}</div>
            <div class="sb-user-meta">
                <p class="sb-user-name">{html.escape(str(raw_name))}</p>
                <p class="sb-user-email">{html.escape(str(st.session_state.user_email or ""))}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Cerrar sesión", use_container_width=True, key="btn_logout_sidebar"):
        st.session_state.authenticated = False
        st.session_state.user_email = ""
        st.rerun()

    # 7. Sidebar JavaScript Enhancement
    st.components.v1.html(
        """
        <script>
        const doc = window.parent.document;
        function initSidebarJS() {
            const navLabels = doc.querySelectorAll('[data-testid="stSidebar"] [data-testid="stRadio"] label');
            navLabels.forEach(label => {
                label.addEventListener('click', function() {
                    navLabels.forEach(l => l.classList.remove('active'));
                    this.classList.add('active');
                });
            });

            const selectBoxes = doc.querySelectorAll('[data-testid="stSidebar"] [data-baseweb="select"]');
            selectBoxes.forEach(sb => {
                sb.addEventListener('mouseenter', function() {
                    this.style.borderColor = 'rgba(23, 180, 212, 0.45)';
                });
                sb.addEventListener('mouseleave', function() {
                    this.style.borderColor = 'rgba(255, 255, 255, 0.16)';
                });
            });
        }
        if (doc.readyState === 'complete') {
            initSidebarJS();
        } else {
            window.parent.addEventListener('load', initSidebarJS);
        }
        setTimeout(initSidebarJS, 300);
        setTimeout(initSidebarJS, 800);
        </script>
        """,
        height=0,
        width=0,
    )

if not simulacros:
    st.warning(f"La promoción '{promo_activa['nombre']}' no tiene simulacros registrados aún.")
    if user_role == "admin":
        st.info("Puedes subir simulacros desde la sección 'Gestión de Simulacros'.")
    if pagina not in ["Gestión de Simulacros", "Panel de Administración", "Resultados ICFES Real", "Comparación Simulacro-Promoción"]:
        st.stop()

if opciones_simulacro and simulacro_seleccionado in simulacro_por_nombre:
    datos_actual = simulacro_por_nombre[simulacro_seleccionado]["df"]
    sim_actual_obj = simulacro_por_nombre[simulacro_seleccionado]

page_handlers = {
    "Inicio": lambda: inicio.render(simulacros, MATERIAS),
    "Rankings": lambda: rankings.render(simulacros, MATERIAS),
    "Reporte General": lambda: reporte_general.render(datos_actual, simulacro_seleccionado, MATERIAS),
    "Comparación Simulacros": lambda: comparacion.render(simulacros, MATERIAS),
    "Análisis Individual": lambda: analisis_individual.render(datos_actual, MATERIAS),
    "Avance": lambda: avance.render(simulacros, MATERIAS, simulacro_seleccionado),
    "Estadísticas Detalladas": lambda: estadisticas_detalladas.render(simulacros, sim_actual_obj, MATERIAS),
    "Resultados ICFES Real": lambda: resultados_reales.render(st.session_state.user_email),
}

if user_role == "admin":
    page_handlers["Comparación Simulacro-Promoción"] = lambda: comparacion_simulacro_promocion.render(st.session_state.user_email)
    page_handlers["Panel de Administración"] = lambda: admin.render(st.session_state.user_email)
    page_handlers["Gestión de Simulacros"] = lambda: gestion.render(st.session_state.user_email)

page_handlers.get(pagina, lambda: None)()

st.markdown("---")
st.markdown(
    """
<div style='text-align: center; color: #6c757d; padding: 2rem;'>
    <p style='font-size: 0.95rem; line-height: 1.6;'>
        <strong style='font-size: 1.05rem; color: #2e1065;'>📊 Dashboard de Análisis de Simulacros PreIcfes</strong><br>
        <span style='color: #4b5563; font-weight: 500;'>Sistema de Evaluación y Seguimiento Académico</span><br><br>
        <span style='color: #6b7280; font-size: 0.9rem; font-weight: 600; letter-spacing: 0.5px;'>
            Creado y desarrollado por JKS y SSO
        </span>
    </p>
</div>
""",
    unsafe_allow_html=True,
)
