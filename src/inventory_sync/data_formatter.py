import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any

class DataFormatter:
    @staticmethod
    def format_disk_info(disks_str: str) -> List[Dict[str, Any]]:
        """將數據庫中的磁盤信息字符串轉換為結構化數據"""
        if not disks_str:
            return []
        
        disks = []
        try:
            # 假設格式為: "SSD:512GB:Samsung PM991,HDD:1TB:WD Blue"
            for disk in disks_str.split(','):
                if not disk.strip():
                    continue
                type_, size, model = disk.strip().split(':')
                # 轉換大小為GB
                size_num = size.replace('TB', '000').replace('GB', '')
                size_gb = int(size_num)
                
                disks.append({
                    "type": type_,
                    "size_gb": size_gb,
                    "model": model
                })
        except Exception as e:
            print(f"Error parsing disk info: {disks_str}, Error: {str(e)}")
        
        return disks

    @staticmethod
    def calculate_checksum(items: List[Dict]) -> str:
        """計算 items 數組的 SHA256 校驗和
        
        Args:
            items: 要計算校驗和的項目列表
            
        Returns:
            str: SHA256 校驗和的十六進制字符串
        
        Note:
            校驗和是通過將 items 轉換為 JSON 字符串後計算 SHA256 得到的
            JSON 字符串必須保持一致的格式，包括：
            - 字段順序
            - 不添加額外空格
            - 使用雙引號
        """
        # 確保字段順序一致
        formatted_items = []
        for item in items:
            formatted_item = {
                "serialnumber": item["serialnumber"],
                "computername": item["computername"],
                "manufacturer": item["manufacturer"],
                "model": item["model"],
                "ram_gb": item["ram_gb"],
                "disks": item["disks"],
                "battery": {
                    "design_capacity": item["battery"]["design_capacity"],
                    "cycle_count": item["battery"]["cycle_count"],
                    "health": item["battery"]["health"]
                }
            }
            formatted_items.append(formatted_item)
        
        # 轉換為 JSON 字符串，不添加額外空格
        items_json = json.dumps(formatted_items, separators=(',', ':'))
        return hashlib.sha256(items_json.encode('utf-8')).hexdigest()

    @classmethod
    def format_record(cls, record: Dict[str, Any]) -> Dict[str, Any]:
        """格式化單條記錄"""
        formatted = {
            "serialnumber": record["SerialNumber"],
            "computername": record.get("ComputerName", ""),
            "manufacturer": record["Manufacturer"],
            "model": record["Model"],
            "systemsku": record["SystemSKU"],
            "operatingsystem": record["OperatingSystem"],
            "cpu": record["CPU"],
            "graphicscard": record["GraphicsCard"],
            "touchscreen": record["TouchScreen"],
            "ram_gb": record["RAM_GB"],
            "disks": cls.format_disk_info(record["Disks"]),
        }
        
        # 添加電池相關信息（如果有）
        if "Full_Charge_Capacity" in record:
            formatted.update({
                "full_charge_capacity": record["Full_Charge_Capacity"],
                "battery_health": record["Battery_Health"]
            })
        
        return formatted

    @classmethod
    def prepare_sync_data(cls, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """準備同步數據的JSON格式"""
        formatted_items = [
            cls.format_record(record)
            for record in records
            if record.get("SerialNumber")  # 確保有序列號
        ]
        
        sync_data = {
            "source": "external_system",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "batch_id": f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "items": formatted_items,
            "metadata": {
                "total_items": len(formatted_items),
                "version": "1.0",
                "checksum": cls.calculate_checksum(formatted_items)
            }
        }
        
        return sync_data 