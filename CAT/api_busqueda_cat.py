# src/cat/api_busqueda_cat.py
from fastapi.middleware.cors import CORSMiddleware
from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
import uvicorn

from .wrapper_cat import leer_cat_xml

app = FastAPI(
    title="Microservicio CAT - API de búsqueda",
    version="1.0.0",
    description="API de búsqueda y datos crudos para Catalunya."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite peticiones desde cualquier origen (frontend)
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],
)

XML_FILE = Path("ITV-CAT.xml")

# --- ENDPOINT EXISTENTE (Para el extractor) ---
@app.get("/cat/records")
def cat_records(limit: int | None = Query(default=None)):
    records = leer_cat_xml(XML_FILE)
    if not records:
        raise HTTPException(status_code=404, detail="No se encontraron registros")
    return records[:limit] if limit else records

# --- NUEVO ENDPOINT (Para el buscador) ---
@app.get("/api/search/cat")
def search_cat(
    localidad: str = "", 
    tipo: str = "", 
    cp: str = "", 
    provincia: str = ""
):
    # 1. Obtener datos raw
    records = leer_cat_xml(XML_FILE)
    
    # 2. Filtrar
    resultados = []
    localidad = localidad.lower()
    tipo = tipo.lower()
    provincia = provincia.lower()
    
    for r in records:
        # Mapeo de campos específicos de CAT
        r_loc = str(r.get("municipi", "")).lower()
        r_cp = str(r.get("cp", ""))
        # En CAT, 'serveis_territorials' suele actuar como provincia administrativa
        r_prov = str(r.get("serveis_territorials", "")).lower()
        
        # Inferencia de tipo (por defecto fija)
        r_tipo_inferred = "fija"
        # Si hubiera algún campo específico se usaría aquí

        match = True
        if localidad and localidad not in r_loc: match = False
        if cp and cp not in r_cp: match = False
        # Filtro provincia: a veces el usuario busca "Barcelona" y en el XML pone "Barcelona"
        if provincia and provincia not in r_prov: match = False
        
        if tipo and tipo != r_tipo_inferred: 
            # Si buscas 'movil' y todas son fijas, no saldrá nada, lo cual es correcto
            match = False

        if match:
            # Normalizar salida
            # Parseo básico de coordenadas si vienen en formato string grande (ej: 41399458)
            lat_raw = r.get("lat", "0")
            lng_raw = r.get("long", "0")
            try:
                lat = float(lat_raw) / 1000000 if float(lat_raw) > 1000 else float(lat_raw)
                lng = float(lng_raw) / 1000000 if float(lng_raw) > 1000 else float(lng_raw)
            except:
                lat, lng = 41.38, 2.17 # Default Barcelona

            resultados.append({
                "nombre": r.get("denominaci", "ITV CAT"),
                "tipo": "Fija", # Hardcoded si no hay info
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
    print("🚀 Iniciando Microservicio CAT en puerto 5020...")
    uvicorn.run(app, host="127.0.0.1", port=5020)