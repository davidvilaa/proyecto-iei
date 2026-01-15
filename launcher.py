import subprocess
import webbrowser
import time
import os
import sys

def main():
    print("=" * 70)
    print("              🚀 LANZADOR PROYECTO ITV")
    print("=" * 70)
    print("\n📦 Iniciando APIs...\n")
    
    # Lista de APIs
    apis = [
        {'name': 'API Wrapper CAT', 'file': 'api_wrapper_cat.py'},
        {'name': 'API Wrapper GAL', 'file': 'api_wrapper_gal.py'},
        {'name': 'API Wrapper CV', 'file': 'api_wrapper_cv.py'},
        {'name': 'API Búsqueda', 'file': 'api_busqueda.py'},
        {'name': 'API Carga', 'file': 'api_carga.py'}
    ]
    
    # Verificar archivos
    for api in apis:
        if not os.path.exists(api['file']):
            print(f"❌ ERROR: No se encuentra {api['file']}")
            input("\nPresiona Enter para salir...")
            return
    
    # Iniciar cada API en ventana CMD separada
    for api in apis:
        print(f"  ✓ Iniciando {api['name']}...")
        subprocess.Popen(
            f'start "ITV - {api["name"]}" cmd /k python {api["file"]}',
            shell=True
        )
        time.sleep(1)
    
    print("\n✅ Todas las APIs iniciadas\n")
    print("⏳ Esperando 3 segundos para que las APIs estén listas...\n")
    time.sleep(3)
    
    # Abrir navegador con el frontend
    html_path = os.path.abspath('index.html')
    if os.path.exists(html_path):
        print(f"🌐 Abriendo navegador: {html_path}\n")
        webbrowser.open(f'file:///{html_path}')
    else:
        print("❌ ERROR: No se encuentra index.html")
        input("\nPresiona Enter para salir...")
        return
    
    print("=" * 70)
    print("✅ PROYECTO ITV INICIADO CORRECTAMENTE")
    print("=" * 70)
    print("\n📌 APIs corriendo en:")
    print("   • http://localhost:5001 (Wrapper CAT)")
    print("   • http://localhost:5002 (Wrapper GAL)")
    print("   • http://localhost:5003 (Wrapper CV)")
    print("   • http://localhost:5004 (API Búsqueda)")
    print("   • http://localhost:5005 (API Carga)")
    print("\n⚠️  Para detener: cierra las ventanas CMD")
    print("\n" + "=" * 70)
    
    input("\nPresiona Enter para cerrar este lanzador...")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        input("\nPresiona Enter para salir...")
