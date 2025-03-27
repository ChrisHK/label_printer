import asyncio
import aiohttp
import ssl
import os
import json
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from .logger import SyncLogger
from .data_formatter import DataFormatter
from sqldb import Database
import hashlib

# 定義 UTC-5 時區
UTC_MINUS_5 = timezone(timedelta(hours=-5))

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            # 確保時間戳有時區信息，並保持在 UTC-5
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=UTC_MINUS_5)
            return obj.isoformat()
        return super().default(obj)

class InventorySync:
    def __init__(self, env: str = "dev"):
        """初始化同步管理器"""
        self.env = env
        self.base_urls = {
            "test": "https://httpbin.org",
            "dev": "https://erp.zerounique.com",
            "prod": "https://erp.zerounique.com"
        }
        self.urls = {
            "test": f"{self.base_urls['test']}/post",
            "dev": f"{self.base_urls['dev']}/api/data-process/inventory",
            "prod": f"{self.base_urls['prod']}/api/data-process/inventory"
        }
        self.auth_token = os.getenv('ERP_API_TOKEN')
        self.logger = SyncLogger()
        self.last_sync_time: Optional[datetime] = None
        self.formatter = DataFormatter()

    def _normalize_item(self, item: Dict) -> Dict:
        """規範化單個項目，只保留 serialnumber
        
        Args:
            item: 單個項目字典
            
        Returns:
            dict: 只包含 serialnumber 的字典
        """
        return {
            "serialnumber": str(item.get("serialnumber", ""))
        }

    def _calculate_checksum(self, items: List[Dict]) -> str:
        """計算校驗和（只使用 serialnumber）
        
        Args:
            items: 項目列表
            
        Returns:
            str: SHA-256 校驗和
        """
        if not isinstance(items, list):
            raise ValueError("Input must be an array")

        # 格式化並排序項目
        normalized_items = [self._normalize_item(item) for item in items]
        sorted_items = sorted(normalized_items, key=lambda x: x["serialnumber"])
        
        # 轉換為 JSON 字符串（無空格）
        json_string = json.dumps(sorted_items, separators=(',', ':'))
        
        # 計算 SHA-256
        return hashlib.sha256(json_string.encode('utf-8')).hexdigest()

    def _normalize_record(self, record: Dict) -> Dict:
        """規範化記錄格式
        
        Args:
            record: 原始記錄
            
        Returns:
            dict: 規範化後的記錄
        """
        # 解析磁盤信息
        disks = []
        disks_str = str(record.get('disks', ''))
        if disks_str:
            disk_parts = disks_str.split(',')
            for disk_str in disk_parts:
                if disk_str.strip():
                    try:
                        type_, size, model = disk_str.strip().split(':')
                        # 解析大小為數字
                        size_num = float(size.replace('TB', '000').replace('GB', ''))
                        disks.append({
                            'size_gb': size_num
                        })
                    except:
                        # 如果解析失敗，添加一個空的磁盤記錄
                        disks.append({
                            'size_gb': 0
                        })
        
        # 構建規範化的記錄
        normalized = {
            'serialnumber': str(record.get('serialnumber', '')),
            'manufacturer': str(record.get('manufacturer', '')),
            'model': str(record.get('model', '')),
            'ram_gb': float(record.get('ram_gb', 0)),
            'disks': disks
        }
        
        # 如果有電池信息，添加到記錄中
        if record.get('full_charge_capacity') is not None and record.get('battery_health') is not None:
            normalized['battery'] = {
                'cycle_count': 0,  # 默認值
                'design_capacity': float(record.get('full_charge_capacity', 0)),
                'health': float(record.get('battery_health', 0))
            }
        
        return normalized

    async def login(self, username: str, password: str) -> bool:
        """登入並獲取token"""
        if self.env not in ["dev", "prod"]:
            return False

        url = f"{self.base_urls[self.env]}/api/users/login"
        
        # 設置SSL上下文和超時
        ssl_context = ssl.create_default_context()
        if self.env == "dev":
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        # 設置超時
        timeout = aiohttp.ClientTimeout(total=10)  # 10秒超時
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                self.logger.info(f"Attempting to login to {url}")
                async with session.post(
                    url,
                    json={"username": username, "password": password},
                    ssl=ssl_context
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # 假設返回的token在data.token中
                        self.auth_token = data.get('token')
                        self.logger.info("Successfully logged in and got token")
                        return True
                    else:
                        error_data = await response.json()
                        self.logger.error(f"Login failed with status {response.status}: {error_data}")
                        return False
        except asyncio.TimeoutError:
            self.logger.error(f"Login request timed out after 10 seconds")
            return False
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error during login: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during login: {str(e)}", exc_info=e)
            return False

    async def _send_to_api(self, data: Dict) -> Dict:
        """發送數據到API"""
        url = self.urls[self.env]
        batch_id = data.get('batch_id', f"SYNC_{datetime.now(UTC_MINUS_5).strftime('%Y%m%d_%H%M%S')}")
        
        self.logger.info(f"Starting sync batch: {batch_id}")
        
        # 確保有 started_at 字段，並且帶有時區信息
        if 'started_at' not in data:
            data['started_at'] = datetime.now(UTC_MINUS_5)
        elif isinstance(data['started_at'], str):
            try:
                data['started_at'] = datetime.fromisoformat(data['started_at'])
            except ValueError:
                data['started_at'] = datetime.now(UTC_MINUS_5)
        
        if isinstance(data['started_at'], datetime) and data['started_at'].tzinfo is None:
            data['started_at'] = data['started_at'].replace(tzinfo=UTC_MINUS_5)
        
        # 打印請求數據以進行調試
        self.logger.info(f"Request data: {json.dumps(data, cls=CustomJSONEncoder)}")
        
        # 設置超時時間和SSL上下文
        timeout = aiohttp.ClientTimeout(total=30)
        ssl_context = ssl.create_default_context()
        if self.env in ["dev", "test"]:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        # 準備headers
        headers = {
            'Content-Type': 'application/json',
            'X-Sync-Version': '1.0',  # 添加版本信息
            'X-Batch-ID': batch_id    # 添加批次ID
        }
        if self.env in ["dev", "prod"] and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        elif self.env in ["dev", "prod"] and not self.auth_token:
            raise ValueError("Authentication token is required for dev/prod environment")
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                # 序列化數據
                request_data = json.dumps(data, cls=CustomJSONEncoder)
                self.logger.info(f"Final request data: {request_data}")
                
                async with session.post(url, data=request_data, ssl=ssl_context, headers=headers) as response:
                    response_data = await response.json()
                    
                    # 簡化響應處理
                    if response.status == 200:
                        return {
                            'success': True,
                            'batch_id': batch_id,
                            'sync_version': response_data.get('version', '1.0'),
                            'items_processed': len(data.get('items', [])),
                            'timestamp': datetime.now(UTC_MINUS_5).isoformat()
                        }
                    else:
                        self.logger.error(f"API error for batch {batch_id}: Status {response.status}, Response: {response_data}")
                        return {
                            'success': False,
                            'error': response_data.get('error', 'Unknown error'),
                            'batch_id': batch_id,
                            'status_code': response.status
                        }
                    
            except Exception as e:
                self.logger.error(f"Error sending data to API: {str(e)}", exc_info=e)
                raise

    async def sync(self) -> Dict:
        """執行同步操作"""
        try:
            with Database() as db:
                # 獲取更新的記錄
                records = db.get_updated_records(self.last_sync_time)
                
                if not records:
                    self.logger.info("No updates found")
                    return {"status": "no_updates"}
                
                # 規範化記錄
                normalized_records = [self._normalize_record(record) for record in records]
                
                # 生成批次ID
                batch_id = f"SYNC_{datetime.now(UTC_MINUS_5).strftime('%Y%m%d_%H%M%S')}"
                
                # 發送到API
                result = await self.send_batch(
                    batch_id=batch_id,
                    records=normalized_records
                )
                
                # 如果同步成功，更新本地記錄狀態
                if result.get('success'):
                    # 更新記錄狀態
                    update_query = """
                        UPDATE system_records
                        SET sync_status = 'synced',
                            last_sync_time = NOW(),
                            sync_version = %s::numeric
                        WHERE serialnumber = ANY(%s)
                    """
                    serialnumbers = [record.get('serialnumber') for record in normalized_records]
                    db.execute_query(update_query, (result.get('sync_version', '1.0'), serialnumbers))
                    
                    self.last_sync_time = datetime.now(UTC_MINUS_5)
                    self.logger.info(f"Successfully synced {len(records)} records")
                    
                    return {
                        "status": "success",
                        "synced_records": len(records),
                        "batch_id": batch_id,
                        "sync_version": result.get('sync_version', '1.0')
                    }
                else:
                    self.logger.error(f"Sync failed: {result.get('error')}")
                    return {
                        "status": "error",
                        "error": result.get('error'),
                        "batch_id": batch_id
                    }
                
        except Exception as e:
            self.logger.error("Sync failed", exc_info=e)
            return {
                "status": "error",
                "message": str(e)
            }

    async def get_sync_status(self) -> Dict:
        """獲取同步狀態"""
        try:
            batch_id = f"STATUS_{datetime.now(UTC_MINUS_5).strftime('%Y%m%d_%H%M%S')}"
            
            # 發送空的記錄列表來獲取狀態
            result = await self.send_batch(batch_id, [])
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get sync status: {str(e)}")
            return {'error': str(e)}

    async def send_batch(self, batch_id: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send a batch of records to the API."""
        normalized_records = [self._normalize_record(record) for record in records]
        checksum = self._calculate_checksum(normalized_records)
        
        # 生成帶時區的時間戳
        now = datetime.now(UTC_MINUS_5)
        
        data = {
            "batch_id": batch_id,
            "source": "python_sync",
            "sync_version": "1.0",
            "items": normalized_records,
            "metadata": {
                "total_items": len(normalized_records),
                "version": "1.0",
                "checksum": checksum
            },
            "started_at": now  # Pass datetime object directly
        }
        
        return await self._send_to_api(data)

    async def verify_sync_status(self):
        """驗證同步狀態"""
        try:
            # 獲取本地狀態
            local_stats = self.get_sync_stats()
            
            # 生成批次ID
            batch_id = f"STATUS_{datetime.now(UTC_MINUS_5).strftime('%Y%m%d_%H%M%S')}"
            
            # 獲取服務器狀態
            response = await self.api.send_batch(
                batch_id=batch_id,
                records=[]
            )
            server_version = response.get('current_version')
            
            return {
                'is_synced': local_stats.latest_version == server_version,
                'local_version': local_stats.latest_version,
                'server_version': server_version,
                'pending_records': local_stats.pending_records,
                'last_sync_time': local_stats.last_sync_time
            }

        except Exception as e:
            self.logger.error(f"Status verification failed: {str(e)}")
            return {
                'is_synced': False,
                'error': str(e)
            }

async def run_sync(env: str = "dev"):
    """運行同步的便捷函數"""
    sync_manager = InventorySync(env)
    return await sync_manager.sync()

if __name__ == "__main__":
    asyncio.run(run_sync()) 