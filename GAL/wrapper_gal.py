# src/gal/wrapper_gal.py
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any





def leer_gal_csv(csv_file_path: str | Path, delimiter: str = ";") -> list[dict[str, Any]]:
    """
    Wrapper GAL (sin HTTP):
    - Lee el CSV de Galicia.
    - Devuelve registros 'crudos' (raw) como lista de dicts.
    - NO hace mapping semántico, NO valida lógica de negocio, NO carga en Firestore.
    """
    csv_path = Path(csv_file_path)

    if not csv_path.exists():
        # En vez de print, aquí devolvemos [] y la API decidirá qué error HTTP devolver.
        return []

    data: list[dict[str, Any]] = []

    # utf-8-sig ayuda si el CSV viene con BOM.
    with csv_path.open(mode="r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=delimiter)

        for row in reader:
            cleaned_row: dict[str, Any] = {}

            # Limpieza mínima: strip en claves/valores y convertir None a "".
            for key, value in row.items():
                if key is None:
                    continue
                k = key.strip()
                v = value.strip() if isinstance(value, str) else (value or "")
                cleaned_row[k] = v

            data.append(cleaned_row)

    return data





