# src/cat/api_busqueda_cat.py
from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# IMPORT SIN EL PUNTO (Correcto para ejecución directa)
from wrapper_cat import leer_cat_xml

app = FastAPI(title="Microservicio CAT - API de búsqueda")

# --- CORS OBLIGATORIO ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RUTA AL ARCHIVO XML
# Usamos .parent para que busque "ITV-CAT.xml" en la carpeta CAT, no en la raíz
XML_FILE = Path(__file__).resolve().parent / "ITV-CAT.xml"

# --- ENDPOINT RAW ---
@app.get("/cat/records")
def cat_records(limit: int | None = Query(default=None)):
    # Verificación defensiva para no crashear si falta el archivo
    if not XML_FILE.exists():
        # Retornamos error 404 pero la API sigue viva
        raise HTTPException(status_code=404, detail=f"No se encuentra el archivo: {XML_FILE.name}")
        
    records = leer_cat_xml(XML_FILE)
    return records[:limit] if limit else records

# --- ENDPOINT BÚSQUEDA ---
@app.get("/api/search/cat")
def search_cat(
    localidad: str = "", 
    tipo: str = "", 
    cp: str = "", 
    provincia: str = ""
):
    print(f"🔎 Buscando en CAT: loc='{localidad}'")
    
    # 1. Leer datos
    if not XML_FILE.exists():
        print(f"⚠️ Archivo no encontrado: {XML_FILE}")
        return {"status": "success", "results": []} # Devolvemos vacio, no error 500
        
    records = leer_cat_xml(XML_FILE)
    
    # 2. Filtrar
    resultados = []
    localidad = localidad.lower()
    tipo = tipo.lower()
    provincia = provincia.lower()
    
    for r in records:
        # Mapeo específico de CAT
        r_loc = str(r.get("municipi", "")).lower()
        r_cp = str(r.get("cp", ""))
        r_prov = str(r.get("serveis_territorials", "")).lower()
        
        # Filtrado
        match = True
        if localidad and localidad not in r_loc: match = False
        if cp and cp not in r_cp: match = False
        if provincia and provincia not in r_prov: match = False
        
        if match:
            # Normalización de coordenadas
            lat_raw = r.get("lat", "0")
            lng_raw = r.get("long", "0")
            try:
                lat = float(lat_raw)
                lng = float(lng_raw)
                # Ajuste si vienen sin punto decimal (ej: 41380000 -> 41.38)
                if lat > 1000: lat /= 1000000
                if lng > 1000: lng /= 1000000
            except:
                lat, lng = 0.0, 0.0

            resultados.append({
                "nombre": r.get("denominaci", "ITV CAT"),
                "tipo": "Fija",
                "direccion": r.get("adre_a", ""),
                "localidad": r.get("municipi", ""),
                "cp": r.get("cp", ""),
                "provincia": r.get("serveis_territorials", ""),
                "lat": lat,
                "lng": lng,
                "descripcion": r.get("horari_de_servei", "")
            })
            
    return {"status": "success", "results": resultados}

# --- ARRANQUE ---
if __name__ == "__main__":
    print(f"🚀 Iniciando API CAT en puerto 5020. Leyendo: {XML_FILE}")
    uvicorn.run(app, host="127.0.0.1", port=5020)