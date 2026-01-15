# src/cat/wrapper_cat.py
from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET



def leer_cat_xml(xml_file_path: str | Path) -> list[dict[str, Any]]:
    """
    Wrapper CAT (sin HTTP):
    - Lee el XML de Catalunya.
    - Devuelve registros RAW como lista de dicts.
    - NO hace mapping semántico, NO valida CP/provincia, NO toca Firestore.
    """
    path = Path(xml_file_path)
    if not path.exists():
        return []



    try:
        tree = ET.parse(path)
        root = tree.getroot()

        estaciones: list[dict[str, Any]] = []

        # El XML parece tener nodos <row> con hijos como campos
        for row_node in root.findall(".//row"):
            record: dict[str, Any] = {}

            for child in row_node:
                # En tu script original ignorabas tags que empiezan por "_" (metadatos)
                if child.tag.startswith("_"):
                    continue

                # 1) Texto normal
                if child.text and child.text.strip():
                    record[child.tag] = child.text.strip()
                # 2) Algunos campos pueden venir como atributo url
                elif child.attrib.get("url"):
                    record[child.tag] = child.attrib.get("url")
                else:
                    record[child.tag] = ""

            # Igual que tu script: solo añadimos si hay campo "estaci" (identificador/nombre origen)
            if record and "estaci" in record:
                estaciones.append(record)

        return estaciones

    except Exception:
        # Si queréis, aquí se puede loguear el error; el API se encargará del HTTP error.
        return []





