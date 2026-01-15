from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import concurrent.futures

app = Flask(__name__)
CORS(app)

# URLs de los microservicios regionales (coinciden con tu launcher.py)
REGIONAL_APIS = [
    'http://localhost:5010/api/search/cv',   # Microservicio CV
    'http://localhost:5020/api/search/cat',  # Microservicio CAT
    'http://localhost:5030/api/search/gal'   # Microservicio GAL
]

def query_service(url, params):
    """Llama a un microservicio regional con timeout"""
    try:
        # Timeout de 5s para dar tiempo a leer archivos grandes
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            return response.json().get('results', [])
    except Exception as e:
        print(f"⚠️ Error contactando {url}: {e}")
    return []

@app.route('/api/search', methods=['GET'])
def search_global():
    params = request.args.to_dict()
    all_results = []

    print(f"🌍 Iniciando búsqueda global: {params}")

    # Peticiones en paralelo a los 3 microservicios
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
    print("🌍 API Orquestador corriendo en puerto 5004")
    app.run(host='127.0.0.1', port=5004)