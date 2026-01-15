from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import concurrent.futures

app = Flask(__name__)
CORS(app)

# Registro de los microservicios regionales
REGIONAL_APIS = [
    'http://localhost:5010/api/search/cv',   # API CV
    'http://localhost:5020/api/search/cat',  # API CAT (Debes crearla)
    'http://localhost:5030/api/search/gal'   # API GAL (Debes crearla)
]

def query_service(url, params):
    """Función auxiliar para llamar a una API regional"""
    try:
        response = requests.get(url, params=params, timeout=2)
        if response.status_code == 200:
            return response.json().get('results', [])
    except Exception as e:
        print(f"⚠️ Error contactando {url}: {e}")
    return []

@app.route('/api/search', methods=['GET'])
def search_global():
    params = request.args.to_dict() # Pasa los mismos filtros (localidad, tipo, etc)
    all_results = []

    # Llamada paralela a las 3 APIs para que sea rápido
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(query_service, url, params) for url in REGIONAL_APIS]
        for future in concurrent.futures.as_completed(futures):
            all_results.extend(future.result())

    return jsonify({
        'status': 'success',
        'total_results': len(all_results),
        'results': all_results
    })

if __name__ == '__main__':
    print("🌍 API Busqueda GLOBAL (Orquestador) corriendo en puerto 5004")
    app.run(host='127.0.0.1', port=5004)