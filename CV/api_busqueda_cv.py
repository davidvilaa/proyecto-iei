# src/cv/api_busqueda_cv.py
from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query

from .wrapper_cv import leer_cv_json

app = FastAPI(
    title="Wrapper CV - API de búsqueda",
    version="1.0.0",
    description="Expone datos crudos de la fuente CV (JSON) para que los consuma el extractor.",
)

JSON_FILE = Path("estaciones.json")



@app.get("/health")
def health():
    return {
        "status": "ok",
        "json_exists": JSON_FILE.exists(),
        "json_path": str(JSON_FILE.resolve()),
    }




@app.get("/cv/records")
def cv_records(
    limit: int | None = Query(default=None, ge=1, le=50000),
):
    """
    Devuelve registros RAW del JSON (sin modificar).
    limit es útil para pruebas.
    """
    records = leer_cv_json(JSON_FILE)

    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudieron leer registros. ¿Existe el JSON en {JSON_FILE.resolve()}?",
        )

    return records[:limit] if limit else records



