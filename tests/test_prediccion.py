"""Pruebas unitarias y de integración para el pipeline de Machine Learning adaptativo."""

import os
import sys
import unittest
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from simulacros_ags.ml.prediccion_icfes import (
    FEATURE_NAMES,
    SUBJECT_DISPLAY_NAMES,
    construir_dataset_entrenamiento,
    entrenar_modelo,
    generar_analisis_diagnostico_cohorte,
    predecir_puntaje_final,
)


class TestMLPredictivo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv(dotenv_path=root_dir / ".env")
        cls.db_url = os.getenv("SUPABASE_DB_URL")
        if not cls.db_url:
            raise unittest.SkipTest("SUPABASE_DB_URL no configurada en el entorno.")
        cls.conn = psycopg2.connect(cls.db_url)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn") and cls.conn:
            cls.conn.close()

    def test_01_feature_set_dimension(self):
        """Valida que el vector de características mantenga 16 dimensiones invariantes."""
        self.assertEqual(len(FEATURE_NAMES), 16)

    def test_02_exclusion_inclusion_dataset(self):
        """Verifica que ningún estudiante de inclusión ingrese al dataset de entrenamiento."""
        dataset = construir_dataset_entrenamiento(self.conn)
        est_ids = dataset["estudiantes_ids"]

        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM estudiantes WHERE es_inclusion = true;")
            inclusion_ids = set(row[0] for row in cur.fetchall())

        colision = set(est_ids).intersection(inclusion_ids)
        self.assertEqual(len(colision), 0, f"Estudiantes de inclusión detectados en entrenamiento: {colision}")

    def test_03_exclusion_inferencia_inclusion(self):
        """Verifica que un estudiante de inclusión sea rechazado para inferencia numérica estandarizada."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM estudiantes WHERE es_inclusion = true LIMIT 1;")
            row = cur.fetchone()

        if row:
            res_inc = predecir_puntaje_final(self.conn, row[0])
            self.assertTrue(res_inc["es_inclusion"])
            self.assertIsNone(res_inc["prediccion"])
            self.assertIsNone(res_inc["predicciones_materias"])

    def test_04_entrenamiento_y_metricas_loocv(self):
        """Valida que el entrenamiento dual seleccione estimadores con métricas de calidad aceptables."""
        dataset = construir_dataset_entrenamiento(self.conn)
        res_train = entrenar_modelo(conn=self.conn, dataset=dataset)
        meta = res_train["metadata"]

        self.assertGreater(meta["r2_global"], 0.60)
        self.assertLess(meta["rmse_global"], 16.0)
        self.assertEqual(len(meta["metricas_materias"]), 5)

    def test_05_inferencia_jerarquica_multioutput(self):
        """Valida la inferencia multi-output (global y 5 asignaturas) para un estudiante regular."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM estudiantes WHERE es_inclusion = false LIMIT 1;")
            row = cur.fetchone()

        self.assertIsNotNone(row)
        res_pred = predecir_puntaje_final(self.conn, row[0])

        self.assertIsNotNone(res_pred.get("prediccion"))
        self.assertTrue(0 <= res_pred["prediccion"] <= 500)
        self.assertEqual(len(res_pred["predicciones_materias"]), 5)

        for subj in SUBJECT_DISPLAY_NAMES:
            self.assertIn(subj, res_pred["predicciones_materias"])
            p_val = res_pred["predicciones_materias"][subj]["puntaje"]
            self.assertTrue(0 <= p_val <= 100)

    def test_06_diagnostico_calibracion_cohorte(self):
        """Valida el cálculo de diagnósticos de error y sesgo para cohortes completadas."""
        diag = generar_analisis_diagnostico_cohorte(self.conn)
        self.assertNotIn("error", diag)
        self.assertGreater(diag["n_estudiantes"], 0)
        self.assertLess(diag["mae_global"], 15.0)


if __name__ == "__main__":
    unittest.main()
