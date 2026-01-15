# src/gal/api_busqueda_gal.py
from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query

from .wrapper_gal import leer_gal_csv

app = FastAPI(
    title="Wrapper GAL - API de búsqueda",
    version="1.0.0",
    description="Expone datos crudos de la fuente GAL (CSV) para que los consuma el extractor.",
)  # FastAPI básico: instancia + decoradores @app.get(...) [web:57]

# Ajusta esta ruta según dónde tengas el CSV en tu proyecto
CSV_FILE = Path("Estacions_ITV.csv")





@app.get("/health")
def health():
    """
    Endpoint típico de salud:
    - Sirve para saber si el servicio está levantado
    - Y si el CSV está disponible
    """
    return {
        "status": "ok",
        "csv_exists": CSV_FILE.exists(),
        "csv_path": str(CSV_FILE.resolve()),
    }


@app.get("/gal/records")
def gal_records(
    limit: int | None = Query(default=None, ge=1, le=20000),
):
    """
    Devuelve los registros raw (tal cual salen del CSV).
    - limit es opcional para no devolver miles de filas durante pruebas.
    """
    records = leer_gal_csv(CSV_FILE)

    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudieron leer registros. ¿Existe el CSV en {CSV_FILE.resolve()}?",
        )

    return records[:limit] if limit else records





