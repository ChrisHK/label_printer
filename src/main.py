from flask import Flask, send_file, send_from_directory
from csv_sync_manager import CSVSyncManager, start_monitoring
from initdb import create_tables, check_product_keys, check_system_records
from sqldb import Database
import webbrowser
from html_preview import generate_html_preview
import os
from print_label_html import app as label_blueprint, init_basic_auth
from threading import Thread

# Create Flask apppy
app = Flask(__name__, 
    static_url_path='',
    static_folder=os.path.join(os.path.dirname(__file__), 'static')
)

# Initialize basic auth
init_basic_auth(app)

# Register blueprint
app.register_blueprint(label_blueprint)

# 確保靜態文件夾存在
os.makedirs(app.static_folder, exist_ok=True)

@app.route('/')
def serve_preview():
    """Serve the preview HTML file"""
    preview_path = os.path.join(os.path.dirname(__file__), 'preview.html')
    return send_file(preview_path)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

def run_flask():
    """Run Flask server in a separate thread"""
    print("Starting Flask server...")
    try:
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Error starting Flask server: {str(e)}")

def initialize_database():
    """Initialize database if needed"""
    with Database() as db:
        db.cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'system_records'
            ) as exists;
        """)
        result = db.cursor.fetchone()
        tables_exist = result['exists']
    
    if not tables_exist:
        print("\nCreating database tables...")
        create_tables()
    else:
        print("\nTables already exist, skipping creation")

def main():
    # Initialize database
    initialize_database()
    
    # Start Flask server in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Generate preview and open in browser
    html_path = generate_html_preview()
    if html_path:
        print(f"\nOpening preview in browser: http://localhost:5000")
        webbrowser.open('http://localhost:5000')
    
    # Start file monitoring with new CSVSyncManager
    base_path = r"\\192.168.0.10\Files\03_IT\data"
    print("\nStarting file monitoring...")
    start_monitoring(base_path)

if __name__ == "__main__":
    main()