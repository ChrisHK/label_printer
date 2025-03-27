import os
from datetime import datetime
import pandas as pd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
from print_label_html import print_new_record
from initdb import update_system_records, update_product_keys
from html_preview import generate_html_preview
from sqldb import Database

class CSVMonitor:
    def __init__(self):
        self.base_path = r"\\192.168.0.10\Files\03_IT\data"
        self.current_month = self._get_current_month()
        self.observer = None
        self.pause_db_updates = False  # Set to False to enable database updates
        
    def _get_current_month(self):
        """Get current month in format 'MonYYYY'"""
        current_date = datetime.now()
        return current_date.strftime('%b%Y')  # 例如: Dec2024
    
    def get_file_paths(self):
        """Get current CSV file paths"""
        return {
            'system_records': os.path.join(self.base_path, f"system_records_{self.current_month}.csv"),
            'product_keys': os.path.join(self.base_path, f"product_keys_{self.current_month}.csv")
        }
    
    def process_system_records(self, file_path):
        """Process system records CSV file"""
        try:
            print("\n" + "="*50)
            print("Processing new system record")
            print("="*50)
            
            # Update database
            if update_system_records(file_path):
                print("Database updated successfully")
                # Generate new preview after successful update
                html_path = generate_html_preview()
                if html_path:
                    print(f"Preview updated: {html_path}")
            else:
                print("Failed to update database")
            
            # Process CSV for printing
            print("\nAttempting to print label...")
            if print_new_record(file_path):
                print("Label printed successfully")
            else:
                print("No new labels to print")
                
            return True
            
        except Exception as e:
            print(f"Error processing system records: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_product_keys(self, file_path):
        """Process product keys CSV file"""
        try:
            print("\n" + "="*50)
            print("Processing new product key")
            print("="*50)
            
            # Update database
            if update_product_keys(file_path):
                print("Database updated successfully")
                # Generate new preview after successful update
                html_path = generate_html_preview()
                if html_path:
                    print(f"Preview updated: {html_path}")
            else:
                print("Failed to update database")
            
            return True
            
        except Exception as e:
            print(f"Error processing product keys: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def start_monitoring(self):
        """Start monitoring CSV files"""
        class FileHandler(FileSystemEventHandler):
            def __init__(self, monitor):
                self.monitor = monitor
                self.is_processing = False
                self.last_modified = {}
            
            def on_modified(self, event):
                if self.is_processing or event.is_directory:
                    return
                    
                file_path = event.src_path
                file_name = os.path.basename(file_path)
                
                if not (file_name.startswith(('system_records_', 'product_keys_')) and 
                        file_name.endswith('.csv')):
                    return
                
                try:
                    self.is_processing = True
                    
                    # Add processing delay
                    time.sleep(3)
                    
                    current_time = os.path.getmtime(file_path)
                    if current_time <= self.last_modified.get(file_path, 0):
                        return
                    
                    self.last_modified[file_path] = current_time
                    print(f"\nProcessing file: {file_name}")
                    
                    if 'system_records' in file_name:
                        self.monitor.process_system_records(file_path)
                    elif 'product_keys' in file_name:
                        self.monitor.process_product_keys(file_path)
                        
                finally:
                    self.is_processing = False
        
        # Start monitoring
        handler = FileHandler(self)
        self.observer = Observer()
        self.observer.schedule(handler, self.base_path, recursive=False)
        self.observer.start()
        
        print(f"\nMonitoring CSV files in: {self.base_path}")
        print(f"Current month: {self.current_month}")
        
        try:
            while True:
                # Check for month change
                new_month = self._get_current_month()
                if new_month != self.current_month:
                    print(f"\nSwitching to new month: {new_month}")
                    self.current_month = new_month
                
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            self.observer.stop()
            print("\nMonitoring stopped")
            
        self.observer.join()