import pandas as pd
import os
from sqldb import Database
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
from html_preview import generate_html_preview
import webbrowser
from datetime import datetime
from test_api import APIConnection, prepare_request_data
import json
from csv_sync_manager import start_monitoring

class DBUpdateHandler(FileSystemEventHandler):
    def __init__(self, target_file, update_function):
        self.target_file = target_file
        self.update_function = update_function
        self.last_modified = 0
        self.is_processing = False
        self.last_size = 0
        
    def wait_for_file_ready(self, file_path, timeout=10):
        """Wait for file write completion"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                current_size = os.path.getsize(file_path)
                if current_size == self.last_size:
                    time.sleep(1)
                    if current_size == os.path.getsize(file_path):
                        self.last_size = current_size
                        return True
                self.last_size = current_size
            except Exception:
                pass
            time.sleep(0.1)
        return False
    
    def on_modified(self, event):
        if self.is_processing:
            return
            
        if not event.is_directory and event.src_path.endswith(self.target_file):
            try:
                self.is_processing = True
                print("Waiting for file write completion...")
                if not self.wait_for_file_ready(event.src_path):
                    print("File write timeout")
                    return
                
                current_modified = os.path.getmtime(event.src_path)
                if current_modified > self.last_modified:
                    self.last_modified = current_modified
                    print(f"File update detected: {event.src_path}")
                    time.sleep(2)
                    self.update_function(event.src_path)
                    
                    # Update HTML preview
                    html_path = generate_html_preview()
                    if html_path:
                        print(f"Updated preview: {html_path}")
                    
            except Exception as e:
                print(f"Error processing file: {str(e)}")
            finally:
                self.is_processing = False

def update_both_databases(func):
    """Decorator to update both databases"""
    def wrapper(*args, **kwargs):
        results = []
        errors = []
        
        # Update primary database
        try:
            result1 = func(*args, **kwargs)
            results.append(('primary', result1))
        except Exception as e:
            print(f"Error updating primary database: {str(e)}")
            errors.append(('primary', str(e)))
        
        # Update development database
        try:
            with Database(db_name='zerodev') as db:
                result2 = func(*args, db=db, **kwargs)
                results.append(('development', result2))
        except Exception as e:
            print(f"Error updating development database: {str(e)}")
            errors.append(('development', str(e)))
        
        # Print summary
        print("\nUpdate Summary:")
        for db_name, result in results:
            print(f"{db_name.title()} database: {'Success' if result else 'Failed'}")
        if errors:
            print("\nErrors:")
            for db_name, error in errors:
                print(f"{db_name.title()} database: {error}")
        
        # Return True only if both updates were successful
        return all(result for _, result in results)
    return wrapper

@update_both_databases
def update_product_keys(data, is_dataframe=False, db=None):
    """Update product keys table with changes from CSV file or DataFrame"""
    if db is None:
        db = Database()  # Default to primary database
    try:
        # Handle input data
        if is_dataframe:
            df = data
        else:
            # Read CSV and normalize column names
            df = pd.read_csv(data)
            
        # Normalize column names
        df.columns = [col.strip().lower() for col in df.columns]
        
        # 欄位名稱映射
        column_map = {
            'computer name': 'computername',
            'computer_name': 'computername',
            'windows os': 'windowsos',
            'windows_os': 'windowsos',
            'os': 'windowsos',
            'product key': 'productkey',
            'product_key': 'productkey',
            'key': 'productkey',
            'time': 'timestamp',
            'date': 'timestamp',
            'serialnumber': 'serialnumber',
            'serial_number': 'serialnumber',
            'serial number': 'serialnumber',
            'status': 'status',
            'activation_date': 'activationdate',
            'activation date': 'activationdate',
            'last_check_date': 'lastcheckdate',
            'last check date': 'lastcheckdate'
        }
        
        # 重命名欄位
        df = df.rename(columns=column_map)
        
        with db:
            # Get existing records
            query = "SELECT productkey_new FROM product_keys"
            db.cursor.execute(query)
            existing_keys = {r['productkey_new'] for r in db.cursor.fetchall()}
            
            # Process records
            records_processed = 0
            records_added = 0
            records_updated = 0
            
            for _, row in df.iterrows():
                try:
                    if pd.isna(row.get('productkey')):
                        continue
                    
                    # 準備數據
                    values = {
                        'computername': str(row.get('computername', '')).strip(),
                        'windowsos': str(row.get('windowsos', '')).strip(),
                        'productkey': str(row.get('productkey', '')).strip(),
                        'serialnumber': str(row.get('serialnumber', '')).strip(),
                        'status': str(row.get('status', '')).strip(),
                        'timestamp': pd.to_datetime(row.get('timestamp')) if not pd.isna(row.get('timestamp')) else None,
                        'activationdate': pd.to_datetime(row.get('activationdate')) if not pd.isna(row.get('activationdate')) else None,
                        'lastcheckdate': pd.to_datetime(row.get('lastcheckdate')) if not pd.isna(row.get('lastcheckdate')) else None
                    }
                    
                    # Insert or update record
                    insert_query = """
                        INSERT INTO product_keys 
                            (computername, windowsos_new, productkey_new, serialnumber, 
                             status, created_at, activation_date, last_check_date, is_current)
                        VALUES (%(computername)s, %(windowsos)s, %(productkey)s, %(serialnumber)s,
                                %(status)s, %(timestamp)s, %(activationdate)s, %(lastcheckdate)s, true)
                        ON CONFLICT (computername, productkey_new) DO UPDATE 
                        SET windowsos_new = EXCLUDED.windowsos_new,
                            serialnumber = EXCLUDED.serialnumber,
                            status = EXCLUDED.status,
                            created_at = EXCLUDED.created_at,
                            activation_date = EXCLUDED.activation_date,
                            last_check_date = EXCLUDED.last_check_date,
                            is_current = true
                    """
                    
                    db.execute_query(insert_query, values)
                    
                    if values['productkey'] in existing_keys:
                        records_updated += 1
                    else:
                        records_added += 1
                    records_processed += 1
                    
                    if records_processed % 100 == 0:  # 每100筆顯示一次進度
                        print(f"Processed {records_processed} records...")
                    
                except Exception as e:
                    print(f"\nError processing record {records_processed + 1}:")
                    print(f"Data: {row.to_dict()}")
                    print(f"Error: {str(e)}")
                    continue
            
            print(f"\nProcessed total: {records_processed} records")
            print(f"Updated: {records_updated} records")
            print(f"Added: {records_added} new records")
            return True
            
    except Exception as e:
        print(f"\nError updating product keys: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_product_keys():
    """Check product keys table data"""
    with Database() as db:
        try:
            # Get total count only
            db.cursor.execute("SELECT COUNT(*) as count FROM product_keys")
            total_count = db.cursor.fetchone()['count']
            print(f"\nTotal product keys in database: {total_count}")
            return True
            
        except Exception as e:
            print(f"Error checking product keys: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def check_system_records():
    """Check system records table data"""
    with Database() as db:
        try:
            # Get total count only
            db.cursor.execute("SELECT COUNT(*) as count FROM system_records")
            total_count = db.cursor.fetchone()['count']
            print(f"\nTotal system records in database: {total_count}")
            return True
            
        except Exception as e:
            print(f"Error checking system records: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

# API configuration
API_CONFIG = {
    'base_url': 'https://erp.zerounique.com',
    'username': 'admin',
    'password': 'admin123'
}

def create_api_connection():
    """創建API連接實例"""
    return APIConnection(
        base_url=API_CONFIG['base_url'],
        username=API_CONFIG['username'],
        password=API_CONFIG['password']
    )

@update_both_databases
def update_system_records(data, is_dataframe=False, db=None):
    """Update system records from CSV file or DataFrame and sync to API"""
    if db is None:
        db = Database()
    try:
        # Handle input data
        if is_dataframe:
            df = data
        else:
            df = pd.read_csv(data)  # data is file_path
            print(f"\nProcessing file: {data}")
        
        print(f"Records to process: {len(df)}")
        
        # 初始化API連接
        api = create_api_connection()
        if not api.login():
            print("Warning: Failed to connect to API, will only update local database")
        
        with db:
            records_processed = 0
            api_items = []
            
            for _, row in df.iterrows():
                try:
                    db.cursor.execute("BEGIN")
                    
                    # 處理時間戳
                    timestamp = None
                    if 'Timestamp' in row and pd.notna(row['Timestamp']):
                        try:
                            timestamp = pd.to_datetime(row['Timestamp'])
                        except:
                            pass
                    
                    if timestamp is None and 'Date' in row and pd.notna(row['Date']):
                        try:
                            timestamp = pd.to_datetime(row['Date'])
                        except:
                            pass
                    
                    if timestamp is None:
                        timestamp = datetime.now()
                    
                    # 檢查是否已存在相同序號和時間戳的記錄
                    db.cursor.execute("""
                        SELECT id FROM system_records 
                        WHERE serialnumber = %(serialnumber)s AND created_at = %(created_at)s
                    """, {
                        'serialnumber': str(row.get('SerialNumber', '')).strip() if pd.notna(row.get('SerialNumber')) else None,
                        'created_at': timestamp
                    })
                    
                    existing_record = db.cursor.fetchone()
                    
                    if not existing_record:
                        # 處理磁碟資訊
                        disks_str = str(row.get('Disks', '')) if pd.notna(row.get('Disks')) else ''
                        # 保持原始格式
                        disks_data = disks_str
                        
                        # 準備API數據
                        api_item = {
                            "serialnumber": str(row.get('SerialNumber', '')).strip() if pd.notna(row.get('SerialNumber')) else None,
                            "manufacturer": str(row.get('Manufacturer', '')).strip() if pd.notna(row.get('Manufacturer')) else None,
                            "model": str(row.get('Model', '')).strip() if pd.notna(row.get('Model')) else None,
                            "ram_gb": str(row.get('RAM_GB', '')).strip() if pd.notna(row.get('RAM_GB')) else None,
                            "disks": disks_data  # 直接使用原始格式，不做轉換
                        }
                        
                        # 處理電池資訊
                        if pd.notna(row.get('Full_Charge_Capacity')) and pd.notna(row.get('Battery_Health')):
                            api_item["battery"] = {
                                "cycle_count": 0,
                                "design_capacity": str(row.get('Full_Charge_Capacity', '')),
                                "health": str(row.get('Battery_Health', ''))
                            }
                        
                        api_items.append(api_item)
                        
                        # 更新本地數據庫
                        params = {
                            'serialnumber': str(row.get('SerialNumber', '')).strip() if pd.notna(row.get('SerialNumber')) else None,
                            'manufacturer': str(row.get('Manufacturer', '')).strip() if pd.notna(row.get('Manufacturer')) else None,
                            'model': str(row.get('Model', '')).strip() if pd.notna(row.get('Model')) else None,
                            'systemsku': str(row.get('SystemSKU', '')).strip() if pd.notna(row.get('SystemSKU')) else None,
                            'operatingsystem': str(row.get('OperatingSystem', '')).strip() if pd.notna(row.get('OperatingSystem')) else None,
                            'cpu': str(row.get('CPU', '')).strip() if pd.notna(row.get('CPU')) else None,
                            'graphicscard': str(row.get('GraphicsCard', '')).strip() if pd.notna(row.get('GraphicsCard')) else None,
                            'ram_gb': str(row.get('RAM_GB', '')).strip() if pd.notna(row.get('RAM_GB')) else None,
                            'disks': disks_data,  # 直接使用原始格式，不做 JSON 轉換
                            'full_charge_capacity': str(row.get('Full_Charge_Capacity', '')).strip() if pd.notna(row.get('Full_Charge_Capacity')) else None,
                            'battery_health': str(row.get('Battery_Health', '')).strip() if pd.notna(row.get('Battery_Health')) else None,
                            'touchscreen': str(row.get('TouchScreen', '')).strip().lower() if pd.notna(row.get('TouchScreen')) else None,
                            'created_at': timestamp,
                            'is_current': True,
                            'sync_status': 'pending',
                            'last_sync_time': None,
                            'sync_version': '1.0',
                            'started_at': timestamp
                        }
                        
                        db.cursor.execute("""
                            INSERT INTO system_records (
                                serialnumber, manufacturer, model, systemsku,
                                operatingsystem, cpu, graphicscard, ram_gb,
                                disks, full_charge_capacity, battery_health,
                                touchscreen, created_at, is_current, sync_status,
                                last_sync_time, sync_version, started_at
                            ) VALUES (
                                %(serialnumber)s, %(manufacturer)s, %(model)s, %(systemsku)s,
                                %(operatingsystem)s, %(cpu)s, %(graphicscard)s, %(ram_gb)s,
                                %(disks)s, %(full_charge_capacity)s, %(battery_health)s,
                                %(touchscreen)s, %(created_at)s, %(is_current)s, %(sync_status)s,
                                %(last_sync_time)s, %(sync_version)s, %(started_at)s
                            )
                        """, params)
                        
                        records_processed += 1
                    
                    db.cursor.execute("COMMIT")
                    
                except Exception as e:
                    db.cursor.execute("ROLLBACK")
                    print(f"Error processing record: {str(e)}")
                    continue
            
            # 如果有新記錄要上傳到API
            if api_items and api.token:
                try:
                    request_data = prepare_request_data(api_items)
                    result = api.send_data(request_data)
                    if result.get('success'):
                        print(f"Successfully uploaded {len(api_items)} records to API")
                    else:
                        print(f"API upload failed: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    print(f"Error uploading to API: {str(e)}")
            
            print(f"\nProcessed {records_processed} new records")
            return records_processed > 0
            
    except Exception as e:
        print(f"Error updating system records: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def create_tables():
    """Create necessary database tables"""
    with Database() as db:
        # Drop existing tables with CASCADE
        db.execute_query("""
            DROP TABLE IF EXISTS system_records CASCADE;
            DROP TABLE IF EXISTS product_keys CASCADE;
        """)
        
        # Create system_records table with improved field definitions
        db.execute_query("""
            CREATE TABLE system_records (
                id SERIAL PRIMARY KEY,
                serialnumber VARCHAR(100),
                computername VARCHAR(200),
                manufacturer VARCHAR(200),
                model VARCHAR(200),
                systemsku TEXT,
                operatingsystem TEXT,
                cpu TEXT,
                resolution VARCHAR(100),
                graphicscard TEXT,
                touchscreen VARCHAR(100),
                ram_gb DECIMAL,
                disks TEXT,
                disks_gb DECIMAL,
                design_capacity BIGINT,
                full_charge_capacity BIGINT,
                cycle_count BIGINT,
                battery_health DECIMAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_current BOOLEAN DEFAULT true,
                sync_status VARCHAR(20) DEFAULT 'pending',
                last_sync_time TIMESTAMP,
                sync_version VARCHAR(10) DEFAULT '1.0',
                started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                data_source VARCHAR(100),
                validation_status VARCHAR(20) DEFAULT 'pending',
                validation_message TEXT
            )
        """)
        
        # Create product_keys table with improved structure
        db.execute_query("""
            CREATE TABLE product_keys (
                id SERIAL PRIMARY KEY,
                computername VARCHAR(200),
                windowsos_new TEXT,
                productkey_new VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_current BOOLEAN DEFAULT true,
                CONSTRAINT product_keys_unique_key UNIQUE (computername, productkey_new)
            )
        """)
        
        # Create indexes for better query performance
        db.execute_query("""
            CREATE INDEX idx_system_records_serialnumber ON system_records(serialnumber);
            CREATE INDEX idx_system_records_computername ON system_records(computername);
            CREATE INDEX idx_product_keys_computername ON product_keys(computername);
        """)
        
        print("Database tables created/updated successfully")

if __name__ == "__main__":
    base_path = r"\\192.168.0.10\Files\03_IT\data"
    
    # Create tables if needed
    create_tables()
    
    print("\nStarting file monitoring...")
    start_monitoring(base_path)
