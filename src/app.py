from flask import Flask, request, jsonify, send_from_directory
from print_label_html import app as label_app, print_label_for_record
from sqldb import Database
from datetime import datetime
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.register_blueprint(label_app)

# 設置基本認證
auth = HTTPBasicAuth()
users = {
    "share": generate_password_hash("share")
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

@app.route('/print_label/<serial_number>', methods=['POST', 'OPTIONS'])
def print_label(serial_number):
    """Handle print label request"""
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        timestamp = request.args.get('timestamp')
        if not timestamp:
            return jsonify({'success': False, 'message': 'Timestamp is required'})
            
        # 從數據庫獲取記錄
        with Database() as db:
            db.cursor.execute("""
                SELECT * FROM system_records 
                WHERE serialnumber = %(serialnumber)s 
                AND created_at = %(created_at)s
            """, {
                'serialnumber': serial_number,
                'created_at': datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            })
            record = db.cursor.fetchone()
            
            if not record:
                return jsonify({'success': False, 'message': 'Record not found'})
            
            success = print_label_for_record(record)
            if success:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'message': 'Failed to print label'})
                
    except Exception as e:
        print(f"Error in print_label_route: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)

# 添加 CORS 支持
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 