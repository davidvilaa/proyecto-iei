from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

JSON_FILES = {
    'CAT': 'datos_cat_temp.json',
    'GAL': 'datos_gal_temp.json',
    'CV': 'estaciones.json'
}

@app.route('/api/search', methods=['GET'])
def search_stations():
    """Busca estaciones en los 3 JSONs"""
    try:
        localidad = request.args.get('localidad', '').lower()
        tipo = request.args.get('tipo', '').lower()
        cp = request.args.get('cp', '')
        provincia = request.args.get('provincia', '').lower()
        
        all_stations = []
        
        for region, filepath in JSON_FILES.items():
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        all_stations.extend(data)
                    print(f"✅ Cargados {len(data)} registros de {filepath}")
                except Exception as e:
                    print(f"❌ Error leyendo {filepath}: {e}")
            else:
                print(f"⚠️  Archivo no encontrado: {filepath}")
        
        results = []
        for station in all_stations:
            localidad_val = str(station.get('municipi') or 
                              station.get('CONCELLO') or 
                              station.get('MUNICIPIO') or '').lower()
            
            cp_val = str(station.get('cp') or 
                        station.get('CÓDIGO POSTAL') or 
                        station.get('C.POSTAL') or '')
            
            provincia_val = str(station.get('serveis_territorials') or 
                               station.get('PROVINCIA') or '').lower()
            
            match = True
            if localidad and localidad not in localidad_val:
                match = False
            if cp and cp not in cp_val:
                match = False
            if provincia and provincia not in provincia_val:
                match = False
            
            if match:
                results.append(station)
        
        print(f"🔍 Búsqueda completada: {len(results)} resultados")
        
        return jsonify({
            'status': 'success',
            'total_results': len(results),
            'results': results[:100]
        }), 200
        
    except Exception as e:
        print(f"❌ Error en búsqueda: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🔍 API Búsqueda corriendo en http://localhost:5004")
    print("=" * 60)
    print("\nArchivos JSON esperados:")
    for name, path in JSON_FILES.items():
        status = "✅" if os.path.exists(path) else "❌"
        print(f"  {status} {name}: {path}")
    print("\n" + "=" * 60)
    app.run(host='127.0.0.1', port=5004, debug=False, use_reloader=False)
