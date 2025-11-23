import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .config import DATA_ROOT, DEFAULT_SIMULACROS, METADATA_FILE, UPLOADS_DIR


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "simulacro"


def ensure_storage_dirs() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def load_metadata() -> Dict:
    ensure_storage_dirs()
    if not METADATA_FILE.exists():
        return bootstrap_metadata()
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError:
        data = {"simulacros": []}
    if "simulacros" not in data or not isinstance(data["simulacros"], list):
        data["simulacros"] = []
    return data


def save_metadata(data: Dict) -> None:
    ensure_storage_dirs()
    with open(METADATA_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def bootstrap_metadata() -> Dict:
    """Crea el archivo de metadatos con los simulacros de semilla si no existe."""
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {"simulacros": []}
    for sim in DEFAULT_SIMULACROS:
        payload["simulacros"].append(
            {
                "id": sim["id"],
                "nombre": sim["nombre"],
                "path": str(sim["path"]),
                "origen": sim.get("origen", "semilla"),
                "estado": "ready",
                "creado_por": sim.get("creado_por", "sistema"),
                "creado_en": sim.get("creado_en", now_iso),
                "errores": [],
                "insights": {},
            }
        )
    save_metadata(payload)
    return payload


def get_simulacros_metadata() -> List[Dict]:
    data = load_metadata()
    return data.get("simulacros", [])


def _next_unique_id(base: str, existing: List[str]) -> str:
    candidate = base
    counter = 2
    while candidate in existing:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def register_simulacro(nombre: str, path: Path, creado_por: str, estado: str = "processing") -> Dict:
    meta = load_metadata()
    existing_ids = [sim.get("id", "") for sim in meta.get("simulacros", [])]
    base_id = _slugify(nombre)
    sim_id = _next_unique_id(base_id, existing_ids)
    registro = {
        "id": sim_id,
        "nombre": nombre.strip(),
        "path": str(path),
        "origen": "upload",
        "estado": estado,
        "creado_por": creado_por,
        "creado_en": datetime.now(timezone.utc).isoformat(),
        "errores": [],
        "insights": {},
    }
    meta["simulacros"].append(registro)
    save_metadata(meta)
    return registro


def update_simulacro(sim_id: str, **fields) -> Optional[Dict]:
    meta = load_metadata()
    updated = None
    for sim in meta.get("simulacros", []):
        if sim.get("id") == sim_id:
            sim.update({k: v for k, v in fields.items() if v is not None})
            updated = sim
            break
    if updated is not None:
        save_metadata(meta)
    return updated


def mark_estado(sim_id: str, estado: str, errores: Optional[List[str]] = None) -> Optional[Dict]:
    return update_simulacro(sim_id, estado=estado, errores=errores or [])


def upsert_insights(sim_id: str, insights: Dict) -> Optional[Dict]:
    return update_simulacro(sim_id, insights=insights or {})
