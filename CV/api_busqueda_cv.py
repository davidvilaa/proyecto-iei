# src/cv/api_busqueda_cv.py
from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import sin punto (para que funcione desde el launcher)
from wrapper_cv import leer_cv_json

app = FastAPI(title="Microservicio CV")

# --- CORS OBLIGATORIO ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RUTA AL ARCHIVO JSON (Robusta)
# Busca 'estaciones.json' en la carpeta CV, sin importar desde dónde ejecutes el script
JSON_FILE = Path(__file__).resolve().parent / "estaciones.json"
print(f"DEBUG: Buscando archivo en {JSON_FILE} - ¿Existe? {JSON_FILE.exists()}")

COORD_MAPPING = {
    "Vila-real": (39.937, -0.098),
    "Vinaròs": (40.468, 0.465),
    "Massalfassar": (39.560, -0.310),
    "Llíria": (39.626, -0.594),
    "Orihuela": (38.083, -0.944),
    "Alcoy": (38.705, -0.474),
    # Fallback para móviles
    "Móvil": (39.469, -0.376) 
}

# --- ENDPOINT RAW ---
@app.get("/cv/records")
def cv_records(limit: int | None = Query(default=None)):
    if not JSON_FILE.exists():
        raise HTTPException(status_code=404, detail=f"No se encuentra el archivo: {JSON_FILE.name}")
    records = leer_cv_json(JSON_FILE)
    return records[:limit] if limit else records

# --- ENDPOINT BÚSQUEDA ---
@app.get("/api/search/cv")
def search_cv(
    localidad: str = "", 
    tipo: str = "", 
    cp: str = "", 
    provincia: str = ""
):
    print(f"🔎 Buscando en CV: loc='{localidad}'")

    if not JSON_FILE.exists():
        print(f"⚠️ Archivo no encontrado: {JSON_FILE}")
        return {"status": "success", "results": []}

    # 1. Leer datos raw
    records = leer_cv_json(JSON_FILE)
    
    # 2. Filtrar
    resultados = []
    localidad = localidad.lower()
    tipo = tipo.lower()
    provincia = provincia.lower()
    
    for r in records:
        # Normalizar datos del registro actual para comparar
        r_loc = str(r.get("MUNICIPIO", "")).lower()
        r_cp = str(r.get("C.POSTAL", ""))
        r_prov = str(r.get("PROVINCIA", "")).lower()
        r_tipo = str(r.get("TIPO ESTACIÓN", "")).lower()
        
        match = True
        if localidad and localidad not in r_loc: match = False
        if cp and cp not in r_cp: match = False
        if provincia and provincia not in r_prov: match = False
        
        # Filtro de tipo aproximado
        if tipo:
            if tipo == "fija" and "fija" not in r_tipo: match = False
            elif tipo == "movil" and "móvil" not in r_tipo and "movil" not in r_tipo: match = False

        if match:
            # 2. BUSCAR COORDENADA POR MUNICIPIO
            municipio = r.get('MUNICIPIO', 'Desconocido')
            lat_fija, lng_fija = COORD_MAPPING.get(municipio, COORD_MAPPING["Móvil"])

            # Si es móvil y no tiene municipio, intenta variar un poco para que no se pisen
            if "Móvil" in str(r.get("TIPO ESTACIÓN")):
                 lat_fija += 0.01 # Pequeño desplazamiento

            resultados.append({
                "nombre": f"ITV {municipio}",
                "tipo": r.get("TIPO ESTACIÓN", "Fija"),
                "direccion": r.get("DIRECCIÓN", ""),
                "localidad": municipio,
                "cp": str(r.get("C.POSTAL", "")),
                "provincia": r.get("PROVINCIA", ""),
                "lat": lat_fija, # <--- Usar coordenada mapeada
                "lng": lng_fija  # <--- Usar coordenada mapeada
            })
            
    return {"status": "success", "results": resultados}

if __name__ == "__main__":
    print(f"🚀 Iniciando API CV en puerto 5010. Leyendo: {JSON_FILE}")
    uvicorn.run(app, host="127.0.0.1", port=5010)