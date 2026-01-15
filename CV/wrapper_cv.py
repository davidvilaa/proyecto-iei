# src/cv/wrapper_cv.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any



def leer_cv_json(json_file_path: str | Path) -> list[dict[str, Any]]:
    """
    Wrapper CV (sin HTTP):
    - Lee la fuente JSON (estaciones.json).
    - Devuelve registros RAW (crudos).
    - NO hace mapping/validaciones semánticas.
    - NO geocodifica.
    - NO escribe en Firestore.
    """
    path = Path(json_file_path)

    if not path.exists():
        return []



    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Aseguramos que sea lista (según tu script original, data_cv se itera como lista).
        if isinstance(data, list):
            return data

        # Si viniera como objeto { "data": [...] } u otra estructura, lo adaptáis aquí.
        return []

    except json.JSONDecodeError:
        return []



