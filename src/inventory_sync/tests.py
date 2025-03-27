import asyncio
import json
from datetime import datetime
from typing import Dict, List
from pathlib import Path
from inventory_sync.data_formatter import DataFormatter
from inventory_sync.sync_manager import InventorySync
from inventory_sync.logger import SyncLogger

class MockDatabase:
    """模擬數據庫類"""
    def get_updated_records(self, last_sync_time=None) -> List[Dict]:
        return [
            {
                "SerialNumber": "TEST123",
                "ComputerName": "TEST-PC-1",
                "Manufacturer": "Dell",
                "Model": "Latitude 5420",
                "SystemSKU": "SKU123",
                "OperatingSystem": "Windows 10 Pro",
                "CPU": "Intel Core i5-1135G7",
                "GraphicsCard": "Intel Iris Xe Graphics",
                "TouchScreen": False,
                "RAM_GB": 16,
                "Disks": "SSD:512GB:Samsung PM991",
                "Full_Charge_Capacity": 6000,
                "Battery_Health": 98,
                "updated_at": datetime.now()
            }
        ]

def test_data_formatter():
    """測試數據格式轉換"""
    print("\n=== Testing Data Formatter ===")
    
    # 測試數據
    test_record = {
        "SerialNumber": "TEST123",
        "ComputerName": "TEST-PC-1",
        "Manufacturer": "Dell",
        "Model": "Latitude 5420",
        "SystemSKU": "SKU123",
        "OperatingSystem": "Windows 10 Pro",
        "CPU": "Intel Core i5-1135G7",
        "GraphicsCard": "Intel Iris Xe Graphics",
        "TouchScreen": False,
        "RAM_GB": 16,
        "Disks": "SSD:512GB:Samsung PM991",
        "Full_Charge_Capacity": 6000,
        "Battery_Health": 98
    }
    
    formatter = DataFormatter()
    
    # 測試磁盤信息格式化
    print("\nTesting disk info formatting:")
    disks = formatter.format_disk_info(test_record["Disks"])
    print(f"Formatted disks: {json.dumps(disks, indent=2)}")
    
    # 測試記錄格式化
    print("\nTesting record formatting:")
    formatted_record = formatter.format_record(test_record)
    print(f"Formatted record: {json.dumps(formatted_record, indent=2)}")
    
    # 測試完整數據準備
    print("\nTesting full data preparation:")
    full_data = formatter.prepare_sync_data([test_record])
    print(f"Prepared data: {json.dumps(full_data, indent=2)}")

async def test_sync_manager():
    """測試同步管理器"""
    print("\n=== Testing Sync Manager (Production) ===")
    
    # 初始化同步管理器，使用生產環境
    sync_manager = InventorySync(env="prod")
    
    # 首先進行登入
    print("\nTesting login:")
    login_success = await sync_manager.login("admin", "admin123")
    if not login_success:
        print("Login failed, skipping API test")
        return
    
    print("Login successful, proceeding with API test")
    
    # 準備測試數據
    test_data = {
        "source": "test",
        "timestamp": "2024-03-22T08:30:00.000Z",
        "batch_id": "TEST_001",
        "items": [{
            "serialnumber": "TEST123",
            "computername": "TEST-PC-1",
            "manufacturer": "Dell",
            "model": "Latitude 5420",
            "ram_gb": 16,
            "disks": [{"size_gb": 512}],
            "battery": {
                "design_capacity": 6000,
                "cycle_count": 50,
                "health": 98
            }
        }],
        "metadata": {
            "total_items": 1,
            "version": "1.0",
            "checksum": None  # Will be calculated before sending
        }
    }
    
    # 計算 checksum
    test_data["metadata"]["checksum"] = DataFormatter.calculate_checksum(test_data["items"])
    
    try:
        # 測試API調用
        print("\nTesting Production API call:")
        result = await sync_manager._send_to_api(test_data)
        print(f"API response: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"API call failed: {str(e)}")

def test_logger():
    """測試日誌系統"""
    print("\n=== Testing Logger ===")
    
    # 設置測試日誌目錄
    test_log_dir = "test_logs"
    logger = SyncLogger(log_dir=test_log_dir)
    
    # 測試各種日誌級別
    print("\nTesting different log levels:")
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")
    
    # 測試同步相關的日誌
    logger.log_sync_start("TEST_BATCH_001")
    logger.log_sync_complete("TEST_BATCH_001", {
        "total": 1,
        "success": 1,
        "failed": 0
    })
    
    # 檢查日誌文件
    log_file = Path(test_log_dir) / f"inventory_sync_{datetime.now().strftime('%Y%m%d')}.log"
    print(f"\nLog file created at: {log_file}")
    if log_file.exists():
        print("Log file successfully created")
    else:
        print("Error: Log file not created")

async def run_tests():
    """運行所有測試"""
    try:
        # 測試數據格式轉換
        test_data_formatter()
        
        # 測試日誌系統
        test_logger()
        
        # 測試同步管理器
        await test_sync_manager()
        
        print("\n=== All tests completed ===")
        
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(run_tests()) 