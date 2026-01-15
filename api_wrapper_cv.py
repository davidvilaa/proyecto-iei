from flask import Flask, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

CV_JSON = 'estaciones.json'

@app.route('/api/wrapper-cv', methods=['GET'])
def wrapper_cv():
    """Devuelve datos CV desde JSON"""
    try:
        if os.path.exists(CV_JSON):
            with open(CV_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return jsonify({
                'status': 'success',
                'region': 'CV',
                'source': 'estaciones.json',
                'total_records': len(data),
                'data': data
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'JSON no encontrado: {CV_JSON}'
            }), 404
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    print("🚀 API Wrapper CV corriendo en http://localhost:5003")
    app.run(host='127.0.0.1', port=5003, debug=False, use_reloader=False)
