from __future__ import annotations

import sys
import time
import subprocess
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import firebase_admin
from firebase_admin import credentials, firestore


# Carpeta raíz del proyecto (…/IEI_FINAL2/IEI_FINAL2)
BASE_DIR = Path(__file__).resolve().parent.parent

# Credenciales (como lo llevas “ahora”: por nombre de fichero)
CREDENTIALS_FILE = BASE_DIR / "iei-proyecto-firebase-adminsdk-fbsvc-04d774ba06.json"

WAREHOUSE_COLLECTIONS = ["provincias", "localidades", "estaciones"]

EXTRACTOR_FILES = {
    "GAL": BASE_DIR / "GAL" / "extractor_gal.py",
    "CAT": BASE_DIR / "CAT" / "extractor_cat.py",
    "CV":  BASE_DIR / "CV" / "extractor_cv.py",
}

Source = Literal["GAL", "CAT", "CV"]


app = FastAPI(title="API Carga", version="1.0.0")

# Para que tu interfaz (otro puerto) pueda llamar sin problemas
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)  # CORS en FastAPI se configura con CORSMiddleware. [web:336]


class LoadRequest(BaseModel):
    sources: list[Source]
    clear_before: bool = False


def get_db():
    if not CREDENTIALS_FILE.exists():
        raise RuntimeError(f"No encuentro credenciales: {CREDENTIALS_FILE}")

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(str(CREDENTIALS_FILE)))

    return firestore.client()


def delete_collection(db, collection_name: str, batch_size: int = 400) -> int:
    deleted = 0
    while True:
        docs = list(db.collection(collection_name).limit(batch_size).stream())
        if not docs:
            break
        batch = db.batch()
        for doc in docs:
            batch.delete(doc.reference)
        batch.commit()
        deleted += len(docs)
    return deleted  # La idea de borrar por lotes es la recomendada por la doc. [web:335]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/clear")
def clear():
    db = get_db()
    deleted = {col: delete_collection(db, col) for col in WAREHOUSE_COLLECTIONS}
    return {"cleared": True, "deleted_docs": deleted}


@app.post("/load")
def load(req: LoadRequest):
    if not req.sources:
        raise HTTPException(status_code=400, detail="sources no puede estar vacío")

    # Validación de rutas
    for s in req.sources:
        if not EXTRACTOR_FILES[s].exists():
            raise HTTPException(status_code=500, detail=f"No existe extractor: {EXTRACTOR_FILES[s]}")

    if req.clear_before:
        clear()

    results = {}
    for s in req.sources:
        t0 = time.time()
        proc = subprocess.run(
            [sys.executable, str(EXTRACTOR_FILES[s])],
            cwd=str(BASE_DIR),              # para que encuentre fuentes/credenciales como lo tienes ahora
            capture_output=True,
            text=True,
        )  # Ejecutar scripts y devolver salida es un patrón típico con subprocess. [web:326]

        results[s] = {
            "ok": proc.returncode == 0,
            "seconds": round(time.time() - t0, 2),
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[-8000:],
            "stderr": (proc.stderr or "")[-8000:],
        }

    return {"requested": req.sources, "results": results}


