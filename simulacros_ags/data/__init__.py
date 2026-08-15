"""Módulo de acceso y procesamiento de datos para los simulacros AGS.

Maneja la persistencia en Supabase (PostgreSQL), normalización de datos y exportación de reportes.
"""

from .exports import generate_template_bytes
from .loaders import (
    get_or_generate_insights,
    load_all_simulacros,
    load_icfes_real_data,
    ordenar_simulacros,
)
from .normalization import (
    COLUMN_CANONICAL_MAP,
    OPTIONAL_NUMERIC,
    REQUIRED_COLUMNS,
    get_regular_presented_df,
)
from .persistence import (
    delete_simulacro,
    ingest_icfes_real_excel,
    ingest_simulacro_excel,
    save_manual_icfes_real_grid,
    save_manual_simulacro_grid,
    update_manual_simulacro_grid,
    update_simulacro_nombre,
)

__all__ = [
    "COLUMN_CANONICAL_MAP",
    "REQUIRED_COLUMNS",
    "OPTIONAL_NUMERIC",
    "get_regular_presented_df",
    "load_all_simulacros",
    "load_icfes_real_data",
    "ordenar_simulacros",
    "get_or_generate_insights",
    "generate_template_bytes",
    "ingest_simulacro_excel",
    "save_manual_simulacro_grid",
    "save_manual_icfes_real_grid",
    "ingest_icfes_real_excel",
    "update_simulacro_nombre",
    "update_manual_simulacro_grid",
    "delete_simulacro",
]
