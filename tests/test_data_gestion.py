"""Pruebas unitarias para los módulos de datos, normalización, ordenamiento e ingesta de simulacros."""

import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch

import pandas as pd

from simulacros_ags.data import (
    COLUMN_CANONICAL_MAP,
    generate_template_bytes,
    get_regular_presented_df,
    ingest_icfes_real_excel,
    ingest_simulacro_excel,
    ordenar_simulacros,
    save_manual_icfes_real_grid,
    save_manual_simulacro_grid,
)
from simulacros_ags.data.normalization import _clean_student_frame, _validate_schema


class TestDataGestion(unittest.TestCase):
    """Verifica la robustez de las funciones de datos, ordenamiento y carga de simulacros."""

    def test_01_ordenar_simulacros_con_dict(self):
        """Verifica que ordenar_simulacros ordene correctamente un diccionario por fecha."""
        data_map = {
            "sim_2": {
                "meta": {"id": "sim_2", "nombre": "Simulacro 2", "creado_en": "2026-03-01"},
                "df": pd.DataFrame({"ESTUDIANTE": ["A"], "PROMEDIO PONDERADO": [350]})
            },
            "sim_1": {
                "meta": {"id": "sim_1", "nombre": "Simulacro 1", "creado_en": "2026-01-01"},
                "df": pd.DataFrame({"ESTUDIANTE": ["A"], "PROMEDIO PONDERADO": [300]})
            }
        }
        res = ordenar_simulacros(data_map)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]["id"], "sim_1")
        self.assertEqual(res[1]["id"], "sim_2")

    def test_02_ordenar_simulacros_con_tupla_load_all_simulacros(self):
        """Garantiza que ordenar_simulacros maneje sin error la tupla devuelta por load_all_simulacros."""
        metadatos = [{"id": "s1", "nombre": "S1"}]
        data_map = {
            "s1": {
                "meta": {"id": "s1", "nombre": "S1", "creado_en": "2026-02-01"},
                "df": pd.DataFrame()
            }
        }
        errores = []
        tuple_input = (metadatos, data_map, errores)

        # No debe lanzar AttributeError: 'tuple' object has no attribute 'items'
        res = ordenar_simulacros(tuple_input)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["nombre"], "S1")

    def test_03_ordenar_simulacros_con_inputs_invalidos_o_vacios(self):
        """Verifica que ordenar_simulacros no falle ante None, listas vacías u objetos corruptos."""
        self.assertEqual(ordenar_simulacros(None), [])
        self.assertEqual(ordenar_simulacros({}), [])
        self.assertEqual(ordenar_simulacros(()), [])
        self.assertEqual(ordenar_simulacros("invalido"), [])

    def test_04_normalizacion_y_limpieza_estudiantes(self):
        """Verifica que _clean_student_frame elimine filas de totales/promedios y normalice nombres."""
        raw_data = {
            "estudiante ": ["  Gómez,  Juan  ", "PROMEDIO GENERAL", "TOTAL", "Pérez, Ana"],
            "lectura critica": [70, 75, 80, 65],
            "matematicas": [80, 85, 90, 70],
            "sociales y ciudadanas": [75, 80, 85, 60],
            "ciencias naturales": [65, 70, 75, 80],
            "ingles": [90, 85, 80, 85],
            "promedio ponderado": [375.0, 380.0, 400.0, 350.0]
        }
        df_raw = pd.DataFrame(raw_data)
        cleaned = _clean_student_frame(df_raw)

        # Debe haber eliminado 'PROMEDIO GENERAL' y 'TOTAL'
        self.assertEqual(len(cleaned), 2)
        nombres = cleaned["ESTUDIANTE"].tolist()
        self.assertIn("GOMEZ JUAN", [n.replace(",", "") for n in nombres])
        self.assertIn("PEREZ ANA", [n.replace(",", "") for n in nombres])

    def test_05_validacion_esquema(self):
        """Verifica la detección de columnas requeridas y campos numéricos."""
        df_incompleto = pd.DataFrame({"ESTUDIANTE": ["Juan"]})
        errs = _validate_schema(df_incompleto)
        self.assertTrue(len(errs) > 0)
        self.assertIn("Faltan las columnas requeridas", errs[0])

    def test_06_generacion_plantilla_excel(self):
        """Verifica que generate_template_bytes devuelva un archivo Excel binario válido."""
        tmpl = generate_template_bytes()
        self.assertIsInstance(tmpl, bytes)
        self.assertTrue(len(tmpl) > 0)
        self.assertTrue(tmpl.startswith(b"PK\x03\x04"))  # Zip/XLSX magic bytes

    def test_07_ingesta_simulacro_validaciones_defensivas(self):
        """Verifica que ingest_simulacro_excel valide nombres y promociones vacías sin romper."""
        buf = BytesIO(b"dummy content")
        ok, msg, _ = ingest_simulacro_excel("", buf, "admin")
        self.assertFalse(ok)
        self.assertIn("nombre", msg.lower())

        ok2, msg2, _ = ingest_simulacro_excel("Simulacro 1", buf, "admin", promocion_id=None)
        self.assertFalse(ok2)

    def test_08_get_regular_presented_df(self):
        """Verifica que get_regular_presented_df filtre estudiantes de inclusión y notas nulas."""
        df = pd.DataFrame({
            "ESTUDIANTE": ["A", "B", "C"],
            "es_inclusion": [False, True, False],
            "PROMEDIO PONDERADO": [350.0, 320.0, None]
        })
        regular = get_regular_presented_df(df)
        self.assertEqual(len(regular), 1)
        self.assertEqual(regular.iloc[0]["ESTUDIANTE"], "A")


if __name__ == "__main__":
    unittest.main()
