from flask import Flask, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

CAT_JSON = 'datos_cat_temp.json'

@app.route('/api/wrapper-cat', methods=['GET'])
def wrapper_cat():
    """Devuelve datos CAT desde JSON"""
    try:
        if os.path.exists(CAT_JSON):
            with open(CAT_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return jsonify({
                'status': 'success',
                'region': 'CAT',
                'source': 'datos_cat_temp.json',
                'total_records': len(data),
                'data': data
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'JSON no encontrado: {CAT_JSON}'
            }), 404
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    print("🚀 API Wrapper CAT corriendo en http://localhost:5001")
    app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)
