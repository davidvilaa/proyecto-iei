import subprocess
import sys
import time
import os

APIS = [
    {'name': 'Wrapper CAT', 'file': 'api_wrapper_cat.py', 'port': 5001},
    {'name': 'Wrapper GAL', 'file': 'api_wrapper_gal.py', 'port': 5002},
    {'name': 'Wrapper CV', 'file': 'api_wrapper_cv.py', 'port': 5003},
    {'name': 'API Búsqueda', 'file': 'api_busqueda.py', 'port': 5004},
    {'name': 'API Carga', 'file': 'api_carga.py', 'port': 5005}
]

processes = []

def start_api(api_info):
    try:
        print(f"🚀 Iniciando {api_info['name']} en puerto {api_info['port']}...")
        process = subprocess.Popen(
            [sys.executable, api_info['file']],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return process
    except Exception as e:
        print(f"❌ Error iniciando {api_info['name']}: {e}")
        return None

def main():
    print("=" * 60)
    print("   🎯 INICIANDO 5 APIs REST DEL PROYECTO ITV")
    print("=" * 60)
    
    for api in APIS:
        if not os.path.exists(api['file']):
            print(f"❌ ERROR: No se encuentra {api['file']}")
            return
    
    print("\n📦 Todos los archivos encontrados\n")
    
    for api in APIS:
        process = start_api(api)
        if process:
            processes.append({'info': api, 'process': process})
            time.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ TODAS LAS APIs INICIADAS CORRECTAMENTE")
    print("=" * 60)
    print("\n📌 URLs disponibles:")
    for api in APIS:
        print(f"   • {api['name']}: http://localhost:{api['port']}")
    
    print("\n🌐 Abre index.html en Live Server para usar el frontend")
    print("\n⚠️  Presiona Ctrl+C para detener todas las APIs\n")
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n\n🛑 Deteniendo todas las APIs...")
        for p in processes:
            p['process'].terminate()
            print(f"   ✓ {p['info']['name']} detenida")
        print("\n👋 Todas las APIs cerradas. ¡Hasta luego!\n")

if __name__ == '__main__':
    main()
