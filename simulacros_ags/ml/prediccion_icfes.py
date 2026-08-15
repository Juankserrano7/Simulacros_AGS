"""Pipeline de Machine Learning adaptativo, multi-output y autorrefinable para predicción del ICFES Saber 11."""

import hashlib
import json
import os
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, VotingRegressor
from sklearn.linear_model import BayesianRidge, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, LeaveOneOut
from sklearn.multioutput import MultiOutputRegressor, RegressorChain
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ..config import MATERIAS

warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

MODEL_DIR = Path(__file__).parent / "artifacts"
MODEL_FILE = MODEL_DIR / "modelo_icfes.joblib"
METADATA_FILE = MODEL_DIR / "metadata.json"

FEATURE_NAMES = [
    "promedio_ponderado_reciente",
    "promedio_ponderado_global",
    "promedio_ponderado_exp_decay",
    "max_promedio_ponderado",
    "min_promedio_ponderado",
    "tendencia_mejora",
    "delta_progreso",
    "volatilidad",
    "n_simulacros",
    "prom_lectura_critica",
    "prom_matematicas",
    "prom_sociales",
    "prom_ciencias",
    "prom_ingles",
    "dispersion_inter_materias",
    "icfes_composite",
]

SUBJECT_DB_COLUMNS = [
    "lectura_critica",
    "matematicas",
    "sociales_ciudadanas",
    "ciencias_naturales",
    "ingles",
]

SUBJECT_DISPLAY_NAMES = [
    "LECTURA CRÍTICA",
    "MATEMÁTICAS",
    "SOCIALES Y CIUDADANAS",
    "CIENCIAS NATURALES",
    "INGLÉS",
]


def extraer_features_estudiante(df_sims_estudiante: pd.DataFrame) -> Optional[np.ndarray]:
    """
    Extrae un vector de 16 características invariant-dimensionales a partir de la
    trayectoria cronológica de simulacros de un estudiante.
    """
    if df_sims_estudiante.empty:
        return None

    if "simulacro_fecha" in df_sims_estudiante.columns:
        df_sorted = df_sims_estudiante.sort_values("simulacro_fecha", ascending=True)
    else:
        df_sorted = df_sims_estudiante

    # Filtrar únicamente simulacros efectivamente presentados (omite ausencias / no presentó)
    pps = [float(p) for p in df_sorted["promedio_ponderado"].dropna() if float(p) > 0]
    if not pps:
        return None

    n_sims = len(pps)
    ult_pp = float(pps[-1])
    primer_pp = float(pps[0])
    prom_global = float(np.mean(pps))
    max_pp = float(np.max(pps))
    min_pp = float(np.min(pps))
    std_pp = float(np.std(pps)) if n_sims > 1 else 0.0
    delta_pp = float(ult_pp - primer_pp)

    # Promedio ponderado con decaimiento exponencial hacia simulacros más recientes
    if n_sims > 1:
        weights = np.exp(np.linspace(-1.0, 0.0, n_sims))
        weights /= weights.sum()
        exp_pp = float(np.dot(weights, pps))
    else:
        exp_pp = ult_pp

    # Pendiente lineal de progresión (tasa de mejora por simulacro presentado)
    if n_sims >= 2:
        x = np.arange(n_sims)
        slope, _ = np.polyfit(x, pps, 1)
        slope = float(slope)
    else:
        slope = 0.0

    # Promedios acumulados por materia considerando únicamente evaluaciones presentadas
    def _col_mean(col_name: str) -> float:
        if col_name in df_sorted.columns:
            vals = [float(v) for v in df_sorted[col_name].dropna() if float(v) > 0]
            if vals:
                return float(np.mean(vals))
        return prom_global

    lc = _col_mean("lectura_critica")
    mat = _col_mean("matematicas")
    soc = _col_mean("sociales_ciudadanas")
    cn = _col_mean("ciencias_naturales")
    ing = _col_mean("ingles")

    subj_std = float(np.std([lc, mat, soc, cn, ing]))
    icfes_composite = float((3 * lc + 3 * mat + 3 * soc + 3 * cn + 1 * ing) * (5.0 / 13.0))

    features = np.array([
        ult_pp,
        prom_global,
        exp_pp,
        max_pp,
        min_pp,
        slope,
        delta_pp,
        std_pp,
        float(n_sims),
        lc,
        mat,
        soc,
        cn,
        ing,
        subj_std,
        icfes_composite,
    ], dtype=float)

    return features


def _calcular_fingerprint_dataset(conn) -> str:
    """
    Calcula un hash identificador del estado exacto de los datos en Supabase.
    Detecta de inmediato cualquier adición, edición de notas o eliminación
    tanto en resultados_simulacro como en resultados_icfes_real.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                COUNT(r.id), 
                COALESCE(SUM(r.puntaje_global), 0),
                COALESCE(SUM(COALESCE(r.lectura_critica,0) + COALESCE(r.matematicas,0) + COALESCE(r.sociales_ciudadanas,0) + COALESCE(r.ciencias_naturales,0) + COALESCE(r.ingles,0)), 0),
                (SELECT COUNT(rs.id) FROM resultados_simulacro rs),
                (SELECT COALESCE(SUM(rs.promedio_ponderado), 0) FROM resultados_simulacro rs),
                (SELECT COALESCE(SUM(COALESCE(rs.lectura_critica,0) + COALESCE(rs.matematicas,0) + COALESCE(rs.sociales_ciudadanas,0) + COALESCE(rs.ciencias_naturales,0) + COALESCE(rs.ingles,0)), 0) FROM resultados_simulacro rs)
            FROM resultados_icfes_real r
            JOIN estudiantes e ON e.id = r.estudiante_id
            WHERE e.es_inclusion = false;
        """)
        row = cur.fetchone()
        raw = f"{row[0]}_{row[1]}_{row[2]}_{row[3]}_{row[4]}_{row[5]}_{FEATURE_NAMES}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()


def construir_dataset_entrenamiento(conn) -> Dict[str, Any]:
    """
    Construye la matriz X, la matriz Y de asignaturas (N x 5) y el vector y_global (N).
    Excluye estrictamente a estudiantes de inclusión.
    """
    query = """
    SELECT 
        e.id AS estudiante_id,
        e.nombre AS estudiante_nombre,
        e.promocion_id,
        r.lectura_critica AS target_lc,
        r.matematicas AS target_mat,
        r.sociales_ciudadanas AS target_soc,
        r.ciencias_naturales AS target_cn,
        r.ingles AS target_ing,
        r.puntaje_global AS target_global,
        s.id AS simulacro_id,
        s.creado_en AS simulacro_fecha,
        rs.promedio_ponderado,
        rs.lectura_critica,
        rs.matematicas,
        rs.sociales_ciudadanas,
        rs.ciencias_naturales,
        rs.ingles
    FROM estudiantes e
    JOIN resultados_icfes_real r ON r.estudiante_id = e.id
    JOIN resultados_simulacro rs ON rs.estudiante_id = e.id
    JOIN simulacros s ON s.id = rs.simulacro_id
    WHERE e.es_inclusion = false
    ORDER BY e.id, s.creado_en ASC;
    """
    df_raw = pd.read_sql_query(query, conn)

    if df_raw.empty:
        raise ValueError("No se encontraron registros históricos de entrenamiento que cumplan es_inclusion = false.")

    X_list = []
    Y_subs_list = []
    y_glob_list = []
    estudiantes_ids = []
    promociones_ids = []

    grouped = df_raw.groupby("estudiante_id")
    for est_id, group in grouped:
        r0 = group.iloc[0]
        target_val = r0["target_global"]
        if pd.isna(target_val):
            continue

        feat_vector = extraer_features_estudiante(group)
        if feat_vector is not None and len(feat_vector) == len(FEATURE_NAMES):
            X_list.append(feat_vector)
            Y_subs_list.append([
                float(r0["target_lc"] or (target_val / 5.0)),
                float(r0["target_mat"] or (target_val / 5.0)),
                float(r0["target_soc"] or (target_val / 5.0)),
                float(r0["target_cn"] or (target_val / 5.0)),
                float(r0["target_ing"] or (target_val / 5.0)),
            ])
            y_glob_list.append(float(target_val))
            estudiantes_ids.append(est_id)
            promociones_ids.append(r0["promocion_id"])

    X = pd.DataFrame(X_list, columns=FEATURE_NAMES)
    Y_subs = pd.DataFrame(Y_subs_list, columns=SUBJECT_DISPLAY_NAMES)
    y_glob = pd.Series(y_glob_list, name="puntaje_global")

    fingerprint = _calcular_fingerprint_dataset(conn)

    return {
        "X": X,
        "Y_subs": Y_subs,
        "y_glob": y_glob,
        "estudiantes_ids": estudiantes_ids,
        "promociones_ids": promociones_ids,
        "fingerprint": fingerprint,
    }


def entrenar_modelo(conn=None, dataset: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Entrena de forma dual el estimador Multi-Output de asignaturas y el ensamble de puntaje global,
    optimizando la calibración cruzada (LOOCV / K-Fold).
    """
    if dataset is None:
        if conn is None:
            raise ValueError("Se requiere una conexión a la base de datos o un dataset preconstruido.")
        dataset = construir_dataset_entrenamiento(conn)

    X = dataset["X"]
    Y_subs = dataset["Y_subs"]
    y_glob = dataset["y_glob"]
    n_muestras = len(X)

    if n_muestras < 5:
        raise ValueError(f"Muestra de entrenamiento insuficiente (N={n_muestras}). Se requieren al menos 5 observaciones.")

    if n_muestras <= 40:
        cv = LeaveOneOut()
    else:
        cv = KFold(n_splits=min(10, n_muestras // 4), shuffle=True, random_state=42)

    # 1. Evaluación y selección del Motor Multi-Output por Asignatura
    candidatos_mo = {
        "MO_Ridge": MultiOutputRegressor(Pipeline([("scaler", StandardScaler()), ("reg", Ridge(alpha=5.0))])),
        "MO_BayesianRidge": MultiOutputRegressor(Pipeline([("scaler", StandardScaler()), ("reg", BayesianRidge(max_iter=400))])),
        "Chain_Ridge": RegressorChain(Pipeline([("scaler", StandardScaler()), ("reg", Ridge(alpha=5.0))]), order=[0, 2, 1, 3, 4]),
        "MO_RandomForest": MultiOutputRegressor(RandomForestRegressor(n_estimators=50, max_depth=3, min_samples_leaf=2, random_state=42)),
    }

    eval_mo = {}
    mejor_mo_nombre = None
    mejor_mo_rmse = float("inf")

    for nombre, estimator in candidatos_mo.items():
        preds_mo_list = []
        y_true_mo_list = []

        for train_idx, test_idx in cv.split(X):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            Y_train, Y_test = Y_subs.iloc[train_idx], Y_subs.iloc[test_idx]

            estimator.fit(X_train, Y_train)
            pred = estimator.predict(X_test)

            preds_mo_list.extend(pred.tolist())
            y_true_mo_list.extend(Y_test.values.tolist())

        preds_mo_arr = np.array(preds_mo_list)
        y_true_mo_arr = np.array(y_true_mo_list)

        per_subject_metrics = {}
        for idx, subj in enumerate(SUBJECT_DISPLAY_NAMES):
            s_true = y_true_mo_arr[:, idx]
            s_pred = preds_mo_arr[:, idx]
            per_subject_metrics[subj] = {
                "mae": round(float(mean_absolute_error(s_true, s_pred)), 2),
                "rmse": round(float(np.sqrt(mean_squared_error(s_true, s_pred))), 2),
                "r2": round(float(r2_score(s_true, s_pred)), 4),
            }

        overall_mo_rmse = float(np.mean([m["rmse"] for m in per_subject_metrics.values()]))
        eval_mo[nombre] = {
            "overall_rmse": round(overall_mo_rmse, 2),
            "subjects": per_subject_metrics,
        }

        if overall_mo_rmse < mejor_mo_rmse:
            mejor_mo_rmse = overall_mo_rmse
            mejor_mo_nombre = nombre

    modelo_mo_ganador = candidatos_mo[mejor_mo_nombre]
    modelo_mo_ganador.fit(X, Y_subs)

    # 2. Evaluación y selección del Motor Global Directo
    candidatos_global = {
        "Ensemble_Bayes_RF": VotingRegressor([
            ("br", Pipeline([("scaler", StandardScaler()), ("reg", BayesianRidge(max_iter=400))])),
            ("rf", RandomForestRegressor(n_estimators=50, max_depth=3, min_samples_leaf=2, random_state=42)),
        ]),
        "Ensemble_Bayes_GB": VotingRegressor([
            ("br", Pipeline([("scaler", StandardScaler()), ("reg", BayesianRidge(max_iter=400))])),
            ("gb", GradientBoostingRegressor(n_estimators=40, max_depth=2, learning_rate=0.06, subsample=0.9, random_state=42)),
        ]),
        "BayesianRidge": Pipeline([
            ("scaler", StandardScaler()),
            ("reg", BayesianRidge(max_iter=400)),
        ]),
        "Ridge": Pipeline([
            ("scaler", StandardScaler()),
            ("reg", Ridge(alpha=5.0)),
        ]),
    }

    eval_global = {}
    mejor_glob_nombre = None
    mejor_glob_rmse = float("inf")

    for nombre, estimator in candidatos_global.items():
        y_true_list = []
        y_pred_list = []

        for train_idx, test_idx in cv.split(X):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y_glob.iloc[train_idx], y_glob.iloc[test_idx]

            estimator.fit(X_train, y_train)
            pred = estimator.predict(X_test)

            y_true_list.extend(y_test.tolist())
            y_pred_list.extend(pred.tolist())

        y_t = np.array(y_true_list)
        y_p = np.array(y_pred_list)

        mae = float(mean_absolute_error(y_t, y_p))
        rmse = float(np.sqrt(mean_squared_error(y_t, y_p)))
        r2 = float(r2_score(y_t, y_p))

        eval_global[nombre] = {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2": round(r2, 4),
        }

        if rmse < mejor_glob_rmse:
            mejor_glob_rmse = rmse
            mejor_glob_nombre = nombre

    modelo_glob_ganador = candidatos_global[mejor_glob_nombre]
    modelo_glob_ganador.fit(X, y_glob)

    metricas_glob_ganador = eval_global[mejor_glob_nombre]
    confiabilidad = "alta" if metricas_glob_ganador["r2"] >= 0.50 else "media"

    artefacto = {
        "model_global": modelo_glob_ganador,
        "model_subjects": modelo_mo_ganador,
    }

    metadata = {
        "modelo_global_elegido": mejor_glob_nombre,
        "modelo_subjects_elegido": mejor_mo_nombre,
        "r2_global": metricas_glob_ganador["r2"],
        "rmse_global": metricas_glob_ganador["rmse"],
        "mae_global": metricas_glob_ganador["mae"],
        "metricas_materias": eval_mo[mejor_mo_nombre]["subjects"],
        "n_estudiantes_entrenamiento": n_muestras,
        "n_features": len(FEATURE_NAMES),
        "features": FEATURE_NAMES,
        "subjects": SUBJECT_DISPLAY_NAMES,
        "fingerprint": dataset.get("fingerprint", ""),
        "evaluaciones_global": eval_global,
        "evaluaciones_subjects": eval_mo,
        "confiabilidad": confiabilidad,
        "entrenado_en": datetime.now(timezone.utc).isoformat(),
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(artefacto, MODEL_FILE)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return {
        "artefacto": artefacto,
        "metadata": metadata,
        "evaluaciones_global": eval_global,
        "evaluaciones_subjects": eval_mo,
    }


def _obtener_modelo_y_metadata(conn) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Obtiene el artefacto de modelos y sus metadatos. Reentrena en caliente si
    los datos cambian o si el esquema de características no coincide.
    """
    necesita_reentrenamiento = False

    if not MODEL_FILE.exists() or not METADATA_FILE.exists():
        necesita_reentrenamiento = True
    else:
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            saved_features = metadata.get("features", [])
            if saved_features != FEATURE_NAMES or "modelo_subjects_elegido" not in metadata:
                necesita_reentrenamiento = True
            else:
                fingerprint_actual = _calcular_fingerprint_dataset(conn)
                if metadata.get("fingerprint") != fingerprint_actual:
                    necesita_reentrenamiento = True
        except Exception:
            necesita_reentrenamiento = True

    if necesita_reentrenamiento:
        res = entrenar_modelo(conn=conn)
        return res["artefacto"], res["metadata"]

    try:
        artefacto = joblib.load(MODEL_FILE)
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        if isinstance(artefacto, dict) and "model_global" in artefacto and "model_subjects" in artefacto:
            return artefacto, metadata
        else:
            res = entrenar_modelo(conn=conn)
            return res["artefacto"], res["metadata"]
    except Exception:
        res = entrenar_modelo(conn=conn)
        return res["artefacto"], res["metadata"]


def predecir_puntaje_final(conn, estudiante_id: str) -> Dict[str, Any]:
    """
    Inferencia jerárquica: predice tanto el Puntaje Global oficial como cada una
    de las 5 asignaturas evaluadas en el examen de estado ICFES Saber 11.
    """
    # 1. Control estricto de inclusión
    with conn.cursor() as cur:
        cur.execute("SELECT es_inclusion, nombre FROM estudiantes WHERE id = %s;", (estudiante_id,))
        row = cur.fetchone()
        if not row:
            return {"error": "Estudiante no encontrado en la base de datos."}
        es_inclusion, est_nombre = row[0], row[1]

    if es_inclusion:
        return {
            "estudiante_id": estudiante_id,
            "estudiante_nombre": est_nombre,
            "es_inclusion": True,
            "prediccion": None,
            "predicciones_materias": None,
            "intervalo": None,
            "confiabilidad": "baja",
            "mensaje": "Los estudiantes en condición de inclusión no reciben predicción numérica estandarizada.",
        }

    # 2. Cargar o autorefinar artefacto dual
    artefacto, metadata = _obtener_modelo_y_metadata(conn)
    model_global = artefacto["model_global"]
    model_subjects = artefacto["model_subjects"]

    # 3. Consultar ÚNICAMENTE los simulacros del estudiante (Aislamiento total sin leakage)
    query_sims = """
    SELECT 
        s.id AS simulacro_id,
        s.creado_en AS simulacro_fecha,
        rs.promedio_ponderado,
        rs.lectura_critica,
        rs.matematicas,
        rs.sociales_ciudadanas,
        rs.ciencias_naturales,
        rs.ingles
    FROM resultados_simulacro rs
    JOIN simulacros s ON s.id = rs.simulacro_id
    WHERE rs.estudiante_id = %s
    ORDER BY s.creado_en ASC;
    """
    df_sims_est = pd.read_sql_query(query_sims, conn, params=(estudiante_id,))

    if df_sims_est.empty or df_sims_est["promedio_ponderado"].dropna().empty:
        return {
            "estudiante_id": estudiante_id,
            "estudiante_nombre": est_nombre,
            "es_inclusion": False,
            "prediccion": None,
            "predicciones_materias": None,
            "intervalo": None,
            "confiabilidad": "baja",
            "mensaje": "El estudiante no registra simulacros presentados para generar una predicción.",
        }

    feat_vector = extraer_features_estudiante(df_sims_est)
    if feat_vector is None or len(feat_vector) != len(FEATURE_NAMES):
        return {
            "estudiante_id": estudiante_id,
            "estudiante_nombre": est_nombre,
            "es_inclusion": False,
            "prediccion": None,
            "predicciones_materias": None,
            "intervalo": None,
            "confiabilidad": "baja",
            "mensaje": "Datos insuficientes para generar el vector de características.",
        }

    X_est = pd.DataFrame([feat_vector], columns=FEATURE_NAMES)

    # Inferencia Dual con auto-recuperación
    try:
        pred_glob_raw = float(model_global.predict(X_est)[0])
        pred_subs_raw = model_subjects.predict(X_est)[0]
    except Exception:
        res_retrain = entrenar_modelo(conn=conn)
        artefacto = res_retrain["artefacto"]
        metadata = res_retrain["metadata"]
        pred_glob_raw = float(artefacto["model_global"].predict(X_est)[0])
        pred_subs_raw = artefacto["model_subjects"].predict(X_est)[0]

    # Reconciliación matemática entre materias y global
    preds_subs_dict: Dict[str, Dict[str, Any]] = {}
    metricas_materias = metadata.get("metricas_materias", {})

    n_presentados = len(df_sims_est["simulacro_id"].unique())
    factor_incertidumbre = 1.0 / np.sqrt(max(1, min(n_presentados, 8)))

    for idx, subj in enumerate(SUBJECT_DISPLAY_NAMES):
        s_val = float(np.clip(pred_subs_raw[idx], 0.0, 100.0))
        s_rmse = float(metricas_materias.get(subj, {}).get("rmse", 5.0))
        s_margen = float(1.96 * s_rmse * (0.7 + 0.6 * factor_incertidumbre))

        s_lower = max(0.0, round(s_val - s_margen, 1))
        s_upper = min(100.0, round(s_val + s_margen, 1))

        preds_subs_dict[subj] = {
            "puntaje": round(s_val, 1),
            "intervalo": [s_lower, s_upper],
            "mae": metricas_materias.get(subj, {}).get("mae", 4.0),
            "rmse": s_rmse,
        }

    # Puntaje global compuesto derivado de las 5 materias
    lc_p = preds_subs_dict["LECTURA CRÍTICA"]["puntaje"]
    mat_p = preds_subs_dict["MATEMÁTICAS"]["puntaje"]
    soc_p = preds_subs_dict["SOCIALES Y CIUDADANAS"]["puntaje"]
    cn_p = preds_subs_dict["CIENCIAS NATURALES"]["puntaje"]
    ing_p = preds_subs_dict["INGLÉS"]["puntaje"]

    icfes_calc_from_subs = (3 * lc_p + 3 * mat_p + 3 * soc_p + 3 * cn_p + 1 * ing_p) * (5.0 / 13.0)

    # Fusión ponderada: 50% estimador global directo + 50% compuesto de asignaturas
    pred_final_reconciled = float(np.clip(0.50 * pred_glob_raw + 0.50 * icfes_calc_from_subs, 0.0, 500.0))

    rmse_base = float(metadata.get("rmse_global", 13.5))
    margen_global = float(1.96 * rmse_base * (0.7 + 0.6 * factor_incertidumbre))

    lower_bound = max(0.0, round(pred_final_reconciled - margen_global, 1))
    upper_bound = min(500.0, round(pred_final_reconciled + margen_global, 1))

    confiabilidad_final = metadata.get("confiabilidad", "alta")
    if n_presentados < 3:
        confiabilidad_final = "media" if n_presentados == 2 else "baja"

    return {
        "estudiante_id": estudiante_id,
        "estudiante_nombre": est_nombre,
        "es_inclusion": False,
        "prediccion": round(pred_final_reconciled, 1),
        "predicciones_materias": preds_subs_dict,
        "intervalo": [lower_bound, upper_bound],
        "rmse_loocv": round(rmse_base, 2),
        "r2_loocv": metadata.get("r2_global"),
        "mae_loocv": metadata.get("mae_global"),
        "modelo_usado": f"{metadata.get('modelo_global_elegido')} + {metadata.get('modelo_subjects_elegido')}",
        "confiabilidad": confiabilidad_final,
        "simulacros_incompletos": (n_presentados < 4),
        "n_simulacros_presentados": n_presentados,
    }


def generar_analisis_diagnostico_cohorte(conn, promocion_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Ejecuta un análisis diagnóstico profundo comparando las predicciones del modelo
    contra los resultados reales del examen ICFES de una o todas las promociones evaluadas.
    Permite retro-calibración y auditoría de sesgo (fine-tuning).
    """
    if promocion_id:
        query = """
        SELECT 
            e.id AS estudiante_id,
            e.nombre AS estudiante_nombre,
            p.nombre AS promocion_nombre,
            r.lectura_critica AS real_lc,
            r.matematicas AS real_mat,
            r.sociales_ciudadanas AS real_soc,
            r.ciencias_naturales AS real_cn,
            r.ingles AS real_ing,
            r.puntaje_global AS real_global
        FROM estudiantes e
        JOIN promociones p ON p.id = e.promocion_id
        JOIN resultados_icfes_real r ON r.estudiante_id = e.id
        WHERE e.es_inclusion = false AND e.promocion_id = %s;
        """
        df_est = pd.read_sql_query(query, conn, params=(promocion_id,))
    else:
        query = """
        SELECT 
            e.id AS estudiante_id,
            e.nombre AS estudiante_nombre,
            p.nombre AS promocion_nombre,
            r.lectura_critica AS real_lc,
            r.matematicas AS real_mat,
            r.sociales_ciudadanas AS real_soc,
            r.ciencias_naturales AS real_cn,
            r.ingles AS real_ing,
            r.puntaje_global AS real_global
        FROM estudiantes e
        JOIN promociones p ON p.id = e.promocion_id
        JOIN resultados_icfes_real r ON r.estudiante_id = e.id
        WHERE e.es_inclusion = false;
        """
        df_est = pd.read_sql_query(query, conn)

    if df_est.empty:
        return {"error": "No hay datos de ICFES real registrados para la cohorte seleccionada."}

    comparativa_rows = []
    for _, row in df_est.iterrows():
        est_id = row["estudiante_id"]
        res_pred = predecir_puntaje_final(conn, est_id)
        if res_pred and res_pred.get("prediccion") is not None:
            pred_g = res_pred["prediccion"]
            real_g = float(row["real_global"])
            diff_g = round(pred_g - real_g, 1)

            pred_subs = res_pred.get("predicciones_materias", {})
            pred_lc = pred_subs.get("LECTURA CRÍTICA", {}).get("puntaje", 0.0)
            pred_mat = pred_subs.get("MATEMÁTICAS", {}).get("puntaje", 0.0)
            pred_soc = pred_subs.get("SOCIALES Y CIUDADANAS", {}).get("puntaje", 0.0)
            pred_cn = pred_subs.get("CIENCIAS NATURALES", {}).get("puntaje", 0.0)
            pred_ing = pred_subs.get("INGLÉS", {}).get("puntaje", 0.0)

            comparativa_rows.append({
                "Estudiante": row["estudiante_nombre"],
                "Promoción": row["promocion_nombre"],
                "Real Global": real_g,
                "Predicción Global": pred_g,
                "Error (Pred - Real)": diff_g,
                "Abs Error": abs(diff_g),
                "Real LC": float(row["real_lc"] or 0),
                "Pred LC": pred_lc,
                "Real MAT": float(row["real_mat"] or 0),
                "Pred MAT": pred_mat,
                "Real SOC": float(row["real_soc"] or 0),
                "Pred SOC": pred_soc,
                "Real CN": float(row["real_cn"] or 0),
                "Pred CN": pred_cn,
                "Real ING": float(row["real_ing"] or 0),
                "Pred ING": pred_ing,
                "Simulacros": res_pred.get("n_simulacros_presentados", 0),
            })

    if not comparativa_rows:
        return {"error": "No se pudieron calcular predicciones para los estudiantes de la cohorte."}

    df_comp = pd.DataFrame(comparativa_rows)

    # Métricas agregadas de calibración
    mae_global = float(df_comp["Abs Error"].mean())
    rmse_global = float(np.sqrt((df_comp["Error (Pred - Real)"] ** 2).mean()))
    sesgo_medio = float(df_comp["Error (Pred - Real)"].mean())  # + sobreestimación, - subestimación

    # Porcentaje de predicciones dentro de rangos de tolerancia
    pct_dentro_10 = float((df_comp["Abs Error"] <= 10.0).mean() * 100)
    pct_dentro_15 = float((df_comp["Abs Error"] <= 15.0).mean() * 100)
    pct_dentro_20 = float((df_comp["Abs Error"] <= 20.0).mean() * 100)

    # Métricas por materia
    sub_metrics = {}
    for sub, short in [("LECTURA CRÍTICA", "LC"), ("MATEMÁTICAS", "MAT"), ("SOCIALES Y CIUDADANAS", "SOC"), ("CIENCIAS NATURALES", "CN"), ("INGLÉS", "ING")]:
        diff_s = df_comp[f"Pred {short}"] - df_comp[f"Real {short}"]
        sub_metrics[sub] = {
            "mae": round(float(diff_s.abs().mean()), 2),
            "rmse": round(float(np.sqrt((diff_s ** 2).mean())), 2),
            "sesgo": round(float(diff_s.mean()), 2),
        }

    return {
        "df_comparativa": df_comp,
        "n_estudiantes": len(df_comp),
        "mae_global": round(mae_global, 2),
        "rmse_global": round(rmse_global, 2),
        "sesgo_medio": round(sesgo_medio, 2),
        "precision_10_pts": round(pct_dentro_10, 1),
        "precision_15_pts": round(pct_dentro_15, 1),
        "precision_20_pts": round(pct_dentro_20, 1),
        "metricas_materias": sub_metrics,
    }
