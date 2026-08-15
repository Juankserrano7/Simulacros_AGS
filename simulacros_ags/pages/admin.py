import hashlib
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
from ..config import MATERIAS, PBKDF2_ITERATIONS
from ..core_utils import get_db_connection, record_audit_log
from ..promociones import (
    create_new_promotion,
    get_salones_for_promotion,
    get_user_promotions,
    update_promotion,
)


def registrar_auditoria(usuario_email: str, tipo_accion: str, tabla_afectada: str, registro_id: Optional[str] = None, detalles: Optional[Dict] = None):
    """Registra una acción en la tabla centralizada `auditoria_cambios` en Supabase."""
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            record_audit_log(cur, usuario_email, tipo_accion, tabla_afectada, registro_id, detalles)
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
        Gestión centralizada de usuarios y permisos, creación y edición de promociones y salones (11, 11A, 11B), 
        asignación de salones e inclusión por estudiante, y registro de auditoría de cambios.
        """
    )

    tab_permisos, tab_promociones, tab_estudiantes, tab_inclusion, tab_inicios, tab_auditoria = st.tabs([
        "🔑 Gestión de Permisos",
        "🏫 Gestión de Promociones",
        "👥 Estudiantes por Promoción",
        "♿ Sección Inclusión",
        "🔐 Inicios de Sesión",
        "📋 Historial de Auditoría"
    ])

    # --- Pestaña 1: Gestión de Permisos ---
    with tab_permisos:
        render_permisos_tab(user_email)

    # --- Pestaña 2: Gestión de Promociones ---
    with tab_promociones:
        render_promociones_tab(user_email)

    # --- Pestaña 3: Estudiantes por Promoción ---
    with tab_estudiantes:
        render_estudiantes_tab(user_email)

    # --- Pestaña 4: Sección Inclusión Exclusiva ---
    with tab_inclusion:
        render_inclusion_tab()

    # --- Pestaña 5: Registro de Inicios de Sesión ---
    with tab_inicios:
        render_inicios_sesion_tab()

    # --- Pestaña 6: Historial de Auditoría ---
    with tab_auditoria:
        render_auditoria_tab()


def render_permisos_tab(current_admin_email: str):
    st.markdown("### 🔑 Control de Usuarios, Roles y Accesos a Promociones")
    
    conn = get_db_connection()
    try:
        # Formulario para registrar un nuevo usuario
        with st.expander("➕ Registrar Nuevo Usuario", expanded=False):
            c_new1, c_new2, c_new3 = st.columns([2, 2, 1])
            with c_new1:
                new_user_email = st.text_input("Correo Institucional", placeholder="ejemplo@aspaen.edu.co", key="admin_new_email")
            with c_new2:
                new_user_pwd = st.text_input("Contraseña Inicial", type="password", placeholder="Mínimo 6 caracteres", key="admin_new_pwd")
            with c_new3:
                new_user_rol = st.selectbox("Rol Asignado", ["docente", "admin"], key="admin_new_rol")

            if st.button("🚀 Crear Usuario en Supabase", type="primary", use_container_width=True, key="btn_create_new_user"):
                email_clean = new_user_email.strip().lower()
                if not email_clean or "@" not in email_clean:
                    st.error("⚠️ Ingrese un correo electrónico institucional válido.")
                elif not new_user_pwd or len(new_user_pwd.strip()) < 6:
                    st.error("⚠️ La contraseña debe tener al menos 6 caracteres.")
                else:
                    with conn.cursor() as cur:
                        cur.execute("SELECT email FROM usuarios WHERE LOWER(email) = %s;", (email_clean,))
                        if cur.fetchone():
                            st.error(f"⚠️ El usuario '{email_clean}' ya existe en la base de datos.")
                        else:
                            salt_bytes = os.urandom(16)
                            salt_hex = salt_bytes.hex()
                            pwd_hash = hashlib.pbkdf2_hmac(
                                "sha256", new_user_pwd.strip().encode("utf-8"), salt_bytes, PBKDF2_ITERATIONS
                            ).hex()
                            cur.execute("""
                                INSERT INTO usuarios (email, salt, password_hash, activo, rol, ultima_actualizacion)
                                VALUES (%s, %s, %s, true, %s, now());
                            """, (email_clean, salt_hex, pwd_hash, new_user_rol))
                            conn.commit()
                            registrar_auditoria(
                                usuario_email=current_admin_email,
                                tipo_accion="CREAR_USUARIO",
                                tabla_afectada="usuarios",
                                registro_id=email_clean,
                                detalles={"rol": new_user_rol}
                            )
                            st.success(f"✅ Usuario '{email_clean}' creado exitosamente con rol '{new_user_rol}'.")
                            st.cache_data.clear()
                            st.rerun()

        st.markdown("---")

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
                                cur.execute("DELETE FROM usuario_promocion_acceso WHERE LOWER(usuario_email) = %s;", (target_email,))
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

                st.markdown("---")
                col_sub1, col_sub2 = st.columns(2)
                with col_sub1:
                    st.markdown("#### 🔐 Actualizar Contraseña")
                    new_pwd = st.text_input(
                        "Nueva Contraseña",
                        type="password",
                        placeholder="Mínimo 6 caracteres",
                        key=f"pwd_input_{target_email}"
                    )
                    if st.button("🔑 Cambiar Contraseña", key=f"btn_pwd_{target_email}", type="primary"):
                        if not new_pwd or len(new_pwd.strip()) < 6:
                            st.error("⚠️ La contraseña debe tener al menos 6 caracteres.")
                        else:
                            salt_bytes = os.urandom(16)
                            salt_hex = salt_bytes.hex()
                            pwd_hash = hashlib.pbkdf2_hmac(
                                "sha256", new_pwd.strip().encode("utf-8"), salt_bytes, PBKDF2_ITERATIONS
                            ).hex()

                            with conn.cursor() as cur:
                                cur.execute(
                                    "UPDATE usuarios SET salt = %s, password_hash = %s, ultima_actualizacion = now() WHERE LOWER(email) = %s;",
                                    (salt_hex, pwd_hash, target_email)
                                )
                            conn.commit()
                            registrar_auditoria(
                                usuario_email=current_admin_email,
                                tipo_accion="ACTUALIZACION_CONTRASENA",
                                tabla_afectada="usuarios",
                                registro_id=target_email,
                                detalles={"mensaje": "Contraseña actualizada por administrador"}
                            )
                            st.success(f"✅ Contraseña de {target_email} actualizada exitosamente en Supabase.")
                            st.cache_data.clear()
                            st.rerun()

                with col_sub2:
                    st.markdown("#### 🗑️ Eliminar Usuario")
                    if is_self:
                        st.info("🛡️ No puedes eliminar tu propia cuenta de Administrador.")
                    else:
                        confirm_del_user = st.checkbox(
                            f"Confirmar eliminación del usuario '{target_email}'",
                            key=f"chk_del_user_{target_email}"
                        )
                        if st.button("🗑️ Eliminar Usuario", key=f"btn_del_user_{target_email}", type="primary", disabled=not confirm_del_user):
                            with conn.cursor() as cur:
                                cur.execute("DELETE FROM usuario_promocion_acceso WHERE LOWER(usuario_email) = %s;", (target_email,))
                                cur.execute("DELETE FROM usuarios WHERE LOWER(email) = %s;", (target_email,))
                            conn.commit()
                            registrar_auditoria(
                                usuario_email=current_admin_email,
                                tipo_accion="ELIMINAR_USUARIO",
                                tabla_afectada="usuarios",
                                registro_id=target_email,
                                detalles={"mensaje": "Usuario eliminado por administrador"}
                            )
                            st.success(f"✅ Usuario '{target_email}' eliminado de Supabase.")
                            st.cache_data.clear()
                            st.rerun()

    finally:
        conn.close()


def render_promociones_tab(current_admin_email: str):
    st.markdown("### 🏫 Crear y Editar Promociones / Salones")

    promociones_existentes = get_user_promotions(current_admin_email)

    subtab_crear, subtab_editar = st.tabs(["➕ Crear Nueva Promoción", "✏️ Editar Promoción Existente"])

    # 1. Sub-pestaña Crear Nueva Promoción
    with subtab_crear:
        st.markdown("#### ➕ Registrar Nueva Promoción")
        col_p1, col_p2, col_p3 = st.columns([2, 1, 1])
        with col_p1:
            nuevo_nombre_promo = st.text_input("Nombre de la Promoción", placeholder="Ej: Grado 11 2026/2027", key="new_promo_name")
        with col_p2:
            nuevo_anio_promo = st.number_input("Año de Graduación", min_value=2020, max_value=2035, value=2026, step=1, key="new_promo_year")
        with col_p3:
            num_salones_input = st.number_input("Número de Salones", min_value=1, max_value=10, value=1, step=1, key="new_promo_salones")

        salones_preview = get_salones_for_promotion(num_salones_input)
        st.info(f"💡 Salones que se configurarán: **{', '.join(salones_preview)}**")

        conn = get_db_connection()
        todos_docentes = []
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT email FROM usuarios WHERE activo = true ORDER BY email ASC;")
                    todos_docentes = [r[0] for r in cur.fetchall()]
            finally:
                conn.close()

        docentes_seleccionados = st.multiselect(
            "Asignar Docentes con Acceso Autorizado",
            options=todos_docentes,
            default=[current_admin_email] if current_admin_email in todos_docentes else todos_docentes,
            key="new_promo_docentes"
        )

        if st.button("🚀 Crear Promoción en Supabase", type="primary", use_container_width=True, key="btn_create_promo"):
            if not nuevo_nombre_promo or not nuevo_nombre_promo.strip():
                st.error("⚠️ Ingresa un nombre válido para la promoción.")
            else:
                p_dict = create_new_promotion(
                    nombre=nuevo_nombre_promo.strip(),
                    anio_graduacion=int(nuevo_anio_promo),
                    num_salones=int(num_salones_input),
                    docente_emails=docentes_seleccionados
                )
                if p_dict:
                    registrar_auditoria(
                        usuario_email=current_admin_email,
                        tipo_accion="CREAR_PROMOCION",
                        tabla_afectada="promociones",
                        registro_id=p_dict["id"],
                        detalles={"nombre": p_dict["nombre"], "anio": p_dict["anio_graduacion"], "num_salones": p_dict["num_salones"]}
                    )
                    st.success(f"✅ Promoción '{p_dict['nombre']}' creada exitosamente con salones: {', '.join(salones_preview)}.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Error al crear la promoción en Supabase.")

    # 2. Sub-pestaña Editar Promoción Existente
    with subtab_editar:
        st.markdown("#### ✏️ Modificar Promoción Registrada")
        if not promociones_existentes:
            st.info("No hay promociones registradas.")
        else:
            promo_opts = {f"{p['nombre']} ({p['anio_graduacion']})": p for p in promociones_existentes}
            sel_promo_label = st.selectbox("Selecciona la promoción a editar", list(promo_opts.keys()), key="select_edit_promo")
            target_promo = promo_opts[sel_promo_label]
            t_id = target_promo["id"]

            col_e1, col_e2, col_e3 = st.columns([2, 1, 1])
            with col_e1:
                edit_nombre_p = st.text_input("Nombre de la Promoción", value=target_promo["nombre"], key=f"edit_p_name_{t_id}")
            with col_e2:
                edit_anio_p = st.number_input("Año de Graduación", min_value=2020, max_value=2035, value=int(target_promo["anio_graduacion"]), step=1, key=f"edit_p_year_{t_id}")
            with col_e3:
                edit_salones_p = st.number_input("Número de Salones", min_value=1, max_value=10, value=int(target_promo.get("num_salones", 1)), step=1, key=f"edit_p_salones_{t_id}")

            salones_edit_preview = get_salones_for_promotion(edit_salones_p)
            st.info(f"💡 Salones configurados para esta promoción: **{', '.join(salones_edit_preview)}**")

            if st.button("💾 Guardar Cambios de la Promoción", type="primary", use_container_width=True, key=f"btn_save_p_{t_id}"):
                ok, msg = update_promotion(
                    promo_id=t_id,
                    nombre=edit_nombre_p.strip(),
                    anio_graduacion=int(edit_anio_p),
                    num_salones=int(edit_salones_p)
                )
                if ok:
                    registrar_auditoria(
                        usuario_email=current_admin_email,
                        tipo_accion="EDITAR_PROMOCION",
                        tabla_afectada="promociones",
                        registro_id=t_id,
                        detalles={"nombre": edit_nombre_p.strip(), "anio": int(edit_anio_p), "num_salones": int(edit_salones_p)}
                    )
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)


def render_estudiantes_tab(current_admin_email: str):
    st.markdown("### 👥 Marcación, Salones y Gestión de Estudiantes por Promoción")

    promociones_existentes = get_user_promotions(current_admin_email)
    if not promociones_existentes:
        st.info("No hay promociones registradas.")
        return

    promo_map = {f"{p['nombre']} ({p['anio_graduacion']})": p for p in promociones_existentes}
    sel_promo_label = st.selectbox("Seleccionar Promoción para Gestionar Estudiantes", list(promo_map.keys()), key="admin_sel_promo_est")
    sel_promo_obj = promo_map[sel_promo_label]
    sel_promo_id = sel_promo_obj["id"]
    num_salones = sel_promo_obj.get("num_salones", 1)

    salones_disponibles = get_salones_for_promotion(num_salones)

    conn = get_db_connection()
    try:
        # Formulario para incluir un nuevo estudiante
        with st.expander("➕ Incluir Nuevo Estudiante a esta Promoción", expanded=False):
            col_e1, col_e2, col_e3 = st.columns([3, 1.5, 1])
            with col_e1:
                new_est_name = st.text_input("Nombre Completo del Estudiante", placeholder="Ej: PEREZ LOPEZ JUAN SEBASTIAN", key="admin_new_est_name")
            with col_e2:
                new_est_grado = st.selectbox("Salón / Seccón", salones_disponibles, key="admin_new_est_grado")
            with col_e3:
                st.write("")
                new_est_inc = st.checkbox("♿ Inclusión", key="admin_new_est_inc")

            if st.button("💾 Guardar Estudiante en Supabase", type="primary", use_container_width=True, key="btn_create_new_est"):
                name_clean = new_est_name.strip().upper()
                if not name_clean:
                    st.error("⚠️ Ingrese un nombre de estudiante válido.")
                else:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO estudiantes (nombre, grado, promocion_id, es_inclusion)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (nombre, promocion_id) DO UPDATE SET
                                grado = EXCLUDED.grado,
                                es_inclusion = EXCLUDED.es_inclusion
                            RETURNING id::text;
                        """, (name_clean, new_est_grado.strip(), sel_promo_id, new_est_inc))
                        st_id = cur.fetchone()[0]
                    conn.commit()
                    registrar_auditoria(
                        usuario_email=current_admin_email,
                        tipo_accion="CREAR_ESTUDIANTE",
                        tabla_afectada="estudiantes",
                        registro_id=st_id,
                        detalles={"nombre": name_clean, "promocion_id": sel_promo_id, "grado": new_est_grado, "es_inclusion": new_est_inc}
                    )
                    st.success(f"✅ Estudiante '{name_clean}' incluido exitosamente en el salón '{new_est_grado}'.")
                    st.cache_data.clear()
                    st.rerun()

        st.markdown("---")

        with conn.cursor() as cur:
            cur.execute("""
                SELECT id::text, nombre, grado, es_inclusion 
                FROM estudiantes 
                WHERE promocion_id = %s 
                ORDER BY grado ASC, nombre ASC;
            """, (sel_promo_id,))
            est_rows = cur.fetchall()

        if not est_rows:
            st.info("No se encontraron estudiantes en esta promoción.")
            return

        df_est = pd.DataFrame(est_rows, columns=["id", "nombre", "grado", "es_inclusion"])
        st.write(f"**Estudiantes registrados ({len(df_est)})** | Salones: {', '.join(salones_disponibles)} | Inclusión actuales: {df_est['es_inclusion'].sum()}")

        st.markdown("#### Lista de Estudiantes (Cambiar Salón / Inclusión)")
        for idx, row in df_est.iterrows():
            st_id = row["id"]
            st_name = row["nombre"]
            st_grado_curr = row["grado"] or salones_disponibles[0]
            curr_inc = bool(row["es_inclusion"])

            # Si el grado actual no está en la lista de salones (ej: '11'), agregarlo a opciones para no fallar
            opts_grado = list(salones_disponibles)
            if st_grado_curr not in opts_grado:
                opts_grado.insert(0, st_grado_curr)

            idx_grado = opts_grado.index(st_grado_curr) if st_grado_curr in opts_grado else 0

            col_a, col_b, col_c, col_d, col_e = st.columns([2.5, 1.2, 1, 1.2, 0.8])
            with col_a:
                st.write(f"👤 **{st_name}**")
            with col_b:
                new_grado = st.selectbox("Salón", opts_grado, index=idx_grado, key=f"sel_g_{st_id}")
            with col_c:
                new_inc = st.toggle("♿ Inclusión", value=curr_inc, key=f"tog_inc_{st_id}")
            with col_d:
                if new_grado != st_grado_curr or new_inc != curr_inc:
                    if st.button("Guardar", key=f"btn_inc_{st_id}", type="primary"):
                        with conn.cursor() as cur:
                            cur.execute("UPDATE estudiantes SET es_inclusion = %s, grado = %s WHERE id = %s;", (new_inc, new_grado, st_id))
                        conn.commit()
                        registrar_auditoria(
                            usuario_email=current_admin_email,
                            tipo_accion="CAMBIO_ESTUDIANTE_SALON_INCLUSION",
                            tabla_afectada="estudiantes",
                            registro_id=st_id,
                            detalles={"estudiante_nombre": st_name, "grado_anterior": st_grado_curr, "grado_nuevo": new_grado, "es_inclusion": new_inc}
                        )
                        st.success(f"✅ {st_name}: Salón '{new_grado}', Inclusión: {new_inc}.")
                        st.cache_data.clear()
                        st.rerun()
            with col_e:
                if st.button("🗑️", key=f"btn_del_est_{st_id}", type="secondary", help=f"Eliminar {st_name}"):
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM resultados_simulacro WHERE estudiante_id = %s;", (st_id,))
                        cur.execute("DELETE FROM resultados_icfes_real WHERE estudiante_id = %s;", (st_id,))
                        cur.execute("DELETE FROM estudiantes WHERE id = %s;", (st_id,))
                    conn.commit()
                    registrar_auditoria(
                        usuario_email=current_admin_email,
                        tipo_accion="ELIMINAR_ESTUDIANTE",
                        tabla_afectada="estudiantes",
                        registro_id=st_id,
                        detalles={"estudiante_nombre": st_name, "promocion_id": sel_promo_id}
                    )
                    st.success(f"✅ Estudiante '{st_name}' eliminado.")
                    st.cache_data.clear()
                    st.rerun()

    finally:
        conn.close()


def render_inclusion_tab():
    st.markdown("### ♿ Análisis Exclusivo de Estudiantes en Condición de Inclusión")
    
    conn = get_db_connection()
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
    
    conn = get_db_connection()
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


def render_inicios_sesion_tab():
    st.markdown("### 🔐 Registro de Inicios de Sesión (Últimos 3 Meses)")
    st.caption("ℹ️ Por políticas de almacenamiento optimizado, este registro conserva únicamente los inicios de sesión de los últimos 90 días.")

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Purga automática preventiva de registros mayores a 3 meses
            cur.execute("DELETE FROM inicios_sesion WHERE fecha_hora < NOW() - INTERVAL '3 months';")
            conn.commit()

            # Consultar registros dentro de la ventana de 3 meses
            cur.execute("""
                SELECT fecha_hora, usuario_email, exitoso, detalles
                FROM inicios_sesion
                WHERE fecha_hora >= NOW() - INTERVAL '3 months'
                ORDER BY fecha_hora DESC
                LIMIT 500;
            """)
            rows = cur.fetchall()

        if not rows:
            st.info("No se han registrado inicios de sesión aún en la base de datos.")
            return

        df_logins = pd.DataFrame(rows, columns=["Fecha / Hora", "Correo Institucional", "Éxito", "Detalles"])

        total_logins = len(df_logins)
        exitosos = int((df_logins["Éxito"] == True).sum())
        fallidos = int((df_logins["Éxito"] == False).sum())

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔑 Total Intentos", total_logins)
        with col2:
            st.metric("✅ Inicios Exitosos", exitosos)
        with col3:
            st.metric("⚠️ Intentos Fallidos", fallidos)

        df_logins["Estado"] = df_logins["Éxito"].apply(lambda x: "✅ Éxito" if x else "❌ Fallido")
        df_logins_display = df_logins[["Fecha / Hora", "Correo Institucional", "Estado", "Detalles"]]

        st.dataframe(df_logins_display, hide_index=True, use_container_width=True)
    except Exception as e:
        st.error(f"Error al cargar el registro de inicios de sesión: {e}")
    finally:
        conn.close()
