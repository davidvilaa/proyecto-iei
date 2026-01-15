import subprocess
import webbrowser
import time
import os
import sys

def main():
    print("=" * 70)
    print("              🚀 LANZADOR PROYECTO ITV (MICROSERVICIOS)")
    print("=" * 70)
    print("\n📦 Iniciando APIs Regionales y Globales...\n")
    
    # 1. ACTUALIZACIÓN: Lista de APIs con las nuevas rutas y nombres
    # Usamos os.path.join para asegurar compatibilidad con Windows/Linux
    apis = [
        # APIs Regionales (Microservicios)
        {
            'name': 'API CV (Valencia)', 
            'file': os.path.join('CV', 'api_busqueda_cv.py'),
            'port': 5010
        },
        {
            'name': 'API CAT (Catalunya)', 
            'file': os.path.join('CAT', 'api_busqueda_cat.py'),
            'port': 5020
        },
        {
            'name': 'API GAL (Galicia)', 
            'file': os.path.join('GAL', 'api_busqueda_gal.py'),
            'port': 5030
        },
        # APIs Globales
        {
            'name': 'API Carga Global', 
            'file': os.path.join('CARGA', 'api_carga.py'),
            'port': 5005
        },
        {
            'name': 'Orquestador Búsqueda', 
            'file': 'api_busqueda.py',
            'port': 5004
        }
    ]
    
    # Verificar archivos antes de lanzar
    missing_files = []
    for api in apis:
        if not os.path.exists(api['file']):
            missing_files.append(api['file'])
    
    if missing_files:
        print("❌ ERROR: No se encuentran los siguientes archivos:")
        for f in missing_files:
            print(f"   - {f}")
        print("\nAsegúrate de haber creado las carpetas CV, CAT, GAL, CARGA y movido los archivos.")
        input("\nPresiona Enter para salir...")
        return
    
    # Iniciar cada API en ventana CMD separada
    for api in apis:
        print(f"  ✓ Iniciando {api['name']}...")
        # Nota: cmd /k mantiene la ventana abierta si falla
        subprocess.Popen(
            f'start "ITV - {api["name"]}" cmd /k python {api["file"]}',
            shell=True
        )
        time.sleep(1) # Pequeña pausa para no saturar el arranque
    
    print("\n✅ Todas las APIs iniciadas\n")
    print("⏳ Esperando 5 segundos para que los servicios arranquen...\n")
    time.sleep(5)
    
    # Abrir navegador con el frontend
    html_path = os.path.abspath('index.html')
    if os.path.exists(html_path):
        print(f"🌐 Abriendo navegador: {html_path}\n")
        webbrowser.open(f'file:///{html_path}')
    else:
        print("❌ ERROR: No se encuentra index.html")
    
    print("=" * 70)
    print("✅ SISTEMA DE MICROSERVICIOS INICIADO")
    print("=" * 70)
    print("\n📌 Endpoints Activos:")
    print(f"   • Orquestador (Front): http://localhost:5004")
    print(f"   • API Carga:           http://localhost:5005")
    print(f"   • Microservicio CV:    http://localhost:5010")
    print(f"   • Microservicio CAT:   http://localhost:5020")
    print(f"   • Microservicio GAL:   http://localhost:5030")
    print("\n⚠️  Para detener: cierra las ventanas CMD generadas")
    print("\n" + "=" * 70)
    
    input("\nPresiona Enter para cerrar este lanzador...")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        input("\nPresiona Enter para salir...")