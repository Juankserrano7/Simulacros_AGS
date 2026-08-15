"""Pruebas unitarias para validar funciones del módulo core_utils."""

import unittest
import numpy as np
from simulacros_ags.core_utils import (
    calculate_icfes_scores,
    normalize_student_name,
    sanitize_score,
)


class TestCoreUtils(unittest.TestCase):
    def test_normalize_student_name(self):
        # Acentos y mayúsculas
        self.assertEqual(normalize_student_name("  josé pérez  "), "JOSE PEREZ")
        # Caracteres especiales
        self.assertEqual(normalize_student_name("Ana-María González #10"), "ANA MARIA GONZALEZ 10")
        # D SILVA
        self.assertEqual(normalize_student_name("D'SILVA ROSAS ALEJANDRO"), "DSILVA ROSAS ALEJANDRO")
        self.assertEqual(normalize_student_name("D SILVA ROSAS ALEJANDRO"), "DSILVA ROSAS ALEJANDRO")
        # Vacíos y None
        self.assertEqual(normalize_student_name(""), "")
        self.assertEqual(normalize_student_name(None), "")
        self.assertEqual(normalize_student_name("nan"), "")

    def test_sanitize_score(self):
        self.assertEqual(sanitize_score(85), 85.0)
        self.assertEqual(sanitize_score("92.5"), 92.5)
        self.assertEqual(sanitize_score(150, min_val=0, max_val=100), 100.0)
        self.assertEqual(sanitize_score(-10, min_val=0, max_val=100), 0.0)
        self.assertEqual(sanitize_score(None, default=0.0), 0.0)
        self.assertIsNone(sanitize_score("invalido", default=None))
        self.assertEqual(sanitize_score(np.nan, default=0.0), 0.0)

    def test_calculate_icfes_scores(self):
        # Si todas las materias son 100:
        scores = {
            "LECTURA CRÍTICA": 100,
            "MATEMÁTICAS": 100,
            "SOCIALES Y CIUDADANAS": 100,
            "CIENCIAS NATURALES": 100,
            "INGLÉS": 100,
        }
        prom_simple, puntaje_global, desv_est = calculate_icfes_scores(scores)
        self.assertEqual(prom_simple, 500.0)
        self.assertEqual(puntaje_global, 500.0)
        self.assertEqual(desv_est, 0.0)

        # Caso mixto con ponderaciones oficiales
        scores_mixed = {
            "LECTURA CRÍTICA": 80,
            "MATEMÁTICAS": 70,
            "SOCIALES Y CIUDADANAS": 60,
            "CIENCIAS NATURALES": 50,
            "INGLÉS": 90,
        }
        prom_s, global_p, desv = calculate_icfes_scores(scores_mixed)
        self.assertEqual(prom_s, 350.0)
        self.assertAlmostEqual(global_p, 334.62, places=1)
        self.assertGreater(desv, 0.0)

    def test_calculate_icfes_scores_with_custom_global(self):
        scores = {
            "LECTURA CRÍTICA": 80,
            "MATEMÁTICAS": 70,
            "SOCIALES Y CIUDADANAS": 60,
            "CIENCIAS NATURALES": 50,
            "INGLÉS": 90,
        }
        prom_s, global_p, desv = calculate_icfes_scores(scores, custom_global=380.0)
        self.assertEqual(global_p, 380.0)


if __name__ == "__main__":
    unittest.main()
