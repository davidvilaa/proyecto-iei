from flask import Flask, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

GAL_JSON = 'datos_gal_temp.json'

@app.route('/api/wrapper-gal', methods=['GET'])
def wrapper_gal():
    """Devuelve datos GAL desde JSON"""
    try:
        if os.path.exists(GAL_JSON):
            with open(GAL_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return jsonify({
                'status': 'success',
                'region': 'GAL',
                'source': 'datos_gal_temp.json',
                'total_records': len(data),
                'data': data
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'JSON no encontrado: {GAL_JSON}'
            }), 404
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    print("🚀 API Wrapper GAL corriendo en http://localhost:5002")
    app.run(host='127.0.0.1', port=5002, debug=False, use_reloader=False)
