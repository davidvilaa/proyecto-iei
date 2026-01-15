# src/gal/api_busqueda_gal.py
from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import re

# Import sin punto
from wrapper_gal import leer_gal_csv 

app = FastAPI(title="Microservicio GAL - API de búsqueda")

# --- CORS OBLIGATORIO ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RUTA AL ARCHIVO CSV (Robusta)
CSV_FILE = Path(__file__).resolve().parent / "Estacions_ITV.csv"
print(f"DEBUG: Buscando archivo en {CSV_FILE} - ¿Existe? {CSV_FILE.exists()}")

def parse_coord_gmaps(coord_str: str):
    """Convierte 43° 18.856' a 43.3142 decimal"""
    if not coord_str: return 0.0, 0.0
    try:
        # Limpiamos caracteres raros
        coord_str = coord_str.replace("'", "").replace("°", "").replace(",", ".")
        parts = coord_str.split() # Separa lat y long
        
        def to_dec(val):
            # Lógica simple: si viene como 43 18.856, lo sumamos
            # Nota: Esto es una aproximación rápida para tu formato
            if len(parts) >= 2:
                # Tu CSV viene tipo: "43 18.856, -8 17.165" tras limpiar
                pass
            return 0.0 # Placeholder si falla
            
        # MEJOR O MÁS FÁCIL: Usar el parseo que tenías en el extractor
        # Pero para hacerlo rápido en la API, vamos a intentar extraer los números
        nums = re.findall(r"([-+]?\d+\.?\d*)", coord_str)
        if len(nums) >= 4:
            # Formato: Grados Lat, Min Lat, Grados Long, Min Long
            lat = float(nums[0]) + (float(nums[1]) / 60)
            lng = float(nums[2]) - (float(nums[3]) / 60) # Ojo al negativo en longitud
            # Corrección signo longitud si es oeste
            if "W" in coord_str or "-" in coord_str.split(',')[1]: 
                lng = -abs(lng)
            return lat, lng
    except:
        pass
    return 42.88, -8.54 # Fallback centro Galicia

# --- ENDPOINT RAW ---
@app.get("/gal/records")
def gal_records(limit: int | None = Query(default=None)):
    if not CSV_FILE.exists():
        raise HTTPException(status_code=404, detail=f"No se encuentra el archivo: {CSV_FILE.name}")
    records = leer_gal_csv(CSV_FILE)
    return records[:limit] if limit else records

# --- ENDPOINT BÚSQUEDA ---
@app.get("/api/search/gal")
def search_gal(
    localidad: str = "", 
    tipo: str = "", 
    cp: str = "", 
    provincia: str = ""
):
    print(f"🔎 Buscando en GAL: loc='{localidad}'")

    if not CSV_FILE.exists():
        print(f"⚠️ Archivo no encontrado: {CSV_FILE}")
        return {"status": "success", "results": []}

    # 1. Obtener datos raw
    records = leer_gal_csv(CSV_FILE)
    
    # 2. Filtrar
    resultados = []
    localidad = localidad.lower()
    tipo = tipo.lower()
    provincia = provincia.lower()
    
    for r in records:
        # Mapeo de campos específicos de GAL
        r_loc = str(r.get("CONCELLO", "")).lower()
        r_cp = str(r.get("CÓDIGO POSTAL", "") or r.get("C.POSTAL", ""))
        r_prov = str(r.get("PROVINCIA", "")).lower()
        r_nombre = str(r.get("NOME DA ESTACIÓN", "Estación GAL"))
        
        # Inferencia de tipo
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
            # USAR LA NUEVA FUNCIÓN
            coord_raw = r.get("COORDENADAS GMAPS", "")
            lat, lng = parse_coord_gmaps(coord_raw)

            resultados.append({
                "nombre": r_nombre,
                "tipo": r_tipo_inferred.capitalize(),
                "direccion": r.get("ENDEREZO", ""),
                "localidad": r.get("CONCELLO", ""),
                "cp": r.get("CÓDIGO POSTAL", ""),
                "provincia": r.get("PROVINCIA", ""),
                "lat": lat,  # <--- Usar variable calculada
                "lng": lng,  # <--- Usar variable calculada
                "descripcion": r.get("HORARIO", "")
            })
            
    return {"status": "success", "results": resultados}

if __name__ == "__main__":
    print(f"🚀 Iniciando API GAL en puerto 5030. Leyendo: {CSV_FILE}")
    uvicorn.run(app, host="127.0.0.1", port=5030)