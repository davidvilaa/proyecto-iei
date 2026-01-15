from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import concurrent.futures

app = Flask(__name__)
# Habilitar CORS para que el frontend (puerto 5500/8080) pueda llamarnos
CORS(app)

# URLs de los microservicios regionales
REGIONAL_APIS = [
    'http://localhost:5010/api/search/cv',   # CV
    'http://localhost:5020/api/search/cat',  # CAT
    'http://localhost:5030/api/search/gal'   # GAL
]

def query_service(url, params):
    """Llama a un microservicio regional con timeout"""
    try:
        # Timeout de 5s para evitar bloqueos si un microservicio va lento
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Aseguramos devolver la lista de resultados
            return data.get('results', [])
    except Exception as e:
        print(f"⚠️ Error contactando {url}: {e}")
    return []

@app.route('/api/search', methods=['GET'])
def search_global():
    params = request.args.to_dict()
    print(f"🌍 Búsqueda global recibida: {params}")
    
    all_results = []

    # Llamada paralela a los 3 microservicios
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(query_service, url, params) for url in REGIONAL_APIS]
        for future in concurrent.futures.as_completed(futures):
            all_results.extend(future.result())

    print(f"✅ Total resultados encontrados: {len(all_results)}")
    
    return jsonify({
        'status': 'success',
        'total_results': len(all_results),
        'results': all_results
    })

if __name__ == '__main__':
    print("============== ORQUESTADOR DE BÚSQUEDA ==============")
    print("🌍 Escuchando en http://localhost:5004")
    app.run(host='127.0.0.1', port=5004, debug=True, use_reloader=False)