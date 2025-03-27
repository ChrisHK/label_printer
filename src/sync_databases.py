from sqldb import Database
import json
from datetime import datetime

def compare_databases():
    """比對兩個數據庫的 system_records"""
    try:
        with Database(db_name='zerodev') as dev_db, Database() as prod_db:
            # 獲取兩個數據庫的記錄數量
            dev_db.cursor.execute("SELECT COUNT(*) as count FROM system_records")
            dev_count = dev_db.cursor.fetchone()['count']
            
            prod_db.cursor.execute("SELECT COUNT(*) as count FROM system_records")
            prod_count = prod_db.cursor.fetchone()['count']
            
            print("\n數據庫記錄數量比對:")
            print(f"開發數據庫 (zerodev): {dev_count} 條記錄")
            print(f"主數據庫 (zerodb): {prod_count} 條記錄")
            
            # 獲取兩個數據庫的最新記錄時間
            dev_db.cursor.execute("SELECT MAX(created_at) as latest FROM system_records")
            dev_latest = dev_db.cursor.fetchone()['latest']
            
            prod_db.cursor.execute("SELECT MAX(created_at) as latest FROM system_records")
            prod_latest = prod_db.cursor.fetchone()['latest']
            
            print("\n最新記錄時間比對:")
            print(f"開發數據庫最新記錄: {dev_latest}")
            print(f"主數據庫最新記錄: {prod_latest}")
            
            # 確定哪個數據庫是源數據庫（記錄更多且更新）
            source_db = None
            target_db = None
            source_name = ""
            target_name = ""
            
            if prod_count > dev_count or (prod_count == dev_count and prod_latest > dev_latest):
                source_db = prod_db
                target_db = dev_db
                source_name = "zerodb"
                target_name = "zerodev"
            else:
                source_db = dev_db
                target_db = prod_db
                source_name = "zerodev"
                target_name = "zerodb"
            
            print(f"\n將使用 {source_name} 作為源數據庫同步到 {target_name}")
            
            return {
                'source_db': source_db,
                'target_db': target_db,
                'source_name': source_name,
                'target_name': target_name,
                'source_count': prod_count if source_name == 'zerodb' else dev_count,
                'target_count': dev_count if source_name == 'zerodb' else prod_count
            }
            
    except Exception as e:
        print(f"比對數據庫時出錯: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def sync_databases():
    """同步兩個數據庫的 system_records"""
    try:
        # 比對數據庫
        result = compare_databases()
        if not result:
            return False
        
        source_name = result['source_name']
        target_name = result['target_name']
        
        # 重新建立數據庫連接
        with Database(db_name=source_name) as source_db, Database(db_name=target_name) as target_db:
            # 開始同步
            print("\n開始同步...")
            
            # 1. 備份目標數據庫
            print(f"備份 {target_name} 數據庫...")
            target_db.cursor.execute("""
                DROP TABLE IF EXISTS system_records_backup;
                CREATE TABLE system_records_backup AS 
                SELECT * FROM system_records;
            """)
            target_db.connection.commit()
            
            # 2. 獲取源數據庫的所有記錄
            print(f"讀取 {source_name} 的記錄...")
            source_db.cursor.execute("""
                SELECT 
                    serialnumber, manufacturer, model, systemsku,
                    operatingsystem, cpu, resolution, graphicscard,
                    touchscreen, ram_gb, disks, design_capacity,
                    full_charge_capacity, cycle_count, battery_health,
                    created_at, is_current, sync_status, last_sync_time,
                    sync_version, started_at
                FROM system_records 
                ORDER BY id
            """)
            records = source_db.cursor.fetchall()
            
            # 3. 清空目標數據庫
            print(f"清空 {target_name} 的 system_records 表...")
            target_db.cursor.execute("TRUNCATE TABLE system_records CASCADE")
            target_db.connection.commit()
            
            # 4. 同步記錄
            print("開始同步記錄...")
            records_processed = 0
            
            for record in records:
                try:
                    target_db.cursor.execute("""
                        INSERT INTO system_records (
                            serialnumber, manufacturer, model, systemsku,
                            operatingsystem, cpu, resolution, graphicscard,
                            touchscreen, ram_gb, disks, design_capacity,
                            full_charge_capacity, cycle_count, battery_health,
                            created_at, is_current, sync_status, last_sync_time,
                            sync_version, started_at
                        ) VALUES (
                            %(serialnumber)s, %(manufacturer)s, %(model)s, %(systemsku)s,
                            %(operatingsystem)s, %(cpu)s, %(resolution)s, %(graphicscard)s,
                            %(touchscreen)s, %(ram_gb)s, %(disks)s, %(design_capacity)s,
                            %(full_charge_capacity)s, %(cycle_count)s, %(battery_health)s,
                            %(created_at)s, %(is_current)s, %(sync_status)s, %(last_sync_time)s,
                            %(sync_version)s, %(started_at)s
                        )
                    """, record)
                    records_processed += 1
                    
                    # 每100條記錄提交一次事務
                    if records_processed % 100 == 0:
                        target_db.connection.commit()
                        print(f"已同步 {records_processed} 條記錄...")
                    
                except Exception as e:
                    print(f"同步記錄時出錯: {str(e)}")
                    print(f"問題記錄: {record}")
                    continue
            
            # 提交剩餘的事務
            target_db.connection.commit()
            
            # 5. 重置序列
            target_db.cursor.execute("""
                SELECT setval('system_records_id_seq', 
                    (SELECT COALESCE(MAX(id), 0) FROM system_records)
                );
            """)
            target_db.connection.commit()
            
            # 6. 驗證同步結果
            print("\n驗證同步結果...")
            source_db.cursor.execute("SELECT COUNT(*) as count FROM system_records")
            source_final_count = source_db.cursor.fetchone()['count']
            
            target_db.cursor.execute("SELECT COUNT(*) as count FROM system_records")
            target_final_count = target_db.cursor.fetchone()['count']
            
            print(f"\n同步完成！")
            print(f"源數據庫 ({source_name}) 記錄數: {source_final_count}")
            print(f"目標數據庫 ({target_name}) 記錄數: {target_final_count}")
            
            if source_final_count == target_final_count:
                print("\n數據同步成功！兩個數據庫記錄數量一致。")
                return True
            else:
                print("\n警告：同步後記錄數量不一致！")
                print("建議檢查日誌以了解可能的錯誤原因。")
                return False
            
    except Exception as e:
        print(f"同步過程中出錯: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sync_databases() 