from sqldb import Database
from datetime import datetime, timezone, timedelta

def import_test_data():
    """導入測試資料"""
    with Database() as db:
        try:
            # 創建測試資料
            test_data = [
                {
                    'serialnumber': 'TEST001',
                    'manufacturer': 'Test Manufacturer',
                    'model': 'Test Model',
                    'systemsku': 'TEST-SKU-001',
                    'operatingsystem': 'Windows 10 Pro',
                    'cpu': 'Intel Core i7',
                    'graphicscard': 'NVIDIA GeForce RTX 3060',
                    'ram_gb': 16,
                    'disks': '512GB SSD',
                    'full_charge_capacity': 45000,
                    'battery_health': 95,
                    'touchscreen': 'Yes',
                    'created_at': datetime.now(timezone(timedelta(hours=8))),  # UTC+8
                    'is_current': True,
                    'sync_status': 'pending',
                    'sync_version': 1,
                    'started_at': datetime.now(timezone(timedelta(hours=8)))  # UTC+8
                },
                {
                    'serialnumber': 'TEST002',
                    'manufacturer': 'Test Manufacturer',
                    'model': 'Test Model Pro',
                    'systemsku': 'TEST-SKU-002',
                    'operatingsystem': 'Windows 11 Pro',
                    'cpu': 'Intel Core i9',
                    'graphicscard': 'NVIDIA GeForce RTX 4080',
                    'ram_gb': 32,
                    'disks': '1TB SSD',
                    'full_charge_capacity': 52000,
                    'battery_health': 98,
                    'touchscreen': 'Yes',
                    'created_at': datetime.now(timezone(timedelta(hours=8))),  # UTC+8
                    'is_current': True,
                    'sync_status': 'pending',
                    'sync_version': 1,
                    'started_at': datetime.now(timezone(timedelta(hours=8)))  # UTC+8
                }
            ]
            
            # 插入測試資料
            for data in test_data:
                db.cursor.execute("""
                    INSERT INTO system_records (
                        serialnumber, manufacturer, model, systemsku,
                        operatingsystem, cpu, graphicscard, ram_gb,
                        disks, full_charge_capacity, battery_health,
                        touchscreen, created_at, is_current, sync_status,
                        sync_version, started_at
                    ) VALUES (
                        %(serialnumber)s, %(manufacturer)s, %(model)s, %(systemsku)s,
                        %(operatingsystem)s, %(cpu)s, %(graphicscard)s, %(ram_gb)s,
                        %(disks)s, %(full_charge_capacity)s, %(battery_health)s,
                        %(touchscreen)s, %(created_at)s, %(is_current)s, %(sync_status)s,
                        %(sync_version)s, %(started_at)s
                    )
                """, data)
            
            db.connection.commit()
            print("Test data imported successfully")
            return True
            
        except Exception as e:
            print(f"Error importing test data: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    import_test_data() 