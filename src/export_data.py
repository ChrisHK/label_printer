from sqldb import Database
import json
from datetime import datetime
import os
import pandas as pd

def export_system_records(source_db='zerodb', target_db='zerodev'):
    """在兩個數據庫之間導出/導入 system_records 表數據"""
    try:
        print(f"\n正在從 {source_db} 導出數據到 {target_db}...")
        
        # 連接源數據庫
        with Database(db_name=source_db) as source:
            # 驗證數據庫連接
            source.cursor.execute("SELECT current_database()")
            current_db = source.cursor.fetchone()['current_database']
            print(f"已連接到源數據庫: {current_db}")
            
            # 檢查表是否存在
            source.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'system_records'
                )
            """)
            table_exists = source.cursor.fetchone()['exists']
            
            if not table_exists:
                print(f"錯誤：{source_db} 數據庫中不存在 system_records 表")
                return False
            
            # 檢查表中的記錄數
            source.cursor.execute("SELECT COUNT(*) as count FROM system_records")
            total_count = source.cursor.fetchone()['count']
            print(f"表中總記錄數：{total_count}")
            
            # 檢查最新的記錄
            source.cursor.execute("""
                SELECT created_at, serialnumber
                FROM system_records
                ORDER BY created_at DESC
                LIMIT 1
            """)
            latest = source.cursor.fetchone()
            if latest:
                print(f"最新記錄時間：{latest['created_at']}")
                print(f"最新記錄序號：{latest['serialnumber']}")
            
            # 獲取所有記錄
            print(f"正在從 {source_db} 數據庫讀取數據...")
            source.cursor.execute("""
                SELECT 
                    id, serialnumber, computername, manufacturer, model,
                    systemsku, operatingsystem, cpu, resolution, graphicscard,
                    touchscreen, ram_gb, disks, design_capacity,
                    full_charge_capacity, cycle_count, battery_health,
                    created_at, is_current, sync_status, last_sync_time,
                    sync_version, started_at
                FROM system_records 
                ORDER BY id
            """)
            records = source.cursor.fetchall()
            
            print(f"從 {source_db} 讀取到 {len(records)} 條記錄")
            
            if len(records) == 0:
                print("警告：沒有找到任何記錄")
                return False
            
            # 顯示第一條記錄的示例（如果有）
            if records:
                print("\n第一條記錄示例：")
                for key, value in records[0].items():
                    print(f"{key}: {value}")
            
            # 連接目標數據庫
            with Database(db_name=target_db) as target:
                # 驗證數據庫連接
                target.cursor.execute("SELECT current_database()")
                current_db = target.cursor.fetchone()['current_database']
                print(f"\n已連接到目標數據庫: {current_db}")
                
                # 開始事務
                target.cursor.execute("BEGIN")
                try:
                    # 檢查目標表中的現有記錄
                    target.cursor.execute("SELECT COUNT(*) as count FROM system_records")
                    target_count = target.cursor.fetchone()['count']
                    print(f"目標數據庫中現有記錄數: {target_count}")
                    
                    # 清空目標表
                    print(f"清空 {target_db} 數據庫的 system_records 表...")
                    target.cursor.execute("TRUNCATE TABLE system_records CASCADE")
                    
                    # 重置序列
                    target.cursor.execute("ALTER SEQUENCE system_records_id_seq RESTART WITH 1")
                    
                    # 導入記錄
                    print("正在導入記錄...")
                    records_count = 0
                    errors_count = 0
                    for record in records:
                        try:
                            # 構建 INSERT 語句
                            columns = record.keys()
                            values = []
                            
                            for key in columns:
                                value = record[key]
                                if value is None:
                                    values.append('NULL')
                                elif isinstance(value, bool):
                                    values.append(str(value).lower())
                                elif isinstance(value, (int, float)):
                                    # 保留原始數值，包括 NaN
                                    if pd.isna(value):
                                        values.append('NULL')
                                    else:
                                        values.append(str(value))
                                elif isinstance(value, datetime):
                                    values.append(f"'{value.isoformat()}'")
                                elif key == 'disks':
                                    # 直接使用原始字串，不做 JSON 轉換
                                    if value:
                                        # 處理字符串中的單引號
                                        escaped_value = str(value).replace("'", "''")
                                        values.append(f"'{escaped_value}'")
                                    else:
                                        values.append('NULL')
                                else:
                                    # 處理字符串中的單引號
                                    escaped_value = str(value).replace("'", "''")
                                    values.append(f"'{escaped_value}'")
                            
                            # 寫入 INSERT 語句
                            columns_str = ', '.join(columns)
                            values_str = ', '.join(values)
                            insert_sql = f"INSERT INTO system_records ({columns_str}) VALUES ({values_str})"
                            
                            try:
                                target.cursor.execute(insert_sql)
                                records_count += 1
                            except Exception as e:
                                print(f"\n插入記錄時出錯:")
                                print(f"SQL: {insert_sql}")
                                print(f"錯誤: {str(e)}")
                                errors_count += 1
                            
                            # 顯示進度
                            if records_count % 100 == 0:
                                print(f"已處理 {records_count} 條記錄...")
                        
                        except Exception as e:
                            print(f"處理記錄時出錯: {str(e)}")
                            errors_count += 1
                            continue
                    
                    # 更新序列
                    target.cursor.execute("SELECT setval('system_records_id_seq', (SELECT MAX(id) FROM system_records))")
                    
                    # 提交事務
                    target.cursor.execute("COMMIT")
                    
                    print(f"\n導入完成！")
                    print(f"總共處理 {len(records)} 條記錄")
                    print(f"成功導入 {records_count} 條記錄")
                    print(f"失敗 {errors_count} 條記錄")
                    
                    # 驗證導入後的記錄數
                    target.cursor.execute("SELECT COUNT(*) as count FROM system_records")
                    final_count = target.cursor.fetchone()['count']
                    print(f"導入後的記錄總數: {final_count}")
                    
                    return True
                    
                except Exception as e:
                    target.cursor.execute("ROLLBACK")
                    raise e
            
    except Exception as e:
        print(f"導出過程中出錯: {str(e)}")
        print("\n詳細錯誤信息：")
        import traceback
        traceback.print_exc()
        return False

def check_database(db_name):
    """檢查數據庫狀態"""
    try:
        print(f"\n檢查 {db_name} 數據庫狀態...")
        with Database(db_name=db_name) as db:
            # 檢查表是否存在
            db.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'system_records'
                )
            """)
            table_exists = db.cursor.fetchone()['exists']
            print(f"system_records 表存在: {table_exists}")
            
            if table_exists:
                # 檢查表結構
                db.cursor.execute("""
                    SELECT column_name, data_type, character_maximum_length
                    FROM information_schema.columns
                    WHERE table_name = 'system_records'
                    ORDER BY ordinal_position;
                """)
                columns = db.cursor.fetchall()
                print("\n表結構:")
                for col in columns:
                    print(f"- {col['column_name']}: {col['data_type']}")
                
                # 檢查記錄數
                db.cursor.execute("SELECT COUNT(*) as count FROM system_records")
                total_count = db.cursor.fetchone()['count']
                print(f"\n總記錄數: {total_count}")
                
                # 檢查所有記錄
                db.cursor.execute("""
                    SELECT serialnumber, manufacturer, model, created_at, is_current
                    FROM system_records
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                records = db.cursor.fetchall()
                if records:
                    print("\n最新5條記錄:")
                    for record in records:
                        print(f"- {record['created_at']} | {record['serialnumber']} | {record['manufacturer']} | {record['model']} | 當前: {record['is_current']}")
                
                # 檢查是否有約束條件
                db.cursor.execute("""
                    SELECT con.conname, con.contype, pg_get_constraintdef(con.oid)
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    WHERE rel.relname = 'system_records'
                """)
                constraints = db.cursor.fetchall()
                if constraints:
                    print("\n表的約束條件:")
                    for con in constraints:
                        print(f"- {con['conname']}: {con['pg_get_constraintdef']}")
                
                # 檢查是否有錯誤的數據
                db.cursor.execute("""
                    SELECT COUNT(*) as count, 
                           COUNT(CASE WHEN battery_health IS NULL THEN 1 END) as null_battery,
                           COUNT(CASE WHEN battery_health < 0 OR battery_health > 200 THEN 1 END) as invalid_battery,
                           COUNT(CASE WHEN cycle_count < 0 THEN 1 END) as negative_cycle,
                           COUNT(CASE WHEN design_capacity < 0 THEN 1 END) as negative_design,
                           COUNT(CASE WHEN full_charge_capacity < 0 THEN 1 END) as negative_full
                    FROM system_records
                """)
                stats = db.cursor.fetchone()
                print("\n數據統計:")
                print(f"- 空的電池健康度: {stats['null_battery']}")
                print(f"- 超出範圍的電池健康度: {stats['invalid_battery']}")
                print(f"- 負的循環次數: {stats['negative_cycle']}")
                print(f"- 負的設計容量: {stats['negative_design']}")
                print(f"- 負的完全充電容量: {stats['negative_full']}")
            
            return table_exists
            
    except Exception as e:
        print(f"檢查數據庫時出錯: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def show_menu():
    """顯示主菜單"""
    while True:
        print("\n數據庫導入工具")
        print("1. 從 zerodb 導入到 zerodev")
        print("2. 從 zerodev 導入到 zerodb")
        print("3. 檢查 zerodb 狀態")
        print("4. 檢查 zerodev 狀態")
        print("5. 退出")
        
        choice = input("\n請選擇操作 (1-5): ")
        
        if choice == '1':
            confirm = input("\n警告：這將清空 zerodev 數據庫中的數據。是否繼續？(yes/no): ")
            if confirm.lower() in ['yes', 'y']:
                export_system_records('zerodb', 'zerodev')
        elif choice == '2':
            confirm = input("\n警告：這將清空 zerodb 數據庫中的數據。是否繼續？(yes/no): ")
            if confirm.lower() in ['yes', 'y']:
                export_system_records('zerodev', 'zerodb')
        elif choice == '3':
            check_database('zerodb')
        elif choice == '4':
            check_database('zerodev')
        elif choice == '5':
            print("\n退出程序...")
            break
        else:
            print("\n無效的選擇，請重試。")

if __name__ == "__main__":
    show_menu() 