# src/cat/api_busqueda_cat.py
from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query

from .wrapper_cat import leer_cat_xml

app = FastAPI(
    title="Wrapper CAT - API de búsqueda",
    version="1.0.0",
    description="Expone datos crudos de la fuente CAT (XML) para que los consuma el extractor.",
)  # patrón básico FastAPI [web:57]

XML_FILE = Path("ITV-CAT.xml")



@app.get("/health")
def health():
    """Health-check simple para saber si el servicio está OK y el XML existe."""
    return {
        "status": "ok",
        "xml_exists": XML_FILE.exists(),
        "xml_path": str(XML_FILE.resolve()),
    }




@app.get("/cat/records")
def cat_records(
    limit: int | None = Query(default=None, ge=1, le=50000),
):
    """
    Devuelve registros RAW obtenidos del XML (sin modificar).
    limit ayuda a probar sin devolver todo.
    """
    records = leer_cat_xml(XML_FILE)

    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudieron leer registros. ¿Existe el XML en {XML_FILE.resolve()}?",
        )

    return records[:limit] if limit else records





