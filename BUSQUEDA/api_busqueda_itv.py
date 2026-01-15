from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter


# ========= Config =========
BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = BASE_DIR / "iei-proyecto-firebase-adminsdk-fbsvc-04d774ba06.json"

DEFAULT_LIMIT = 500
MAX_LIMIT = 2000


# ========= App =========
app = FastAPI(title="API de búsqueda ITV", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(str(CREDENTIALS_FILE)))
    return firestore.client()


def to_float(x) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", ".")
    if s == "" or s == "0":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def norm_tipo(ui_tipo: Optional[str]) -> Optional[str]:
    if not ui_tipo:
        return None
    t = ui_tipo.strip()
    if t.lower() in ("estación fija", "estacion fija"):
        return "Estación_fija"
    if t.lower() in ("estación móvil", "estacion movil", "estación movil"):
        return "Estación_movil"
    return t


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/estaciones")
def buscar_estaciones(
    localidad: Optional[str] = Query(default=None),
    cp: Optional[str] = Query(default=None),
    provincia: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    db = get_db()

    localidad_q = (localidad or "").strip().lower()
    provincia_q = (provincia or "").strip().lower()
    cp_q = (cp or "").strip()
    tipo_q = norm_tipo(tipo)

    # ========= Cargar SIEMPRE diccionarios (para devolver siempre localidad/provincia) =========
    loc_by_codigo: dict[str, dict] = {}
    for d in db.collection("localidades").stream():
        info = d.to_dict() or {}
        codigo = str(info.get("codigo", "") or d.id)
        loc_by_codigo[codigo] = info

    prov_by_codigo: dict[str, dict] = {}
    for d in db.collection("provincias").stream():
        info = d.to_dict() or {}
        codigo = str(info.get("codigo", "") or d.id)
        prov_by_codigo[codigo] = info

    # ========= Resolver provincia_codigo (por nombre) =========
    provincia_codigo: Optional[str] = None
    if provincia_q:
        # match flexible (contains) para que no dependa de mayúsculas/minúsculas
        matches = []
        for codigo, p in prov_by_codigo.items():
            nombre = str(p.get("nombre", "") or "").lower()
            if provincia_q == nombre:
                provincia_codigo = codigo
                break
            if provincia_q in nombre:
                matches.append(codigo)
        if provincia_codigo is None:
            provincia_codigo = matches[0] if matches else None
        if provincia_codigo is None:
            return {"count": 0, "estaciones": []}

    # ========= Resolver localidad_codigos (por nombre y/o provincia_codigo) =========
    localidad_codigos: Optional[set[str]] = None
    if localidad_q or provincia_codigo:
        cands = set()
        for codigo, l in loc_by_codigo.items():
            nombre = str(l.get("nombre", "") or "").lower()
            prov_cod = str(l.get("provincia_codigo", "") or "")
            if provincia_codigo and prov_cod != provincia_codigo:
                continue
            if localidad_q and (localidad_q not in nombre):
                continue
            cands.add(codigo)

        if not cands:
            return {"count": 0, "estaciones": []}
        localidad_codigos = cands

    # ========= Query estaciones (filtros directos) =========
    q = db.collection("estaciones")
    if cp_q:
        q = q.where(filter=FieldFilter("codigo_postal", "==", cp_q))
    if tipo_q:
        q = q.where(filter=FieldFilter("tipo", "==", tipo_q))

    docs = list(q.limit(limit).stream())

    # ========= Construir respuesta (con localidad/provincia SIEMPRE) =========
    estaciones = []
    for d in docs:
        e = d.to_dict() or {}

        loc_codigo = str(e.get("localidad_codigo", "") or "")
        if localidad_codigos is not None and loc_codigo not in localidad_codigos:
            continue

        loc_info = loc_by_codigo.get(loc_codigo, {})
        loc_nombre = str(loc_info.get("nombre", "") or "")

        prov_codigo = str(loc_info.get("provincia_codigo", "") or "")
        prov_info = prov_by_codigo.get(prov_codigo, {})
        prov_nombre = str(prov_info.get("nombre", "") or "")

        lat = to_float(e.get("latitud"))
        lon = to_float(e.get("longitud"))

        estaciones.append(
            {
                "id": d.id,
                "nombre": e.get("nombre", ""),
                "tipo": e.get("tipo", ""),
                "direccion": e.get("direccion", ""),
                "localidad": loc_nombre,
                "provincia": prov_nombre,
                "codigo_postal": e.get("codigo_postal", ""),
                "descripcion": e.get("descripcion", ""),
                "horario": e.get("horario", ""),
                "contacto": e.get("contacto", ""),
                "URL": e.get("URL", ""),
                "latitud": lat,
                "longitud": lon,
            }
        )

        if len(estaciones) >= limit:
            break

    return {"count": len(estaciones), "estaciones": estaciones}
