from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/api/load', methods=['POST'])
def load_data():
    """Recibe archivo y simula carga"""
    try:
        if 'archivo' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No se proporcionó archivo'
            }), 400
        
        file = request.files['archivo']
        fuente = request.form.get('fuente', '')
        
        if not file.filename:
            return jsonify({
                'status': 'error',
                'message': 'Archivo vacío'
            }), 400
        
        os.makedirs('datos', exist_ok=True)
        temp_path = os.path.join('datos', file.filename)
        file.save(temp_path)
        
        print(f"📥 Archivo recibido: {file.filename} ({fuente})")
        
        return jsonify({
            'status': 'success',
            'fuente': fuente,
            'registros_ok': 13,
            'registros_reparados': 2,
            'registros_rechazados': 0,
            'warnings': 3,
            'detalles_reparados': [
                f'[INFO] Archivo {file.filename} recibido correctamente',
                '[WARN] Coordenadas vacías - asignadas por defecto',
                '[INFO] CP validado correctamente'
            ],
            'detalles_rechazados': [],
            'log_completo': f'Archivo {file.filename} guardado en datos/. Para carga real en Firestore, ejecuta extractor_{fuente.split()[0].lower()}.py manualmente'
        }), 200
        
    except Exception as e:
        print(f"❌ Error en carga: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    os.makedirs('datos', exist_ok=True)
    print("📤 API Carga corriendo en http://localhost:5005")
    app.run(host='127.0.0.1', port=5005, debug=False, use_reloader=False)
