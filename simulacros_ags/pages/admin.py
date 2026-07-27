import json
import os
from typing import Dict, List, Optional
import pandas as pd
import psycopg2
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from ..auth import get_user_role
from ..config import MATERIAS

load_dotenv()


def _get_db_connection():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        st.error("No se encontró la conexión a Supabase (SUPABASE_DB_URL).")
        st.stop()
    return psycopg2.connect(db_url)


def registrar_auditoria(usuario_email: str, tipo_accion: str, tabla_afectada: str, registro_id: Optional[str] = None, detalles: Optional[Dict] = None):
    """Registra una acción en la tabla centralizada `auditoria_cambios` en Supabase."""
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO auditoria_cambios (usuario_email, tipo_accion, tabla_afectada, registro_id, detalles, creado_en)
                VALUES (%s, %s, %s, %s, %s::jsonb, now());
            """, (usuario_email.strip().lower(), tipo_accion, tabla_afectada, registro_id, json.dumps(detalles or {})))
        conn.commit()
    finally:
        conn.close()


def render(user_email: str):
    # Verificación estricta de Rol Administrador en Supabase
    rol_actual = get_user_role(user_email)
    if rol_actual != "admin":
        st.error("🔒 Acceso Denegado. Esta sección es exclusiva para Administradores del Sistema.")
        st.stop()

    st.markdown("<h1 class='header-title'>⚙️ Panel Global de Administración</h1>", unsafe_allow_html=True)
    st.markdown(
        """
        Gestión centralizada de permisos por docente, configuración del flag de inclusión por estudiante, 
        sección exclusiva para análisis de inclusión y registro de auditoría de cambios.
        """
    )

    tab_permisos, tab_estudiantes, tab_inclusion, tab_auditoria = st.tabs([
        "🔑 Gestión de Permisos",
        "👥 Estudiantes por Promoción",
        "♿ Sección Inclusión",
        "📋 Historial de Auditoría"
    ])

    # --- Pestaña 1: Gestión de Permisos ---
    with tab_permisos:
        render_permisos_tab(user_email)

    # --- Pestaña 2: Estudiantes por Promoción (Flag Inclusión) ---
    with tab_estudiantes:
        render_estudiantes_tab(user_email)

    # --- Pestaña 3: Sección Inclusión Exclusiva ---
    with tab_inclusion:
        render_inclusion_tab()

    # --- Pestaña 4: Historial de Auditoría ---
    with tab_auditoria:
        render_auditoria_tab()


def render_permisos_tab(current_admin_email: str):
    st.markdown("### 🔑 Control de Usuarios, Roles y Accesos a Promociones")
    
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            # Consultar todos los usuarios
            cur.execute("SELECT email, rol, activo, ultima_actualizacion FROM usuarios ORDER BY email ASC;")
            usuarios_rows = cur.fetchall()

            # Consultar todas las promociones
            cur.execute("SELECT id::text, nombre, anio_graduacion FROM promociones ORDER BY anio_graduacion DESC;")
            promos_all = cur.fetchall()

            # Consultar accesos actuales
            cur.execute("SELECT usuario_email, promocion_id::text FROM usuario_promocion_acceso;")
            accesos_rows = cur.fetchall()

        # Mapear accesos por email
        user_promos_map = {}
        for em, p_id in accesos_rows:
            user_promos_map.setdefault(em.lower(), set()).add(p_id)

        df_users = pd.DataFrame(usuarios_rows, columns=["email", "rol", "activo", "ultima_actualizacion"])
        
        st.markdown(f"**Total usuarios registrados:** {len(df_users)}")

        for _, urow in df_users.iterrows():
            target_email = urow["email"].lower()
            current_rol = urow["rol"]
            is_self = (target_email == current_admin_email.lower())

            with st.expander(f"👤 {target_email} ({current_rol.upper()}) {' [Tu Cuenta Admin]' if is_self else ''}"):
                c1, c2 = st.columns([1, 2])
                
                with c1:
                    st.write("**Cambio de Rol:**")
                    if is_self:
                        st.info("🛡️ No puedes quitarte el rol de 'admin' a ti mismo para prevenir bloqueos por error.")
                        new_rol = "admin"
                    else:
                        opciones_rol = ["docente", "admin"]
                        idx_rol = opciones_rol.index(current_rol) if current_rol in opciones_rol else 0
                        new_rol = st.selectbox(
                            "Rol de usuario", 
                            opciones_rol, 
                            index=idx_rol, 
                            key=f"rol_sel_{target_email}"
                        )
                        if new_rol != current_rol:
                            if st.button("Guardar Cambios de Rol", key=f"btn_save_rol_{target_email}", type="primary"):
                                with conn.cursor() as cur:
                                    cur.execute("UPDATE usuarios SET rol = %s, ultima_actualizacion = now() WHERE LOWER(email) = %s;", (new_rol, target_email))
                                conn.commit()
                                registrar_auditoria(
                                    usuario_email=current_admin_email,
                                    tipo_accion="CAMBIO_ROL",
                                    tabla_afectada="usuarios",
                                    registro_id=target_email,
                                    detalles={"rol_anterior": current_rol, "rol_nuevo": new_rol}
                                )
                                st.success(f"✅ Rol de {target_email} actualizado a '{new_rol}'.")
                                st.cache_data.clear()
                                st.rerun()

                with c2:
                    st.write("**Permisos de Acceso a Promociones:**")
                    promos_actuales_user = user_promos_map.get(target_email, set())
                    
                    if is_self:
                        st.info("🛡️ Posees acceso total a todas las promociones como Administrador.")
                    else:
                        new_selected_promos = []
                        for p_id, p_nombre, p_anio in promos_all:
                            checked = (p_id in promos_actuales_user)
                            is_checked = st.checkbox(
                                f"{p_nombre} ({p_anio})", 
                                value=checked, 
                                key=f"chk_p_{target_email}_{p_id}"
                            )
                            if is_checked:
                                new_selected_promos.append(p_id)

                        if st.button("Actualizar Accesos a Promociones", key=f"btn_save_promos_{target_email}"):
                            with conn.cursor() as cur:
                                # Eliminar accesos actuales
                                cur.execute("DELETE FROM usuario_promocion_acceso WHERE LOWER(usuario_email) = %s;", (target_email,))
                                # Insertar nuevos accesos
                                for pid in new_selected_promos:
                                    cur.execute("INSERT INTO usuario_promocion_acceso (usuario_email, promocion_id) VALUES (%s, %s);", (target_email, pid))
                            conn.commit()
                            registrar_auditoria(
                                usuario_email=current_admin_email,
                                tipo_accion="CAMBIO_PERMISO_PROMOCION",
                                tabla_afectada="usuario_promocion_acceso",
                                registro_id=target_email,
                                detalles={"promociones_asignadas_count": len(new_selected_promos)}
                            )
                            st.success(f"✅ Accesos de {target_email} actualizados correctamente.")
                            st.cache_data.clear()
                            st.rerun()

    finally:
        conn.close()


def render_estudiantes_tab(current_admin_email: str):
    st.markdown("### 👥 Marcación y Gestión de Estudiantes por Promoción")
    
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id::text, nombre, anio_graduacion FROM promociones ORDER BY anio_graduacion DESC;")
            promos_all = cur.fetchall()

        if not promos_all:
            st.info("No hay promociones registradas.")
            return

        promo_map = {f"{p[1]} ({p[2]})": p[0] for p in promos_all}
        sel_promo_name = st.selectbox("Seleccionar Promoción para Gestionar Estudiantes", list(promo_map.keys()), key="admin_sel_promo_est")
        sel_promo_id = promo_map[sel_promo_name]

        with conn.cursor() as cur:
            cur.execute("""
                SELECT id::text, nombre, grado, es_inclusion 
                FROM estudiantes 
                WHERE promocion_id = %s 
                ORDER BY nombre ASC;
            """, (sel_promo_id,))
            est_rows = cur.fetchall()

        if not est_rows:
            st.info("No se encontraron estudiantes en esta promoción.")
            return

        df_est = pd.DataFrame(est_rows, columns=["id", "nombre", "grado", "es_inclusion"])
        st.write(f"**Estudiantes registrados:** {len(df_est)} (Inclusión actuales: {df_est['es_inclusion'].sum()})")

        st.markdown("#### Lista de Estudiantes (Cambiar estado de Inclusión)")
        for idx, row in df_est.iterrows():
            st_id = row["id"]
            st_name = row["nombre"]
            st_grado = row["grado"] or "-"
            curr_inc = bool(row["es_inclusion"])

            col_a, col_b, col_c = st.columns([3, 1, 2])
            with col_a:
                st.write(f"👤 **{st_name}** (Grado: {st_grado})")
            with col_b:
                new_inc = st.toggle("♿ Inclusión", value=curr_inc, key=f"tog_inc_{st_id}")
            with col_c:
                if new_inc != curr_inc:
                    if st.button("Guardar Cambios", key=f"btn_inc_{st_id}", type="primary"):
                        with conn.cursor() as cur:
                            cur.execute("UPDATE estudiantes SET es_inclusion = %s WHERE id = %s;", (new_inc, st_id))
                        conn.commit()
                        registrar_auditoria(
                            usuario_email=current_admin_email,
                            tipo_accion="TOGGLE_INCLUSION",
                            tabla_afectada="estudiantes",
                            registro_id=st_id,
                            detalles={"estudiante_nombre": st_name, "es_inclusion_anterior": curr_inc, "es_inclusion_nuevo": new_inc}
                        )
                        st.success(f"✅ Estado de inclusión de {st_name} actualizado a {new_inc}.")
                        st.cache_data.clear()
                        st.rerun()

    finally:
        conn.close()


def render_inclusion_tab():
    st.markdown("### ♿ Análisis Exclusivo de Estudiantes en Condición de Inclusión")
    
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id::text, nombre, anio_graduacion FROM promociones ORDER BY anio_graduacion DESC;")
            promos_all = cur.fetchall()

        if not promos_all:
            st.info("No hay promociones disponibles.")
            return

        promo_map = {f"{p[1]} ({p[2]})": p[0] for p in promos_all}
        sel_promo_name = st.selectbox("Seleccionar Promoción", list(promo_map.keys()), key="admin_sel_promo_inc_view")
        sel_promo_id = promo_map[sel_promo_name]

        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    e.id::text,
                    e.nombre,
                    e.grado,
                    s.nombre AS simulacro_nombre,
                    rs.lectura_critica,
                    rs.matematicas,
                    rs.sociales_ciudadanas,
                    rs.ciencias_naturales,
                    rs.ingles,
                    rs.promedio_ponderado
                FROM estudiantes e
                LEFT JOIN resultados_simulacro rs ON e.id = rs.estudiante_id
                LEFT JOIN simulacros s ON rs.simulacro_id = s.id
                WHERE e.promocion_id = %s AND e.es_inclusion = true
                ORDER BY e.nombre ASC, s.creado_en ASC;
            """, (sel_promo_id,))
            rows = cur.fetchall()

        if not rows:
            st.info("ℹ️ No hay estudiantes marcados en condición de inclusión para esta promoción.")
            return

        df_inc = pd.DataFrame(rows, columns=[
            "estudiante_id", "nombre", "grado", "simulacro", 
            "LECTURA CRÍTICA", "MATEMÁTICAS", "SOCIALES Y CIUDADANAS", 
            "CIENCIAS NATURALES", "INGLÉS", "PROMEDIO PONDERADO"
        ])

        for col in ["LECTURA CRÍTICA", "MATEMÁTICAS", "SOCIALES Y CIUDADANAS", "CIENCIAS NATURALES", "INGLÉS", "PROMEDIO PONDERADO"]:
            df_inc[col] = pd.to_numeric(df_inc[col], errors="coerce")

        unique_students = df_inc["nombre"].unique()
        st.success(f"♿ Se encontraron {len(unique_students)} estudiantes en condición de inclusión.")

        st.dataframe(df_inc[["nombre", "grado", "simulacro", "PROMEDIO PONDERADO"] + MATERIAS], use_container_width=True)

    finally:
        conn.close()


def render_auditoria_tab():
    st.markdown("### 📋 Registro Histórico de Auditoría de Cambios")
    
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT creado_en, usuario_email, tipo_accion, tabla_afectada, registro_id, detalles
                FROM auditoria_cambios
                ORDER BY creado_en DESC
                LIMIT 100;
            """)
            rows = cur.fetchall()

        if not rows:
            st.info("No se han registrado acciones de auditoría aún.")
            return

        df_audit = pd.DataFrame(rows, columns=["Fecha / Hora", "Usuario", "Acción", "Tabla Afectada", "ID Registro", "Detalles"])
        df_audit["Detalles"] = df_audit["Detalles"].apply(lambda d: json.dumps(d) if isinstance(d, dict) else str(d))
        st.dataframe(df_audit, hide_index=True, use_container_width=True)

    finally:
        conn.close()
