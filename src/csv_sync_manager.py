import os
import time
from datetime import datetime
from typing import Optional, Dict, List
import pandas as pd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from test_api import APIConnection, prepare_request_data
from sqldb import Database
import json
import logging
from html_preview import generate_html_preview

class CSVSyncManager:
    def __init__(self, base_path: str):
        """Initialize sync manager
        
        Args:
            base_path: Base path for CSV files
        """
        self.base_path = base_path
        self.api = None
        
        # 為日誌系統增加日期跟踪
        self.log_date = datetime.now().strftime('%Y%m%d')
        self.log_handlers = {}
        
        self.setup_logging()
        self.last_printed_sn = None  # Record last printed serial number
        self.last_print_time = None  # Record last printed time
        
    def setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger("csv_sync")
        self.logger.setLevel(logging.INFO)
        
        # Create log directory
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        # Set up file handler - create log files by date
        log_file = os.path.join(self.log_dir, f"sync_{self.log_date}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Set up console handler - show important info only
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Set different formats
        file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        console_formatter = logging.Formatter('%(message)s')  # Simplified console output
        
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 存儲文件處理器以便後續更新
        self.log_handlers['file'] = file_handler
        self.log_handlers['console'] = console_handler
    
    def check_log_date(self):
        """檢查日期是否變化，如果是則更新日誌文件"""
        current_date = datetime.now().strftime('%Y%m%d')
        if current_date != self.log_date:
            # 日期已變化，需要切換到新的日誌文件
            self.log_date = current_date
            
            # 創建新的文件處理器
            log_file = os.path.join(self.log_dir, f"sync_{self.log_date}.log")
            new_handler = logging.FileHandler(log_file, encoding='utf-8')
            new_handler.setLevel(logging.INFO)
            
            # 設置格式
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            new_handler.setFormatter(formatter)
            
            # 移除舊的文件處理器
            self.logger.removeHandler(self.log_handlers['file'])
            
            # 添加新的文件處理器
            self.logger.addHandler(new_handler)
            self.log_handlers['file'] = new_handler
            
            # 記錄日誌切換信息
            self.logger.info(f"日誌文件已切換到新日期: {self.log_date}")
    
    def log_info(self, message):
        """增強的信息日誌記錄，帶日期檢查"""
        self.check_log_date()
        self.logger.info(message)
    
    def log_error(self, message):
        """增強的錯誤日誌記錄，帶日期檢查"""
        self.check_log_date()
        self.logger.error(message)
    
    def log_warning(self, message):
        """增強的警告日誌記錄，帶日期檢查"""
        self.check_log_date()
        self.logger.warning(message)
    
    def log_debug(self, message):
        """增強的調試日誌記錄，帶日期檢查"""
        self.check_log_date()
        self.logger.debug(message)
    
    def initialize_api(self) -> bool:
        """Initialize API connection"""
        try:
            self.api = APIConnection(
                base_url="https://erp.zerounique.com",
                username="admin",
                password="admin123"
            )
            result = self.api.login()
            if result:
                self.log_info("API connection successful")
            else:
                self.log_error("API login failed")
            return result
        except Exception as e:
            self.log_error(f"API initialization failed: {str(e)}")
            return False
    
    def process_system_records(self, file_path: str) -> bool:
        """Process system records CSV file
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            bool: Whether processing was successful
        """
        try:
            self.log_info(f"Processing system records: {os.path.basename(file_path)}")
            
            # Initialize API connection
            if not hasattr(self, 'api') or self.api is None:
                if not self.initialize_api():
                    self.log_error("API connection failed")
                    return False
            
            # Read CSV file
            df = pd.read_csv(file_path)
            self.log_info(f"Found {len(df)} records")
            
            # Process timestamp
            try:
                # Use Timestamp column first
                if 'Timestamp' in df.columns:
                    # Save original Timestamp data
                    df['original_timestamp'] = df['Timestamp']
                    
                    # Clean up timestamp format
                    df['Timestamp'] = df['Timestamp'].apply(
                        lambda x: str(x).strip() if pd.notna(x) else None
                    )
                    
                    # Convert to datetime, keeping original format
                    df['created_at'] = pd.to_datetime(
                        df['Timestamp'],
                        format='mixed',
                        errors='coerce'
                    )
                    
                    # If conversion fails, try other formats
                    mask = pd.isna(df['created_at'])
                    if mask.any():
                        self.log_warning("Some timestamps failed to parse, trying alternative formats")
                        for fmt in ['%m/%d/%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M']:
                            try:
                                df.loc[mask, 'created_at'] = pd.to_datetime(
                                    df.loc[mask, 'Timestamp'],
                                    format=fmt,
                                    errors='coerce'
                                )
                                mask = pd.isna(df['created_at'])
                                if not mask.any():
                                    break
                            except:
                                continue
                
                elif 'Date' in df.columns:
                    self.log_warning("Using Date column instead of Timestamp")
                    df['created_at'] = pd.to_datetime(df['Date'], format='mixed', errors='coerce')
                    df['original_timestamp'] = df['Date']
                else:
                    self.log_warning("No Timestamp or Date column found, using current time")
                    current_time = pd.Timestamp.now()
                    df['created_at'] = current_time
                    df['original_timestamp'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
                
                # Process any NaT (invalid date)
                mask = pd.isna(df['created_at'])
                if mask.any():
                    current_time = pd.Timestamp.now()
                    df.loc[mask, 'created_at'] = current_time
                    df.loc[mask, 'original_timestamp'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
                
                # Ensure consistency in time zone (using UTC)
                df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_localize(None)
                
                # Only record detailed timestamp information in log file
                sample_data = df[['SerialNumber', 'original_timestamp', 'created_at']].head()
                self.log_debug("\n" + sample_data.to_string())
                
            except Exception as e:
                self.log_error(f"Timestamp processing error: {str(e)}")
                return False
            
            # Save last record
            latest_csv_record = df.iloc[-1] if not df.empty else None
            if latest_csv_record is not None:
                self.log_info(f"Latest record: {latest_csv_record.get('SerialNumber', '')}")
            
            # Get last processed time from both databases
            with Database() as zerodb, Database(db_name='zerodev') as zerodev:
                # Get all existing serial numbers from both databases
                zerodb.cursor.execute("SELECT serialnumber FROM system_records")
                zerodev.cursor.execute("SELECT serialnumber FROM system_records")
                
                zerodb_serials = {r['serialnumber'] for r in zerodb.cursor.fetchall()}
                zerodev_serials = {r['serialnumber'] for r in zerodev.cursor.fetchall()}
                
                # Get the last processed timestamps
                zerodb.cursor.execute("SELECT MAX(created_at) as last_timestamp FROM system_records")
                zerodev.cursor.execute("SELECT MAX(created_at) as last_timestamp FROM system_records")
                
                zerodb_last = zerodb.cursor.fetchone()['last_timestamp'] or pd.Timestamp.min
                zerodev_last = zerodev.cursor.fetchone()['last_timestamp'] or pd.Timestamp.min
                
                # Use the earlier timestamp as a baseline
                last_processed_time = min(zerodb_last, zerodev_last)
                
                self.log_info(f"Last processed time: {last_processed_time}")
                
                # Check record counts in both databases
                zerodb.cursor.execute("SELECT COUNT(*) as count FROM system_records")
                zerodev.cursor.execute("SELECT COUNT(*) as count FROM system_records")
                
                zerodb_count = zerodb.cursor.fetchone()['count']
                zerodev_count = zerodev.cursor.fetchone()['count']
                
                self.log_info(f"Current record count - main database: {zerodb_count}, development database: {zerodev_count}")
                
                if zerodb_count != zerodev_count:
                    self.log_warning(f"Database record count mismatch!")

            # Process records that are either:
            # 1. Newer than the last processed time, or
            # 2. Have a serial number that doesn't exist in either database
            existing_serials = zerodb_serials.union(zerodev_serials)
            new_records = df[
                (df['created_at'] > last_processed_time) | 
                (~df['SerialNumber'].isin(existing_serials))
            ]
            self.log_info(f"Found {len(new_records)} new records to process")
            
            # Print latest label even if no new records
            if len(new_records) == 0:
                self.log_info("No new records to process")
                # If there's a latest record, check if label needs printing
                if latest_csv_record is not None:
                    try:
                        serialnumber = str(latest_csv_record.get('SerialNumber', '')).strip()
                        timestamp = latest_csv_record.get('created_at')
                        
                        # Check if recently printed
                        current_time = datetime.now()
                        if (self.last_printed_sn == serialnumber and 
                            self.last_print_time is not None and 
                            (current_time - self.last_print_time).total_seconds() < 30):  # Don't reprint within 30 seconds
                            self.log_info(f"Skipping print for SN: {serialnumber} - recently printed")
                            return True
                        # If there's a latest record, try printing label
                        self.log_info(f"Attempting to print label for latest CSV record: {serialnumber} ({timestamp})")
                        
                        # Find matching record in database
                        with Database() as db:
                            db.cursor.execute("""
                                SELECT id, created_at 
                                FROM system_records 
                                WHERE serialnumber = %s
                                ORDER BY created_at DESC 
                                LIMIT 1
                            """, (serialnumber,))
                            record = db.cursor.fetchone()
                            
                            if record:
                                self.log_info(f"Found matching record in database - ID: {record['id']}, Created: {record['created_at']}")
                                # Print label only if record doesn't exist
                                from print_label_html import print_label_by_id
                                if print_label_by_id(record['id']):
                                    self.log_info(f"Successfully reprinted label for SN: {serialnumber}")
                                    # Update last printed record
                                    self.last_printed_sn = serialnumber
                                    self.last_print_time = datetime.now()
                                else:
                                    self.log_error(f"Failed to reprint label for SN: {serialnumber}")
                            else:
                                self.log_warning(f"No matching record found in database for SN: {serialnumber}")
                                
                    except Exception as e:
                        self.log_error(f"Error reprinting latest label: {str(e)}")
                        import traceback
                        traceback.print_exc()
                return True
            
            # Update both databases
            success_main = self._update_database(new_records, 'zerodb')
            success_dev = self._update_database(new_records, 'zerodev')
            
            # Verify updated record count
            with Database() as zerodb, Database(db_name='zerodev') as zerodev:
                zerodb.cursor.execute("SELECT COUNT(*) as count FROM system_records")
                zerodev.cursor.execute("SELECT COUNT(*) as count FROM system_records")
                
                new_zerodb_count = zerodb.cursor.fetchone()['count']
                new_zerodev_count = zerodev.cursor.fetchone()['count']
                
                self.log_info(f"Updated record counts - zerodb: {new_zerodb_count}, zerodev: {new_zerodev_count}")
                
                if new_zerodb_count != new_zerodev_count:
                    self.log_error(f"Database sync failed! Record counts still mismatch after update!")
                    self.log_error(f"zerodb: {new_zerodb_count}, zerodev: {new_zerodev_count}")
                    return False
            
            # Generate preview
            html_path = generate_html_preview()
            if html_path:
                self.log_info(f"Updated preview: {html_path}")
            
            return success_main and success_dev
                
        except Exception as e:
            self.log_error(f"Error processing system records: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _update_database(self, df: pd.DataFrame, db_name: str) -> bool:
        """Update specified database
        
        Args:
            df: DataFrame containing records
            db_name: Database name
            
        Returns:
            bool: Whether update was successful
        """
        try:
            self.log_info(f"Updating {db_name} database...")
            records_processed = 0
            latest_record_id = None
            latest_record_sn = None
            api_records = []  # Collect records for API upload
            
            with Database(db_name=db_name) as db:
                for _, row in df.iterrows():
                    try:
                        serialnumber = str(row.get('SerialNumber', '')).strip()
                        timestamp = row.get('created_at')
                        
                        # Simplify record processing output
                        self.log_debug(f"Processing record: {serialnumber}")
                        
                        # Ensure timestamp consistency
                        if pd.isna(timestamp):
                            self.log_warning(f"Missing timestamp for SN: {serialnumber}, using current time")
                            timestamp = pd.Timestamp.now()
                        else:
                            # Ensure timestamp is Timestamp type
                            timestamp = pd.to_datetime(timestamp)
                            # Remove time zone information to maintain consistency
                            if timestamp.tzinfo is not None:
                                timestamp = timestamp.tz_localize(None)
                        
                        self.log_info(f"Processing record in {db_name}: SerialNumber={serialnumber}, Timestamp={timestamp}")
                        
                        # Check if record already exists with same serial number and timestamp
                        db.cursor.execute("""
                            SELECT id FROM system_records 
                            WHERE serialnumber = %s AND created_at = %s::timestamp
                        """, (serialnumber, timestamp))
                        
                        existing_record = db.cursor.fetchone()
                        if not existing_record:
                            # Process disk data - keep original format
                            disks_str = str(row.get('Disks', '')).strip() if pd.notna(row.get('Disks')) else ''
                            
                            # Process battery information
                            battery_data = {
                                'design_capacity': None,
                                'full_charge_capacity': None,
                                'cycle_count': None,
                                'battery_health': None
                            }
                            
                            # 直接處理電池數據，保留原始格式不轉換
                            def process_battery_value(value):
                                if pd.isna(value):
                                    return None
                                return str(value).strip()
                            
                            # 不再需要電池JSON數據
                            # battery_json = {}
                            
                            # Design capacity - 保留原始格式
                            design_capacity = process_battery_value(row.get('Design_Capacity'))
                            
                            # Actual capacity - 保留原始格式
                            full_charge_capacity = process_battery_value(row.get('Full_Charge_Capacity'))
                            
                            # Cycle count - 保留原始格式
                            cycle_count = process_battery_value(row.get('Cycle_Count'))
                            
                            # Battery health - 保留原始格式
                            battery_health = process_battery_value(row.get('Battery_Health'))
                            
                            # Directly use original format, no conversion
                            insert_data = {
                                'serialnumber': serialnumber,
                                'computername': str(row.get('ComputerName', '')).strip() if pd.notna(row.get('ComputerName')) else None,
                                'manufacturer': str(row.get('Manufacturer', '')).strip(),
                                'model': str(row.get('Model', '')).strip(),
                                'systemsku': str(row.get('SystemSKU', '')).strip() if pd.notna(row.get('SystemSKU')) else None,
                                'ram_gb': float(row.get('RAM_GB', 0)) if pd.notna(row.get('RAM_GB')) else 0,
                                'disks': disks_str,  # Directly use original string, no conversion
                                'created_at': row.get('original_timestamp') if pd.notna(row.get('original_timestamp')) else timestamp,
                                'operatingsystem': str(row.get('OperatingSystem', '')).strip(),
                                'cpu': str(row.get('CPU', '')).strip(),
                                'resolution': str(row.get('Resolution', '')).strip() if pd.notna(row.get('Resolution')) else None,
                                'graphicscard': str(row.get('GraphicsCard', '')).strip(),
                                'touchscreen': str(row.get('TouchScreen', '')).strip() if pd.notna(row.get('TouchScreen')) else None,
                                'design_capacity': design_capacity,
                                'full_charge_capacity': full_charge_capacity,
                                'cycle_count': cycle_count,
                                'battery_health': battery_health
                            }
                            
                            self.log_info(f"Inserting new record to {db_name}: {insert_data}")
                            
                            try:
                                db.cursor.execute("""
                                    INSERT INTO system_records (
                                        serialnumber, computername, manufacturer, model,
                                        systemsku, ram_gb, disks, created_at, is_current,
                                        sync_status, operatingsystem, cpu, resolution,
                                        graphicscard, touchscreen, design_capacity,
                                        full_charge_capacity, cycle_count, battery_health
                                    ) VALUES (
                                        %(serialnumber)s, %(computername)s, %(manufacturer)s,
                                        %(model)s, %(systemsku)s, %(ram_gb)s, %(disks)s,
                                        %(created_at)s, true, 'pending', %(operatingsystem)s,
                                        %(cpu)s, %(resolution)s, %(graphicscard)s,
                                        %(touchscreen)s, %(design_capacity)s,
                                        %(full_charge_capacity)s, %(cycle_count)s,
                                        %(battery_health)s
                                    ) RETURNING id
                                """, insert_data)
                                
                                # Get ID of new inserted record
                                new_record = db.cursor.fetchone()
                                if new_record:
                                    record_id = new_record['id']
                                    latest_record_id = record_id
                                    latest_record_sn = serialnumber
                                    records_processed += 1
                                    
                                    # Collect records for API upload
                                    api_records.append(insert_data)
                                    
                                    # Explicitly commit after each successful insert
                                    db.connection.commit()
                                    self.log_info(f"Successfully inserted record with ID: {record_id}")
                                    
                            except Exception as e:
                                self.log_error(f"Error inserting record: {str(e)}")
                                db.connection.rollback()
                                continue
                            
                    except Exception as e:
                        self.log_error(f"Record processing error: {str(e)}")
                        db.connection.rollback()
                        continue
                
                # Print label
                if db_name == 'zerodb' and latest_record_id is not None:
                    try:
                        from print_label_html import print_label_by_id
                        # Wait a short time to ensure the record is fully committed
                        time.sleep(0.5)
                        if print_label_by_id(latest_record_id):
                            self.log_info(f"Label printed: {latest_record_sn}")
                            self.last_printed_sn = latest_record_sn
                            self.last_print_time = datetime.now()
                        else:
                            self.log_error(f"Label printing failed for ID: {latest_record_id}")
                    except Exception as e:
                        self.log_error(f"Printing error: {str(e)}")
                
                # If there's new records, upload to API
                if api_records and db_name == 'zerodb':  # Only upload to main database
                    try:
                        if not hasattr(self, 'api') or self.api is None:
                            if not self.initialize_api():
                                self.log_error("Failed to initialize API connection")
                                return False
                        
                        # Prepare API request data
                        request_data = prepare_request_data(api_records)
                        
                        # Send data to API
                        response = self.api.send_data(request_data)
                        if response.get('error'):
                            self.log_error(f"API upload failed: {response.get('error')}")
                        else:
                            self.log_info(f"Successfully uploaded {len(api_records)} records to API")
                            
                    except Exception as e:
                        self.log_error(f"Error uploading to API: {str(e)}")
                
                # Generate preview after all updates are complete
                if records_processed > 0:
                    try:
                        html_path = generate_html_preview()
                        if html_path:
                            self.log_info(f"Updated preview: {html_path}")
                        else:
                            self.log_error("Failed to generate preview")
                    except Exception as e:
                        self.log_error(f"Error generating preview: {str(e)}")
                
                self.log_info(f"Processed {records_processed} new records")
                return True
                
        except Exception as e:
            self.log_error(f"Database update error: {str(e)}")
            return False
    
    def process_product_keys(self, file_path: str) -> bool:
        """Process product keys CSV file
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            bool: Whether processing was successful
        """
        try:
            self.log_info(f"Processing product keys from: {file_path}")
            
            # Read CSV file
            df = pd.read_csv(file_path)
            self.log_info(f"Found {len(df)} records in CSV")
            
            # Standardize column names
            df.columns = [col.strip().lower() for col in df.columns]
            
            # Column mapping
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
                'date': 'timestamp'
            }
            
            # Rename columns
            df = df.rename(columns=column_map)
            
            # Update database
            with Database() as db:
                # Get existing records
                db.cursor.execute("SELECT productkey_new FROM product_keys")
                existing_keys = {r['productkey_new'] for r in db.cursor.fetchall()}
                
                records_processed = 0
                records_updated = 0
                records_added = 0
                
                for _, row in df.iterrows():
                    try:
                        if pd.isna(row.get('productkey')):
                            continue
                        
                        values = (
                            str(row.get('computername', '')).strip(),
                            str(row.get('windowsos', '')).strip(),
                            str(row.get('productkey', '')).strip(),
                            pd.to_datetime(row.get('timestamp')) if pd.notna(row.get('timestamp')) else None
                        )
                        
                        db.execute_query("""
                            INSERT INTO product_keys 
                                (computername, windowsos_new, productkey_new, created_at, is_current)
                            VALUES (%s, %s, %s, %s, true)
                            ON CONFLICT (computername, productkey_new) DO UPDATE 
                            SET windowsos_new = EXCLUDED.windowsos_new,
                                created_at = EXCLUDED.created_at,
                                is_current = true
                        """, values)
                        
                        if str(row.get('productkey', '')).strip() in existing_keys:
                            records_updated += 1
                        else:
                            records_added += 1
                        records_processed += 1
                        
                    except Exception as e:
                        self.log_error(f"Error processing record: {str(e)}")
                        continue
                
                self.log_info(f"Processed total: {records_processed} records")
                self.log_info(f"Updated: {records_updated} records")
                self.log_info(f"Added: {records_added} new records")
                
                # Generate preview
                html_path = generate_html_preview()
                if html_path:
                    self.log_info(f"Updated preview: {html_path}")
                
                return True
                
        except Exception as e:
            self.log_error(f"Error processing product keys: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

class CSVHandler(FileSystemEventHandler):
    def __init__(self, manager: CSVSyncManager):
        self.manager = manager
        self.is_processing = False
        self.last_modified = 0
        self.last_size = 0
    
    def wait_for_file_ready(self, file_path: str, timeout: int = 10) -> bool:
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
        """File modification event processing"""
        if self.is_processing:
            return
            
        if not event.is_directory:
            try:
                self.is_processing = True
                
                # Wait for file write completion
                if not self.wait_for_file_ready(event.src_path):
                    self.manager.log_warning("File write timeout")
                    return
                
                current_modified = os.path.getmtime(event.src_path)
                if current_modified > self.last_modified:
                    self.last_modified = current_modified
                    self.manager.log_info(f"File update detected: {event.src_path}")
                    
                    # Process based on file type
                    if "system_records" in event.src_path:
                        self.manager.process_system_records(event.src_path)
                    elif "product_keys" in event.src_path:
                        self.manager.process_product_keys(event.src_path)
                    
            except Exception as e:
                self.manager.log_error(f"Error processing file: {str(e)}")
            finally:
                self.is_processing = False

def start_monitoring(base_path: str):
    """Start monitoring CSV files
    
    Args:
        base_path: Base path containing CSV files
    """
    manager = CSVSyncManager(base_path)
    handler = CSVHandler(manager)
    
    observer = Observer()
    observer.schedule(handler, base_path, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nMonitoring stopped")
    
    observer.join()

if __name__ == "__main__":
    base_path = r"\\192.168.0.10\Files\03_IT\data"
    start_monitoring(base_path) 