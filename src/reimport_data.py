import os
from datetime import datetime
import pandas as pd
import re
from sqldb import Database
from initdb import create_tables, update_system_records, update_product_keys
from html_preview import generate_html_preview
import json

def read_system_records(file_path):
    """
    讀取系統記錄CSV文件並進行初始數據處理
    """
    try:
        # 直接讀取 CSV，保持原始格式
        df = pd.read_csv(
            file_path,
            encoding='utf-8',
            dtype=str,  # 全部當作字符串讀入
            na_values=['', 'N/A', 'NULL', '#N/A', '#VALUE!']
        )
        return df
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def parse_disk_capacity(capacity_str):
    """
    解析磁盤容量字符串並轉換為GB
    支持更多格式：'256GB', '1TB', '512GB', '1.5TB' 等
    """
    if pd.isna(capacity_str) or not isinstance(capacity_str, str):
        return 0
    
    capacity_str = capacity_str.strip().upper()
    if not capacity_str:
        return 0
    
    try:
        # 使用正則表達式提取數字和單位
        match = re.match(r'([\d.]+)\s*(TB|GB|MB)?', capacity_str)
        if not match:
            return 0
            
        value = float(match.group(1))
        unit = match.group(2) if match.group(2) else 'GB'
        
        # 轉換為GB
        conversion = {
            'TB': 1024,
            'GB': 1,
            'MB': 1/1024
        }
        
        return value * conversion.get(unit, 0)
    except Exception as e:
        print(f"Error parsing disk capacity '{capacity_str}': {str(e)}")
        return 0

def validate_and_clean_data(df):
    """
    驗證和清理數據框架中的數據
    """
    # 創建副本避免警告
    df = df.copy()
    
    # 清理 ComputerName
    if 'ComputerName' in df.columns:
        df['ComputerName'] = df['ComputerName'].str.strip()
    
    # 清理和標準化 Resolution
    if 'Resolution' in df.columns:
        def clean_resolution(res):
            if pd.isna(res):
                return None
            # 提取數字部分
            match = re.search(r'(\d+)x(\d+)', str(res))
            if match:
                return f"{match.group(1)}x{match.group(2)}"
            return None
        df['Resolution'] = df['Resolution'].apply(clean_resolution)
    
    # 清理和標準化 Disks
    if 'Disks' in df.columns:
        df['Disks_GB'] = df['Disks'].apply(parse_disk_capacity)
    
    # 處理數值型欄位，但不過濾數據
    numeric_columns = ['Design_Capacity', 'Full_Charge_Capacity', 'Cycle_Count', 'Battery_Health']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 標記無效記錄而不是過濾它們
    df['is_valid'] = True
    if all(col in df.columns for col in numeric_columns):
        df['is_valid'] = (
            df['Design_Capacity'].notna() &
            df['Full_Charge_Capacity'].notna() &
            df['Cycle_Count'].notna() &
            df['Battery_Health'].notna()
        )
    
    return df

def standardize_data_format(df):
    """
    標準化數據格式
    """
    # 標準化日期時間格式
    df['Timestamp'] = pd.to_datetime(df['Timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    
    # 標準化計算機名稱格式
    df['ComputerName'] = df['ComputerName'].str.upper()
    
    # 標準化分辨率格式
    def standardize_resolution(res):
        if pd.isna(res):
            return 'Unknown'
        parts = res.split('x')
        if len(parts) == 2:
            try:
                width = int(parts[0])
                height = int(parts[1])
                return f"{width}x{height}"
            except ValueError:
                return 'Invalid'
        return 'Invalid'
    
    df['Resolution'] = df['Resolution'].apply(standardize_resolution)
    
    # 標準化容量單位（轉換為GB並添加單位）
    df['Disks_Formatted'] = df['Disks_GB'].apply(
        lambda x: f"{int(x)}GB" if x < 1024 else f"{x/1024:.1f}TB"
    )
    
    # 格式化數值型欄位
    df['Design_Capacity'] = df['Design_Capacity'].fillna(0).astype(int)
    df['Cycle_Count'] = df['Cycle_Count'].fillna(0).astype(int)
    
    return df

def process_system_records(file_path):
    """完整的數據處理流程"""
    # 1. 讀取數據
    df = read_system_records(file_path)
    if df is None:
        return None
    
    print(f"Original columns: {df.columns.tolist()}")
    print(f"CSV records count: {len(df)}")
    
    # 檢查數據庫連接
    with Database() as db:
        db.cursor.execute("SELECT current_database()")
        current_db = db.cursor.fetchone()['current_database']
        print(f"當前連接的數據庫: {current_db}")
        
        # 檢查表中的現有記錄
        db.cursor.execute("SELECT COUNT(*) as count FROM system_records")
        existing_count = db.cursor.fetchone()['count']
        print(f"數據庫中現有記錄數: {existing_count}")
    
    return df

def get_csv_files():
    """Get all CSV files sorted by month"""
    base_path = r"\\192.168.0.10\Files\03_IT\data"
    
    def parse_month_year(filename):
        try:
            parts = filename.split('_')
            if len(parts) >= 2:
                date_part = parts[-1].split('.')[0]
                return datetime.strptime(date_part, '%b%Y')
        except ValueError:
            return datetime(1900, 1, 1)
        return datetime(1900, 1, 1)
    
    # Get and filter file lists
    system_files = []
    product_files = []
    
    for file in os.listdir(base_path):
        if file.endswith('.csv'):
            if file.startswith('system_records_'):
                system_files.append(file)
            elif file.startswith('product_keys_'):
                product_files.append(file)
    
    # Sort by date
    system_files.sort(key=parse_month_year)
    product_files.sort(key=parse_month_year)
    
    return {
        'system': system_files,
        'product': product_files
    }

def process_product_keys(file_path):
    """
    處理產品密鑰文件
    """
    try:
        # 直接讀取 CSV
        df = pd.read_csv(
            file_path,
            encoding='utf-8',
            dtype=str,  # 全部當作字符串讀入
            na_values=['', 'N/A', 'NULL']
        )
        
        print(f"Original columns: {df.columns.tolist()}")
        print(f"CSV records count: {len(df)}")
        
        return df
    except Exception as e:
        print(f"Error processing product keys file: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def clear_and_reimport():
    """Clear database and reimport all CSV data"""
    base_path = r"\\192.168.0.10\Files\03_IT\data"
    
    print("\nStarting database cleanup and reimport process...")
    
    # Recreate tables (this will drop existing tables)
    print("\nRecreating database tables...")
    create_tables()
    
    # Get all CSV files
    all_files = os.listdir(base_path)
    system_files = [f for f in all_files if f.startswith('system_records_') and f.endswith('.csv')]
    product_files = [f for f in all_files if f.startswith('product_keys_') and f.endswith('.csv')]
    
    # Sort files by date (newest first)
    system_files.sort(reverse=True)
    product_files.sort(reverse=True)
    
    # Import system records
    print(f"\nFound {len(system_files)} system record files:")
    for file in system_files:
        print(f"- {file}")
    
    print("\nProcessing system records...")
    total_records = 0
    total_csv_records = 0
    for file in system_files:
        file_path = os.path.join(base_path, file)
        print(f"\nImporting {file}...")
        try:
            # 使用改進的數據處理流程
            df = process_system_records(file_path)
            if df is not None:
                total_csv_records += len(df)
                if update_system_records(df, is_dataframe=True):
                    total_records += len(df)
                    print(f"Successfully imported {len(df)} records from {file}")
                else:
                    print(f"Failed to import {file}")
        except Exception as e:
            print(f"Error processing {file}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\nTotal CSV records: {total_csv_records}")
    print(f"Total system records imported: {total_records}")
    
    # Import product keys
    print(f"\nFound {len(product_files)} product key files:")
    for file in product_files:
        print(f"- {file}")
    
    print("\nProcessing product keys...")
    total_keys = 0
    total_csv_keys = 0
    for file in product_files:
        file_path = os.path.join(base_path, file)
        print(f"\nImporting {file}...")
        try:
            # 使用改進的產品密鑰處理流程
            df = process_product_keys(file_path)
            if df is not None:
                total_csv_keys += len(df)
                if update_product_keys(df, is_dataframe=True):
                    total_keys += len(df)
                    print(f"Successfully imported {len(df)} records from {file}")
                else:
                    print(f"Failed to import {file}")
        except Exception as e:
            print(f"Error processing {file}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\nTotal CSV product keys: {total_csv_keys}")
    print(f"Total product keys imported: {total_keys}")
    
    # Generate new preview
    print("\nGenerating HTML preview...")
    html_path = generate_html_preview()
    if html_path:
        print(f"Updated preview: {html_path}")
        # 在 Windows 中打開預覽文件
        os.startfile(html_path)
    else:
        print("Failed to generate HTML preview")
    
    print("\nDatabase reimport completed!")

def check_database_status():
    """Check current database status"""
    with Database() as db:
        # Check system records
        db.cursor.execute("SELECT COUNT(*) as count FROM system_records")
        system_count = db.cursor.fetchone()['count']
        
        # Check product keys
        db.cursor.execute("SELECT COUNT(*) as count FROM product_keys")
        product_count = db.cursor.fetchone()['count']
        
        # Check TouchScreen values distribution
        db.cursor.execute("""
            SELECT touchscreen, COUNT(*) as count 
            FROM system_records 
            GROUP BY touchscreen 
            ORDER BY count DESC
        """)
        touchscreen_stats = db.cursor.fetchall()
        
        print("\nCurrent database status:")
        print(f"System Records: {system_count}")
        print(f"Product Keys: {product_count}")
        
        print("\nTouchScreen values distribution:")
        for stat in touchscreen_stats:
            print(f"'{stat['touchscreen']}': {stat['count']} records")

def update_system_records(df, is_dataframe=False, db=None):
    """Update system records table with changes from CSV file or DataFrame"""
    if db is None:
        db = Database()
    try:
        with db:
            records_processed = 0
            
            for _, row in df.iterrows():
                try:
                    db.cursor.execute("BEGIN")
                    
                    # 將相同序號的舊記錄標記為非當前
                    if row.get('SerialNumber'):
                        db.cursor.execute("""
                            UPDATE system_records 
                            SET is_current = FALSE 
                            WHERE serialnumber = %(serialnumber)s
                        """, {'serialnumber': row.get('SerialNumber')})
                    
                    # 處理數值型欄位
                    try:
                        design_capacity = int(float(row.get('Design_Capacity', 0)))
                    except (ValueError, TypeError):
                        design_capacity = 0
                        
                    try:
                        full_charge_capacity = int(float(row.get('Full_Charge_Capacity', 0)))
                    except (ValueError, TypeError):
                        full_charge_capacity = 0
                        
                    try:
                        cycle_count = int(float(row.get('Cycle_Count', 0)))
                    except (ValueError, TypeError):
                        cycle_count = 0
                        
                    try:
                        battery_health = float(row.get('Battery_Health', 0))
                    except (ValueError, TypeError):
                        battery_health = 0
                    
                    # 處理磁盤數據 - 完全保持原始格式
                    disks_str = str(row.get('Disks', '')).strip() if pd.notna(row.get('Disks')) else ''
                    disks_data = disks_str  # 直接使用原始格式，不做任何轉換或修改
                    
                    # 處理 touchscreen 欄位，如果為空則設為 "unknown"
                    touchscreen_value = str(row.get('TouchScreen', '')).strip().lower() if pd.notna(row.get('TouchScreen')) else "unknown"
                    
                    # 處理 resolution 欄位
                    resolution_value = str(row.get('Resolution', '')).strip() if pd.notna(row.get('Resolution')) else None
                    if resolution_value:
                        # 提取數字部分
                        match = re.search(r'(\d+)x(\d+)', resolution_value)
                        if match:
                            resolution_value = f"{match.group(1)}x{match.group(2)}"
                        else:
                            resolution_value = None
                    
                    # 插入新記錄，保持原始數據
                    params = {
                        'serialnumber': str(row.get('SerialNumber', '')).strip() if pd.notna(row.get('SerialNumber')) else None,
                        'computername': str(row.get('ComputerName', '')).strip() if pd.notna(row.get('ComputerName')) else None,
                        'manufacturer': str(row.get('Manufacturer', '')).strip() if pd.notna(row.get('Manufacturer')) else None,
                        'model': str(row.get('Model', '')).strip() if pd.notna(row.get('Model')) else None,
                        'systemsku': str(row.get('SystemSKU', '')).strip() if pd.notna(row.get('SystemSKU')) else None,
                        'operatingsystem': str(row.get('OperatingSystem', '')).strip() if pd.notna(row.get('OperatingSystem')) else None,
                        'cpu': str(row.get('CPU', '')).strip() if pd.notna(row.get('CPU')) else None,
                        'resolution': resolution_value,
                        'graphicscard': str(row.get('GraphicsCard', '')).strip() if pd.notna(row.get('GraphicsCard')) else None,
                        'ram_gb': str(row.get('RAM_GB', '')).strip() if pd.notna(row.get('RAM_GB')) else None,
                        'disks': disks_data,
                        'design_capacity': design_capacity,
                        'full_charge_capacity': full_charge_capacity,
                        'cycle_count': cycle_count,
                        'battery_health': battery_health,
                        'touchscreen': touchscreen_value,
                        'created_at': row.get('Timestamp') or row.get('Date') or datetime.now(),
                        'is_current': True
                    }
                    
                    db.cursor.execute("""
                        INSERT INTO system_records (
                            serialnumber, computername, manufacturer, model,
                            systemsku, operatingsystem, cpu, resolution,
                            graphicscard, ram_gb, disks, design_capacity,
                            full_charge_capacity, cycle_count, battery_health,
                            touchscreen, created_at, is_current
                        ) VALUES (
                            %(serialnumber)s, %(computername)s, %(manufacturer)s, %(model)s,
                            %(systemsku)s, %(operatingsystem)s, %(cpu)s, %(resolution)s,
                            %(graphicscard)s, %(ram_gb)s, %(disks)s, %(design_capacity)s,
                            %(full_charge_capacity)s, %(cycle_count)s, %(battery_health)s,
                            %(touchscreen)s, %(created_at)s, %(is_current)s
                        )
                    """, params)
                    
                    records_processed += 1
                    db.cursor.execute("COMMIT")
                    
                except Exception as e:
                    db.cursor.execute("ROLLBACK")
                    print(f"Error processing record: {str(e)}")
                    continue
            
            print(f"Records processed: {records_processed}")
            return records_processed > 0
            
    except Exception as e:
        print(f"Error updating system records: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def update_product_keys(df, is_dataframe=False, db=None):
    """Update product keys table with changes from CSV file or DataFrame"""
    if db is None:
        db = Database()
    try:
        with db:
            records_processed = 0
            
            for _, row in df.iterrows():
                try:
                    db.cursor.execute("BEGIN")
                    
                    # 將相同電腦名稱的舊記錄標記為非當前
                    if row.get('ComputerName'):
                        db.cursor.execute("""
                            UPDATE product_keys 
                            SET is_current = FALSE 
                            WHERE computername = %(computername)s
                        """, {'computername': row.get('ComputerName')})
                    
                    # 插入新記錄，保持原始數據
                    params = {
                        'computername': row.get('ComputerName'),
                        'windowsos_new': row.get('WindowsOS'),
                        'productkey_new': row.get('ProductKey'),
                        'created_at': row.get('Timestamp') or datetime.now(),
                        'is_current': True
                    }
                    
                    db.cursor.execute("""
                        INSERT INTO product_keys (
                            computername, windowsos_new, productkey_new,
                            created_at, is_current
                        ) VALUES (
                            %(computername)s, %(windowsos_new)s, %(productkey_new)s,
                            %(created_at)s, %(is_current)s
                        )
                    """, params)
                    
                    records_processed += 1
                    db.cursor.execute("COMMIT")
                    
                except Exception as e:
                    db.cursor.execute("ROLLBACK")
                    print(f"Error processing record: {str(e)}")
                    continue
            
            print(f"Records processed: {records_processed}")
            return records_processed > 0
            
    except Exception as e:
        print(f"Error updating product keys: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    while True:
        print("\nDatabase Management Tool")
        print("1. Clear database and reimport all data")
        print("2. Check database status")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == '1':
            confirm = input("\nWARNING: This will delete all existing data. Continue? (yes/no): ")
            if confirm.lower() in ['yes', 'y']:
                clear_and_reimport()
        elif choice == '2':
            check_database_status()
        elif choice == '3':
            print("\nExiting...")
            break
        else:
            print("\nInvalid choice. Please try again.") 