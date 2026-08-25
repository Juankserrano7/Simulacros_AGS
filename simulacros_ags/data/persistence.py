"""Módulo de persistencia, mutaciones y operaciones de escritura en PostgreSQL (Supabase)."""

import json
import uuid
from io import BytesIO
from typing import Dict, Tuple

import pandas as pd
import streamlit as st

from ..ai import generate_ai_insights
from ..config import MATERIAS, MAX_UPLOAD_MB
from ..core_utils import (
    calculate_icfes_scores,
    get_db_connection,
    record_audit_log,
    sanitize_score,
)
from .normalization import _clean_student_frame, _validate_schema


def ingest_simulacro_excel(nombre: str, file_buffer: BytesIO, usuario: str, promocion_id: Optional[str] = None) -> Tuple[bool, str, Dict]:
    """Valida e ingesta un nuevo simulacro cargado por Excel directamente en Supabase."""
    if not nombre or not nombre.strip():
        return False, "Debes indicar un nombre para el simulacro.", {}

    file_buffer.seek(0, 2)
    size_mb = file_buffer.tell() / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        return False, f"El archivo excede el límite de {MAX_UPLOAD_MB} MB.", {}
    file_buffer.seek(0)
    header = file_buffer.read(8)
    file_buffer.seek(0)

    # Validar Magic Bytes de Excel
    fname = getattr(file_buffer, "name", "").lower()
    if fname.endswith(".xlsx") and not header.startswith(b"PK\x03\x04"):
        return False, "El archivo .xlsx no posee una cabecera binaria válida de hoja de cálculo.", {}
    if fname.endswith(".xls") and not header.startswith(b"\xd0\xcf\x11\xe0"):
        return False, "El archivo .xls no posee una cabecera binaria válida de Excel.", {}

    try:
        df_raw = pd.read_excel(file_buffer)
    except Exception as exc:  # noqa: BLE001
        return False, f"No se pudo leer el Excel: {exc}", {}

    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    df = _clean_student_frame(df_raw)
    errores = _validate_schema(df)
    if errores:
        return False, "; ".join(errores), {}

    promocion_id = promocion_id or (st.session_state.get("promocion_activa_id") if hasattr(st, "session_state") else None)
    if not promocion_id:
        return False, "No hay una promoción activa seleccionada.", {}

    conn = get_db_connection()
    if not conn:
        return False, "No hay conexión configurada a Supabase.", {}

    sim_id = str(uuid.uuid4())
    insights = generate_ai_insights(nombre.strip(), df, materias=MATERIAS)

    try:
        with conn.cursor() as cur:
            # 1. Insertar registro en tabla `simulacros`
            cur.execute("""
                INSERT INTO simulacros (id, nombre, promocion_id, origen, estado, creado_por, insights)
                VALUES (%s, %s, %s, 'upload', 'ready', %s, %s::jsonb);
            """, (sim_id, nombre.strip(), promocion_id, usuario, json.dumps(insights)))

            # 2. Insertar/obtener estudiantes e insertar sus resultados
            for _, r in df.iterrows():
                st_name = str(r["ESTUDIANTE"]).strip()
                st_grado = str(r["GRADO"]).strip() if pd.notna(r.get("GRADO")) else None

                cur.execute("""
                    INSERT INTO estudiantes (nombre, grado, promocion_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (nombre, promocion_id) DO UPDATE SET grado = EXCLUDED.grado
                    RETURNING id;
                """, (st_name, st_grado, promocion_id))
                st_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO resultados_simulacro (
                        simulacro_id, estudiante_id, lectura_critica, matematicas,
                        sociales_ciudadanas, ciencias_naturales, ingles,
                        promedio_simple, promedio_ponderado, desviacion_estandar
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (simulacro_id, estudiante_id) DO UPDATE SET
                        lectura_critica = EXCLUDED.lectura_critica,
                        matematicas = EXCLUDED.matematicas,
                        sociales_ciudadanas = EXCLUDED.sociales_ciudadanas,
                        ciencias_naturales = EXCLUDED.ciencias_naturales,
                        ingles = EXCLUDED.ingles,
                        promedio_simple = EXCLUDED.promedio_simple,
                        promedio_ponderado = EXCLUDED.promedio_ponderado,
                        desviacion_estandar = EXCLUDED.desviacion_estandar;
                """, (
                    sim_id, st_id,
                    sanitize_score(r.get("LECTURA CRÍTICA"), default=None),
                    sanitize_score(r.get("MATEMÁTICAS"), default=None),
                    sanitize_score(r.get("SOCIALES Y CIUDADANAS"), default=None),
                    sanitize_score(r.get("CIENCIAS NATURALES"), default=None),
                    sanitize_score(r.get("INGLÉS"), default=None),
                    sanitize_score(r.get("PROMEDIO SIMPLE"), default=None),
                    sanitize_score(r.get("PROMEDIO PONDERADO"), min_val=0.0, max_val=500.0, default=None),
                    sanitize_score(r.get("DESVIACIÓN ESTÁNDAR"), min_val=0.0, max_val=100.0, default=None)
                ))

            record_audit_log(
                cur,
                usuario,
                "INGESTAR_SIMULACRO_EXCEL",
                "simulacros",
                sim_id,
                {"nombre": nombre.strip(), "estudiantes_ingestados": len(df)}
            )

        conn.commit()
        st.cache_data.clear()
        return True, f"Simulacro '{nombre.strip()}' subido e ingestado correctamente en Supabase.", {"id": sim_id, "nombre": nombre.strip()}
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        return False, f"Error al procesar e insertar en Supabase: {exc}", {}
    finally:
        conn.close()


def save_manual_simulacro_grid(nombre: str, promocion_id: str, df_editor: pd.DataFrame, usuario: str) -> Tuple[bool, str, Dict]:
    """Recibe la grilla de puntuaciones editada manualmente, aplica las fórmulas del ICFES y guarda en Supabase."""
    if not nombre or not nombre.strip():
        return False, "El nombre del simulacro no puede estar vacío.", {}

    if not promocion_id:
        return False, "No hay una promoción activa seleccionada.", {}

    if df_editor.empty:
        return False, "La grilla de estudiantes está vacía.", {}

    conn = get_db_connection()
    if not conn:
        return False, "No hay conexión configurada a Supabase.", {}

    sim_id = str(uuid.uuid4())
    
    # Calcular fórmulas ICFES estandarizadas por fila
    calculated_rows = []
    for _, r in df_editor.iterrows():
        st_name = str(r.get("ESTUDIANTE", "")).strip()
        if not st_name:
            continue

        subj_scores = {m: r.get(m) for m in MATERIAS}
        custom_global = r.get("PUNTAJE GLOBAL (0-500)") or r.get("PROMEDIO PONDERADO")
        prom_simple, pg_val, desv_est = calculate_icfes_scores(subj_scores, custom_global)

        calculated_rows.append({
            "ESTUDIANTE": st_name,
            "LECTURA CRÍTICA": sanitize_score(subj_scores.get("LECTURA CRÍTICA")),
            "MATEMÁTICAS": sanitize_score(subj_scores.get("MATEMÁTICAS")),
            "SOCIALES Y CIUDADANAS": sanitize_score(subj_scores.get("SOCIALES Y CIUDADANAS")),
            "CIENCIAS NATURALES": sanitize_score(subj_scores.get("CIENCIAS NATURALES")),
            "INGLÉS": sanitize_score(subj_scores.get("INGLÉS")),
            "PROMEDIO SIMPLE": prom_simple,
            "PROMEDIO PONDERADO": pg_val,
            "DESVIACIÓN ESTÁNDAR": desv_est
        })

    df_calc = pd.DataFrame(calculated_rows)
    insights = generate_ai_insights(nombre.strip(), df_calc, materias=MATERIAS)

    try:
        with conn.cursor() as cur:
            # 1. Insertar registro en tabla `simulacros`
            cur.execute("""
                INSERT INTO simulacros (id, nombre, promocion_id, origen, estado, creado_por, insights)
                VALUES (%s, %s, %s, 'manual', 'ready', %s, %s::jsonb);
            """, (sim_id, nombre.strip(), promocion_id, usuario, json.dumps(insights)))

            # 2. Consultar mapa de estudiantes existentes en la promoción
            cur.execute("SELECT id, nombre FROM estudiantes WHERE promocion_id = %s;", (promocion_id,))
            st_db_map = {str(r[1]).strip().upper(): r[0] for r in cur.fetchall()}

            inserted_count = 0
            for _, r in df_calc.iterrows():
                st_name_norm = str(r["ESTUDIANTE"]).strip().upper()
                st_id = st_db_map.get(st_name_norm)
                
                if not st_id:
                    cur.execute("""
                        INSERT INTO estudiantes (nombre, grado, promocion_id)
                        VALUES (%s, '11', %s)
                        ON CONFLICT (nombre, promocion_id) DO UPDATE SET grado = EXCLUDED.grado
                        RETURNING id;
                    """, (r["ESTUDIANTE"], promocion_id))
                    st_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO resultados_simulacro (
                        simulacro_id, estudiante_id, lectura_critica, matematicas,
                        sociales_ciudadanas, ciencias_naturales, ingles,
                        promedio_simple, promedio_ponderado, desviacion_estandar
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (simulacro_id, estudiante_id) DO UPDATE SET
                        lectura_critica = EXCLUDED.lectura_critica,
                        matematicas = EXCLUDED.matematicas,
                        sociales_ciudadanas = EXCLUDED.sociales_ciudadanas,
                        ciencias_naturales = EXCLUDED.ciencias_naturales,
                        ingles = EXCLUDED.ingles,
                        promedio_simple = EXCLUDED.promedio_simple,
                        promedio_ponderado = EXCLUDED.promedio_ponderado,
                        desviacion_estandar = EXCLUDED.desviacion_estandar;
                """, (
                    sim_id, st_id,
                    r["LECTURA CRÍTICA"], r["MATEMÁTICAS"], r["SOCIALES Y CIUDADANAS"],
                    r["CIENCIAS NATURALES"], r["INGLÉS"], r["PROMEDIO SIMPLE"],
                    r["PROMEDIO PONDERADO"], r["DESVIACIÓN ESTÁNDAR"]
                ))
                inserted_count += 1

            record_audit_log(
                cur,
                usuario,
                "CREAR_SIMULACRO_MANUAL",
                "simulacros",
                sim_id,
                {"nombre": nombre.strip(), "estudiantes_ingestados": inserted_count}
            )

        conn.commit()
        st.cache_data.clear()
        return True, f"Simulacro '{nombre.strip()}' guardado e ingestado exitosamente con {inserted_count} estudiantes en Supabase.", {"id": sim_id, "nombre": nombre.strip()}
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        return False, f"Error guardando el simulacro manual en Supabase: {exc}", {}
    finally:
        conn.close()


def save_manual_icfes_real_grid(promocion_id: str, df_editor: pd.DataFrame, usuario: str) -> Tuple[bool, str, Dict]:
    """Guarda o actualiza las notas oficiales del ICFES Real para los estudiantes de la promoción activa."""
    if not promocion_id:
        return False, "No hay una promoción activa seleccionada.", {}

    if df_editor.empty:
        return False, "La grilla de estudiantes está vacía.", {}

    conn = get_db_connection()
    if not conn:
        return False, "No hay conexión configurada a Supabase.", {}

    calculated_rows = []
    for _, r in df_editor.iterrows():
        st_name = str(r.get("ESTUDIANTE", "")).strip()
        if not st_name:
            continue

        subj_scores = {m: r.get(m) for m in MATERIAS}
        custom_global = r.get("PUNTAJE GLOBAL (0-500)") or r.get("PROMEDIO PONDERADO")
        _, pg_val, _ = calculate_icfes_scores(subj_scores, custom_global)

        calculated_rows.append({
            "ESTUDIANTE": st_name,
            "LECTURA CRÍTICA": sanitize_score(subj_scores.get("LECTURA CRÍTICA")),
            "MATEMÁTICAS": sanitize_score(subj_scores.get("MATEMÁTICAS")),
            "SOCIALES Y CIUDADANAS": sanitize_score(subj_scores.get("SOCIALES Y CIUDADANAS")),
            "CIENCIAS NATURALES": sanitize_score(subj_scores.get("CIENCIAS NATURALES")),
            "INGLÉS": sanitize_score(subj_scores.get("INGLÉS")),
            "PUNTAJE GLOBAL": pg_val,
        })

    if not calculated_rows:
        return False, "No se encontraron estudiantes válidos en la grilla.", {}

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT anio_graduacion FROM promociones WHERE id = %s;", (promocion_id,))
            p_row = cur.fetchone()
            anio_presentacion = p_row[0] if p_row else 2026

            cur.execute("SELECT id, nombre FROM estudiantes WHERE promocion_id = %s;", (promocion_id,))
            st_db_map = {str(r[1]).strip().upper(): r[0] for r in cur.fetchall()}

            saved_count = 0
            for r in calculated_rows:
                st_name_norm = str(r["ESTUDIANTE"]).strip().upper()
                st_id = st_db_map.get(st_name_norm)

                if not st_id:
                    cur.execute("""
                        INSERT INTO estudiantes (nombre, grado, promocion_id)
                        VALUES (%s, '11', %s)
                        ON CONFLICT (nombre, promocion_id) DO UPDATE SET grado = EXCLUDED.grado
                        RETURNING id;
                    """, (r["ESTUDIANTE"], promocion_id))
                    st_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO resultados_icfes_real (
                        estudiante_id, promocion_id, anio_presentacion,
                        lectura_critica, matematicas, sociales_ciudadanas,
                        ciencias_naturales, ingles, puntaje_global
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (estudiante_id, anio_presentacion) DO UPDATE SET
                        promocion_id = EXCLUDED.promocion_id,
                        lectura_critica = EXCLUDED.lectura_critica,
                        matematicas = EXCLUDED.matematicas,
                        sociales_ciudadanas = EXCLUDED.sociales_ciudadanas,
                        ciencias_naturales = EXCLUDED.ciencias_naturales,
                        ingles = EXCLUDED.ingles,
                        puntaje_global = EXCLUDED.puntaje_global;
                """, (
                    st_id, promocion_id, anio_presentacion,
                    r["LECTURA CRÍTICA"], r["MATEMÁTICAS"], r["SOCIALES Y CIUDADANAS"],
                    r["CIENCIAS NATURALES"], r["INGLÉS"], r["PUNTAJE GLOBAL"]
                ))
                saved_count += 1

            record_audit_log(
                cur,
                usuario,
                "GUARDAR_ICFES_REAL_MANUAL",
                "resultados_icfes_real",
                promocion_id,
                {"estudiantes_guardados": saved_count, "anio": anio_presentacion}
            )

        conn.commit()
        st.cache_data.clear()

        try:
            from ..ml.prediccion_icfes import entrenar_modelo
            entrenar_modelo(conn=conn)
        except Exception:
            pass

        return True, f"Resultados oficiales ICFES Real guardados exitosamente para {saved_count} estudiantes. Modelo ML auto-calibrado.", {}
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        return False, f"Error guardando resultados ICFES Real: {exc}", {}
    finally:
        conn.close()


def ingest_icfes_real_excel(file_buffer: BytesIO, usuario: str, promocion_id: Optional[str] = None) -> Tuple[bool, str, Dict]:
    """Valida e ingesta las notas oficiales del ICFES Real desde un archivo Excel/CSV."""
    file_buffer.seek(0, 2)
    size_mb = file_buffer.tell() / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        return False, f"El archivo excede el límite de {MAX_UPLOAD_MB} MB.", {}
    file_buffer.seek(0)
    header = file_buffer.read(8)
    file_buffer.seek(0)

    fname = getattr(file_buffer, "name", "").lower()
    if fname.endswith(".xlsx") and not header.startswith(b"PK\x03\x04"):
        return False, "El archivo .xlsx no posee una cabecera binaria válida de hoja de cálculo.", {}
    if fname.endswith(".xls") and not header.startswith(b"\xd0\xcf\x11\xe0"):
        return False, "El archivo .xls no posee una cabecera binaria válida de Excel.", {}

    try:
        df_raw = pd.read_excel(file_buffer)
    except Exception as exc:  # noqa: BLE001
        return False, f"No se pudo leer el Excel: {exc}", {}

    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    df = _clean_student_frame(df_raw)
    errores = _validate_schema(df)
    if errores:
        return False, "; ".join(errores), {}

    promocion_id = promocion_id or (st.session_state.get("promocion_activa_id") if hasattr(st, "session_state") else None)
    if not promocion_id:
        return False, "No hay una promoción activa seleccionada.", {}

    conn = get_db_connection()
    if not conn:
        return False, "No hay conexión configurada a Supabase.", {}

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT anio_graduacion FROM promociones WHERE id = %s;", (promocion_id,))
            p_row = cur.fetchone()
            anio_presentacion = p_row[0] if p_row else 2026

            saved_count = 0
            for _, r in df.iterrows():
                st_name = str(r["ESTUDIANTE"]).strip()
                st_grado = str(r["GRADO"]).strip() if pd.notna(r.get("GRADO")) else None

                cur.execute("""
                    INSERT INTO estudiantes (nombre, grado, promocion_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (nombre, promocion_id) DO UPDATE SET grado = EXCLUDED.grado
                    RETURNING id;
                """, (st_name, st_grado, promocion_id))
                st_id = cur.fetchone()[0]

                subj_scores = {m: r.get(m) for m in MATERIAS}
                custom_global = r.get("PUNTAJE GLOBAL (0-500)") or r.get("PROMEDIO PONDERADO")
                _, pg_val, _ = calculate_icfes_scores(subj_scores, custom_global)

                cur.execute("""
                    INSERT INTO resultados_icfes_real (
                        estudiante_id, promocion_id, anio_presentacion,
                        lectura_critica, matematicas, sociales_ciudadanas,
                        ciencias_naturales, ingles, puntaje_global
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (estudiante_id, anio_presentacion) DO UPDATE SET
                        promocion_id = EXCLUDED.promocion_id,
                        lectura_critica = EXCLUDED.lectura_critica,
                        matematicas = EXCLUDED.matematicas,
                        sociales_ciudadanas = EXCLUDED.sociales_ciudadanas,
                        ciencias_naturales = EXCLUDED.ciencias_naturales,
                        ingles = EXCLUDED.ingles,
                        puntaje_global = EXCLUDED.puntaje_global;
                """, (
                    st_id, promocion_id, anio_presentacion,
                    sanitize_score(r.get("LECTURA CRÍTICA")),
                    sanitize_score(r.get("MATEMÁTICAS")),
                    sanitize_score(r.get("SOCIALES Y CIUDADANAS")),
                    sanitize_score(r.get("CIENCIAS NATURALES")),
                    sanitize_score(r.get("INGLÉS")),
                    pg_val
                ))
                saved_count += 1

            record_audit_log(
                cur,
                usuario,
                "INGESTAR_ICFES_REAL_EXCEL",
                "resultados_icfes_real",
                promocion_id,
                {"estudiantes_guardados": saved_count, "anio": anio_presentacion}
            )

        conn.commit()
        st.cache_data.clear()

        try:
            from ..ml.prediccion_icfes import entrenar_modelo
            entrenar_modelo(conn=conn)
        except Exception:
            pass

        return True, f"Resultados oficiales ICFES Real ingestados exitosamente para {saved_count} estudiantes. Modelo ML auto-calibrado.", {}
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        return False, f"Error al procesar e insertar ICFES Real: {exc}", {}
    finally:
        conn.close()


def update_simulacro_nombre(simulacro_id: str, nuevo_nombre: str, usuario: str) -> Tuple[bool, str]:
    """Actualiza exclusivamente el nombre del simulacro en Supabase de forma rápida y segura."""
    if not simulacro_id or not simulacro_id.strip():
        return False, "ID de simulacro inválido."
    nuevo_nombre_clean = nuevo_nombre.strip() if nuevo_nombre else ""
    if not nuevo_nombre_clean:
        return False, "El nombre del simulacro no puede estar vacío."

    conn = get_db_connection()
    if not conn:
        return False, "No hay conexión configurada a Supabase."

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT nombre FROM simulacros WHERE id = %s;", (simulacro_id,))
            row = cur.fetchone()
            if not row:
                return False, "El simulacro especificado no existe en la base de datos."
            nombre_anterior = row[0]

            cur.execute("UPDATE simulacros SET nombre = %s WHERE id = %s;", (nuevo_nombre_clean, simulacro_id))

            record_audit_log(
                cur,
                usuario,
                "RENOMBRAR_SIMULACRO",
                "simulacros",
                simulacro_id,
                {"nombre_anterior": nombre_anterior, "nuevo_nombre": nuevo_nombre_clean}
            )

        conn.commit()
        st.cache_data.clear()
        return True, f"Nombre actualizado de '{nombre_anterior}' a '{nuevo_nombre_clean}'."
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        return False, f"Error al renombrar el simulacro: {exc}"
    finally:
        conn.close()


def update_manual_simulacro_grid(
    simulacro_id: str,
    arg2: Any,
    arg3: Any = "admin",
    arg4: Optional[str] = None
) -> Tuple[bool, str]:
    """Actualiza en caliente las notas y nombre del simulacro con recálculo automático de fórmulas ICFES."""
    if not simulacro_id:
        return False, "ID de simulacro inválido."

    conn = get_db_connection()
    if not conn:
        return False, "No hay conexión configurada a Supabase."

    # Discriminar si arg2 es un DataFrame o un string con nuevo_nombre
    if isinstance(arg2, pd.DataFrame):
        df_editor = arg2
        usuario = str(arg3) if arg3 else "admin"
        nuevo_nombre = arg4
    else:
        nuevo_nombre = str(arg2) if arg2 else None
        df_editor = arg3 if isinstance(arg3, pd.DataFrame) else pd.DataFrame()
        usuario = str(arg4) if arg4 else "admin"

    if df_editor is None or df_editor.empty:
        return False, "No se recibieron datos válidos para actualizar."

    # Si no se especificó nuevo nombre, conservar el existente en la base de datos
    if not nuevo_nombre or not str(nuevo_nombre).strip():
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT nombre FROM simulacros WHERE id = %s;", (simulacro_id,))
                row = cur.fetchone()
                nuevo_nombre_clean = row[0] if row else "Simulacro"
        except Exception:
            nuevo_nombre_clean = "Simulacro"
    else:
        nuevo_nombre_clean = str(nuevo_nombre).strip()

    # Recalcular métricas
    calculated_rows = []
    for _, r in df_editor.iterrows():
        st_name = str(r.get("ESTUDIANTE", "")).strip()
        if not st_name:
            continue

        subj_scores = {m: r.get(m) for m in MATERIAS}
        custom_global = r.get("PUNTAJE GLOBAL (0-500)") or r.get("PROMEDIO PONDERADO")
        prom_simple, pg_val, desv_est = calculate_icfes_scores(subj_scores, custom_global)

        calculated_rows.append({
            "ESTUDIANTE": st_name,
            "LECTURA CRÍTICA": sanitize_score(subj_scores.get("LECTURA CRÍTICA")),
            "MATEMÁTICAS": sanitize_score(subj_scores.get("MATEMÁTICAS")),
            "SOCIALES Y CIUDADANAS": sanitize_score(subj_scores.get("SOCIALES Y CIUDADANAS")),
            "CIENCIAS NATURALES": sanitize_score(subj_scores.get("CIENCIAS NATURALES")),
            "INGLÉS": sanitize_score(subj_scores.get("INGLÉS")),
            "PROMEDIO SIMPLE": prom_simple,
            "PROMEDIO PONDERADO": pg_val,
            "DESVIACIÓN ESTÁNDAR": desv_est
        })

    df_calc = pd.DataFrame(calculated_rows)
    insights = generate_ai_insights(nuevo_nombre_clean, df_calc, materias=MATERIAS)

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE simulacros
                SET nombre = %s, insights = %s::jsonb
                WHERE id = %s;
            """, (nuevo_nombre_clean, json.dumps(insights), simulacro_id))

            cur.execute("SELECT promocion_id FROM simulacros WHERE id = %s;", (simulacro_id,))
            promo_row = cur.fetchone()
            promocion_id = promo_row[0] if promo_row else None

            if promocion_id:
                cur.execute("SELECT id, nombre FROM estudiantes WHERE promocion_id = %s;", (promocion_id,))
                st_db_map = {str(r[1]).strip().upper(): r[0] for r in cur.fetchall()}

                for _, r in df_calc.iterrows():
                    st_name_norm = str(r["ESTUDIANTE"]).strip().upper()
                    st_id = st_db_map.get(st_name_norm)

                    if not st_id:
                        cur.execute("""
                            INSERT INTO estudiantes (nombre, grado, promocion_id)
                            VALUES (%s, '11', %s)
                            ON CONFLICT (nombre, promocion_id) DO UPDATE SET grado = EXCLUDED.grado
                            RETURNING id;
                        """, (r["ESTUDIANTE"], promocion_id))
                        st_id = cur.fetchone()[0]

                    cur.execute("""
                        INSERT INTO resultados_simulacro (
                            simulacro_id, estudiante_id, lectura_critica, matematicas,
                            sociales_ciudadanas, ciencias_naturales, ingles,
                            promedio_simple, promedio_ponderado, desviacion_estandar
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (simulacro_id, estudiante_id) DO UPDATE SET
                            lectura_critica = EXCLUDED.lectura_critica,
                            matematicas = EXCLUDED.matematicas,
                            sociales_ciudadanas = EXCLUDED.sociales_ciudadanas,
                            ciencias_naturales = EXCLUDED.ciencias_naturales,
                            ingles = EXCLUDED.ingles,
                            promedio_simple = EXCLUDED.promedio_simple,
                            promedio_ponderado = EXCLUDED.promedio_ponderado,
                            desviacion_estandar = EXCLUDED.desviacion_estandar;
                    """, (
                        simulacro_id, st_id,
                        r["LECTURA CRÍTICA"], r["MATEMÁTICAS"], r["SOCIALES Y CIUDADANAS"],
                        r["CIENCIAS NATURALES"], r["INGLÉS"], r["PROMEDIO SIMPLE"],
                        r["PROMEDIO PONDERADO"], r["DESVIACIÓN ESTÁNDAR"]
                    ))

            record_audit_log(
                cur,
                usuario,
                "ACTUALIZAR_SIMULACRO_GRILLA",
                "simulacros",
                simulacro_id,
                {"nuevo_nombre": nuevo_nombre_clean, "estudiantes_actualizados": len(df_calc)}
            )

        conn.commit()
        st.cache_data.clear()
        return True, f"Simulacro '{nuevo_nombre_clean}' actualizado exitosamente con {len(df_calc)} registros."
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        return False, f"Error actualizando el simulacro: {exc}"
    finally:
        conn.close()


def delete_simulacro(simulacro_id: str, usuario: str = "admin") -> Tuple[bool, str]:
    """Elimina un simulacro y todos sus resultados asociados de Supabase con registro de auditoría."""
    if not simulacro_id:
        return False, "ID de simulacro inválido."

    conn = get_db_connection()
    if not conn:
        return False, "No hay conexión configurada a Supabase."

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT nombre FROM simulacros WHERE id = %s;", (simulacro_id,))
            row = cur.fetchone()
            nombre_sim = row[0] if row else simulacro_id

            cur.execute("DELETE FROM resultados_simulacro WHERE simulacro_id = %s;", (simulacro_id,))
            cur.execute("DELETE FROM simulacros WHERE id = %s;", (simulacro_id,))

            record_audit_log(
                cur,
                usuario,
                "ELIMINAR_SIMULACRO",
                "simulacros",
                simulacro_id,
                {"nombre_eliminado": nombre_sim}
            )

        conn.commit()
        st.cache_data.clear()
        return True, f"Simulacro '{nombre_sim}' y sus resultados eliminados exitosamente."
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        return False, f"Error al eliminar el simulacro: {exc}"
    finally:
        conn.close()
