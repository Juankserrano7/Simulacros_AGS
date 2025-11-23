import json
import os
from datetime import datetime, timezone
from typing import Dict, List

import pandas as pd

from .config import MATERIAS


def _build_stats(df: pd.DataFrame, materias: List[str]) -> Dict:
    promedios_materias = {mat: float(df[mat].mean()) for mat in materias if mat in df.columns}
    desviaciones = {mat: float(df[mat].std()) for mat in materias if mat in df.columns}
    orden_materias = sorted(promedios_materias.items(), key=lambda x: x[1])
    peor_materia, mejor_materia = orden_materias[0][0], orden_materias[-1][0]
    return {
        "promedio_general": float(df["PROMEDIO PONDERADO"].mean()),
        "min_general": float(df["PROMEDIO PONDERADO"].min()),
        "max_general": float(df["PROMEDIO PONDERADO"].max()),
        "promedios_materias": promedios_materias,
        "desviaciones": desviaciones,
        "mejor_materia": mejor_materia,
        "peor_materia": peor_materia,
    }


def _heuristic_insights(nombre: str, stats: Dict) -> Dict:
    recomendacion_base = (
        f"Fortalece {stats['peor_materia']} con sesiones cortas de práctica diagnóstica y retroalimentación semanal,"
        " priorizando a los estudiantes debajo del promedio general."
    )
    recomendacion_profundizar = (
        f"Aprovecha el desempeño en {stats['mejor_materia']} para crear grupos de mentores que ayuden en {stats['peor_materia']}."
    )
    dispersion_mayor = max(stats["desviaciones"], key=stats["desviaciones"].get)

    return {
        "modelo": "heuristico-local",
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "resumen": f"Panorama de {nombre} actualizado automáticamente.",
        "recomendaciones": {
            "corto": [recomendacion_base, recom_end := "Refuerzo express con micro-simulacros semanales.", "Retroalimentación 1:1 a estudiantes en riesgo."],
            "mediano": [recomendacion_profundizar, "Club de estudio guiado para nivel medio.", "Monitoreo quincenal por materia con rúbricas."],
            "largo": ["Programa de mentorías entre pares.", "Plan trimestral de repaso por objetivos ICFES.", "Simulacros completos con retroalimentación grupal."]
        },
        "conclusiones": [],
        "alertas": [
            f"Variabilidad alta en {dispersion_mayor} (σ {stats['desviaciones'][dispersion_mayor]:.1f}).",
            f"{stats['peor_materia']} es el área crítica ({stats['promedios_materias'][stats['peor_materia']]:.1f} pts).",
        ],
        "fortalezas": [
            f"Destaca {stats['mejor_materia']} con {stats['promedios_materias'][stats['mejor_materia']]:.1f} pts.",
            "Hay margen de apoyo entre pares desde las materias fuertes hacia las débiles.",
        ],
        "datos": stats,
    }


def generate_ai_insights(nombre: str, df: pd.DataFrame, materias: List[str] = MATERIAS) -> Dict:
    """Genera recomendaciones. Usa OpenAI si hay clave, si no aplica heurística."""
    stats = _build_stats(df, materias)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _heuristic_insights(nombre, stats)

    try:
        from openai import OpenAI
    except Exception:
        return _heuristic_insights(nombre, stats)

    client = OpenAI(api_key=api_key)
    modelo = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    mensajes = [
        {
            "role": "system",
            "content": (
                "Eres un asesor pedagógico experto en ICFES. Responde en español y en formato JSON con campos:"
                " resumen (string), recomendaciones (objeto con listas de 3 viñetas para corto/mediano/largo plazo), conclusiones (lista vacía),"
                " alertas (lista de 2 viñetas enfocadas en riesgos/prioridades), fortalezas (lista de 2 viñetas con logros/oportunidades)."
                " Sé concreto y accionable."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Simulacro: {nombre}\n"
                f"Promedio general: {stats['promedio_general']:.2f}\n"
                f"Mejor materia: {stats['mejor_materia']} -> {stats['promedios_materias'][stats['mejor_materia']]:.2f}\n"
                f"Peor materia: {stats['peor_materia']} -> {stats['promedios_materias'][stats['peor_materia']]:.2f}\n"
                f"Desviaciones: {json.dumps(stats['desviaciones'])}"
            ),
        },
    ]
    try:
        respuesta = client.chat.completions.create(
            model=modelo,
            response_format={"type": "json_object"},
            messages=mensajes,
            temperature=0.3,
            max_tokens=400,
        )
        contenido = respuesta.choices[0].message.content
        parsed = json.loads(contenido)
        return {
            "modelo": f"openai/{modelo}",
            "generado_en": datetime.now(timezone.utc).isoformat(),
            "resumen": parsed.get("resumen", ""),
            "recomendaciones": parsed.get("recomendaciones", {}),
            "conclusiones": [],
            "alertas": parsed.get("alertas", []),
            "fortalezas": parsed.get("fortalezas", []),
            "datos": stats,
        }
    except Exception:
        return _heuristic_insights(nombre, stats)
