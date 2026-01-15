# CARGA/api_carga.py
from __future__ import annotations
import os
import shutil
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Microservicio de Carga")

# --- CORS (Crucial para que el frontend pueda conectar) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/load")
async def load_data(
    archivo: UploadFile = File(...),
    fuente: str = Form(...)
):
    """
    Recibe el archivo y simula el proceso de carga guardándolo en /datos
    """
    try:
        if not archivo.filename:
            raise HTTPException(status_code=400, detail="No se proporcionó archivo")
        
        # Crear carpeta datos si no existe
        os.makedirs('datos', exist_ok=True)
        
        # Guardar el archivo físicamente
        file_path = Path("datos") / archivo.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(archivo.file, buffer)
            
        print(f"📥 Archivo recibido: {archivo.filename} ({fuente})")
        
        # Simulación de respuesta (Mock)
        # En el futuro aquí llamarías a los extractores reales
        return {
            'status': 'success',
            'fuente': fuente,
            'registros_ok': 15,
            'registros_reparados': 0,
            'registros_rechazados': 0,
            'warnings': 0,
            'detalles_reparados': [],
            'detalles_rechazados': [],
            'log_completo': f'Archivo {archivo.filename} guardado correctamente en la carpeta datos/.'
        }
        
    except Exception as e:
        print(f"❌ Error en carga: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    print("🚀 API Carga corriendo en puerto 5005")
    # Usamos uvicorn igual que en las otras APIs
    uvicorn.run(app, host='127.0.0.1', port=5005)