# src/cv/api_busqueda_cv.py
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from .wrapper_cv import leer_cv_json

app = FastAPI(title="Microservicio CV")
JSON_FILE = Path("estaciones.json") # Asegúrate que la ruta sea correcta relativa a la ejecución

# --- ENDPOINT EXISTENTE (Para el extractor) ---
@app.get("/cv/records")
def cv_records(limit: int | None = Query(default=None)):
    records = leer_cv_json(JSON_FILE)
    return records[:limit] if limit else records

# --- NUEVO ENDPOINT (Para el buscador) ---
@app.get("/api/search/cv")
def search_cv(
    localidad: str = "", 
    tipo: str = "", 
    cp: str = "", 
    provincia: str = ""
):
    # 1. Leer datos raw
    records = leer_cv_json(JSON_FILE)
    
    # 2. Filtrar
    resultados = []
    localidad = localidad.lower()
    tipo = tipo.lower()
    provincia = provincia.lower()
    
    for r in records:
        # Normalizar datos del registro actual para comparar
        # NOTA: Ajusta las claves según tu JSON (MUNICIPIO, C.POSTAL, etc)
        r_loc = str(r.get("MUNICIPIO", "")).lower()
        r_cp = str(r.get("C.POSTAL", ""))
        r_prov = str(r.get("PROVINCIA", "")).lower()
        r_tipo = str(r.get("TIPO ESTACIÓN", "")).lower()
        
        match = True
        if localidad and localidad not in r_loc: match = False
        if cp and cp not in r_cp: match = False
        if provincia and provincia not in r_prov: match = False
        # Filtro de tipo aproximado (ajusta según tus necesidades)
        if tipo:
            if tipo == "fija" and "fija" not in r_tipo: match = False
            elif tipo == "movil" and "móvil" not in r_tipo and "movil" not in r_tipo: match = False

        if match:
            # Normalizar salida para que el Front la entienda (igual que hacías en app.js)
            resultados.append({
                "nombre": r.get("MUNICIPIO", "Estación"), # Ojo, en tu JSON no hay campo nombre claro, usabas Municipio
                "tipo": r.get("TIPO ESTACIÓN"),
                "direccion": r.get("DIRECCIÓN"),
                "localidad": r.get("MUNICIPIO"),
                "cp": r.get("C.POSTAL"),
                "provincia": r.get("PROVINCIA"),
                "lat": 39.4699, # Placeholder o lógica real
                "lng": -0.3763
            })
            
    return {"status": "success", "results": resultados}

# --- ARRANQUE ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5010)