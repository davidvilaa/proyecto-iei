# src/gal/api_busqueda_gal.py
from __future__ import annotations
from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
import uvicorn

# Asegúrate de que este import funcione con tu estructura de carpetas
# Si te da error de import, verifica que existe __init__.py en la carpeta GAL
from .wrapper_gal import leer_gal_csv 

app = FastAPI(
    title="Microservicio GAL - API de búsqueda",
    version="1.0.0",
    description="API de búsqueda y datos crudos para Galicia."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite peticiones desde cualquier origen (frontend)
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],
)

CSV_FILE = Path("Estacions_ITV.csv") # O la ruta donde esté tu CSV/JSON real

# --- ENDPOINT EXISTENTE (Para el extractor) ---
@app.get("/gal/records")
def gal_records(limit: int | None = Query(default=None)):
    records = leer_gal_csv(CSV_FILE)
    if not records:
        raise HTTPException(status_code=404, detail="No se encontraron registros")
    return records[:limit] if limit else records

# --- NUEVO ENDPOINT (Para el buscador) ---
@app.get("/api/search/gal")
def search_gal(
    localidad: str = "", 
    tipo: str = "", 
    cp: str = "", 
    provincia: str = ""
):
    # 1. Obtener datos raw
    records = leer_gal_csv(CSV_FILE)
    
    # 2. Filtrar
    resultados = []
    localidad = localidad.lower()
    tipo = tipo.lower()
    provincia = provincia.lower()
    
    for r in records:
        # Mapeo de campos específicos de GAL (según tu JSON/CSV)
        # Ajusta las claves ("CONCELLO", "NOME...", etc) si tu CSV tiene otras cabeceras
        r_loc = str(r.get("CONCELLO", "")).lower()
        r_cp = str(r.get("CÓDIGO POSTAL", "") or r.get("C.POSTAL", ""))
        r_prov = str(r.get("PROVINCIA", "")).lower()
        r_nombre = str(r.get("NOME DA ESTACIÓN", "Estación GAL"))
        
        # Lógica de tipo (simple, ya que GAL no suele tener campo 'tipo' explícito)
        r_tipo_inferred = "fija"
        if "móvil" in r_nombre.lower() or "movil" in r_nombre.lower():
            r_tipo_inferred = "movil"

        match = True
        if localidad and localidad not in r_loc: match = False
        if cp and cp not in r_cp: match = False
        if provincia and provincia not in r_prov: match = False
        
        if tipo:
            if tipo == "fija" and r_tipo_inferred != "fija": match = False
            elif tipo == "movil" and r_tipo_inferred != "movil": match = False

        if match:
            # Normalizar salida estándar
            resultados.append({
                "nombre": r_nombre,
                "tipo": r_tipo_inferred.capitalize(),
                "direccion": r.get("ENDEREZO", ""),
                "localidad": r.get("CONCELLO", ""),
                "cp": r.get("CÓDIGO POSTAL", ""),
                "provincia": r.get("PROVINCIA", ""),
                "lat": 42.88, # Coordenada default Galicia si no parseas
                "lng": -8.54,
                "descripcion": r.get("HORARIO", "")
            })
            
    return {"status": "success", "results": resultados}

# --- ARRANQUE ---
if __name__ == "__main__":
    print("🚀 Iniciando Microservicio GAL en puerto 5030...")
    uvicorn.run(app, host="127.0.0.1", port=5030)