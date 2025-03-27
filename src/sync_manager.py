import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass
from sqldb import Database
from inventory_sync.sync_manager import InventorySync
import json

@dataclass
class SyncStats:
    total_records: int
    synced_records: int
    pending_records: int
    latest_version: float
    last_sync_time: Optional[datetime]

class SystemRecordSyncManager:
    def __init__(self, db: Database, api: InventorySync):
        self.db = db
        self.api = api
        self.logger = logging.getLogger("sync_manager")
        self._setup_logging()

    def _setup_logging(self):
        """設置日誌記錄"""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def get_sync_stats(self) -> SyncStats:
        """獲取同步統計信息"""
        query = """
            SELECT 
                COUNT(*) as total_records,
                COUNT(*) FILTER (WHERE sync_status = 'synced') as synced_records,
                COUNT(*) FILTER (WHERE sync_status = 'pending') as pending_records,
                COALESCE(MAX(sync_version), 0.0) as latest_version,
                MAX(last_sync_time) as last_sync_time
            FROM system_records
        """
        with self.db:
            self.db.cursor.execute(query)
            stats = self.db.cursor.fetchone()
            return SyncStats(
                total_records=stats['total_records'],
                synced_records=stats['synced_records'],
                pending_records=stats['pending_records'],
                latest_version=float(stats['latest_version']),
                last_sync_time=stats['last_sync_time']
            )

    def get_records_to_sync(self, batch_size: int = 100) -> List[Dict]:
        """獲取需要同步的記錄"""
        query = """
            SELECT 
                id,
                serialnumber,
                computername,
                manufacturer,
                model,
                systemsku,
                operatingsystem,
                cpu,
                resolution,
                graphicscard,
                touchscreen,
                ram_gb,
                disks,
                design_capacity,
                full_charge_capacity,
                cycle_count,
                battery_health,
                created_at
            FROM system_records
            WHERE sync_status = 'pending'
            ORDER BY id
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        """
        with self.db:
            self.db.cursor.execute(query, (batch_size,))
            records = self.db.cursor.fetchall()
            
            # 轉換記錄格式
            formatted_records = []
            for record in records:
                formatted = {
                    'id': record['id'],
                    'serialnumber': record['serialnumber'],
                    'computername': record['computername'],
                    'manufacturer': record['manufacturer'],
                    'model': record['model'],
                    'systemsku': record['systemsku'],
                    'operatingsystem': record['operatingsystem'],
                    'cpu': record['cpu'],
                    'resolution': record['resolution'],
                    'graphicscard': record['graphicscard'],
                    'touchscreen': record['touchscreen'],
                    'ram_gb': float(record['ram_gb'] if record['ram_gb'] is not None else 0),
                    'disks': str(record['disks'])  # 直接使用原始格式
                }
                
                # 添加電池信息（如果有）
                if record['full_charge_capacity'] is not None and record['battery_health'] is not None:
                    formatted['battery'] = {
                        'cycle_count': float(record['cycle_count'] if record['cycle_count'] is not None else 0),
                        'design_capacity': float(record['design_capacity'] if record['design_capacity'] is not None else 0),
                        'full_charge_capacity': float(record['full_charge_capacity']),
                        'health': float(record['battery_health'])
                    }
                
                formatted_records.append(formatted)
            
            return formatted_records

    def update_synced_records(self, record_ids: List[int], new_version: str):
        """更新已同步記錄的狀態
        
        Args:
            record_ids: 要更新的記錄ID列表
            new_version: 新的版本號（字符串格式，例如 '1.0'）
        """
        query = """
            UPDATE system_records
            SET sync_status = 'synced',
                sync_version = %s::numeric,
                last_sync_time = NOW()
            WHERE id = ANY(%s)
        """
        with self.db:
            self.db.cursor.execute(query, (new_version, record_ids))
            self.logger.info(f"Updated {len(record_ids)} records to version {new_version}")

    async def sync_batch(self, records: List[Dict]) -> Dict:
        """同步一批記錄到服務器"""
        try:
            # 生成批次ID
            batch_id = f"SYNC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 發送到服務器
            response = await self.api.send_batch(
                batch_id=batch_id,
                records=records
            )
            
            if response.get('success'):
                # 更新已同步記錄的狀態
                self.update_synced_records(
                    record_ids=[r['id'] for r in records],
                    new_version=response['sync_version']
                )
                return {
                    'success': True,
                    'synced_count': len(records),
                    'new_version': response['sync_version']
                }
            else:
                raise Exception(response.get('error', 'Unknown error'))

        except Exception as e:
            self.logger.error(f"Sync failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def perform_full_sync(self):
        """執行完整同步過程"""
        try:
            total_synced = 0
            while True:
                # 獲取待同步記錄
                records = self.get_records_to_sync()
                if not records:
                    break

                # 同步這批記錄
                result = await self.sync_batch(records)
                if result['success']:
                    total_synced += result['synced_count']
                    self.logger.info(
                        f"Synced {result['synced_count']} records. "
                        f"New version: {result['new_version']}"
                    )
                else:
                    raise Exception(result.get('error', 'Sync failed'))

            return {
                'success': True,
                'total_synced': total_synced,
                'final_stats': self.get_sync_stats().__dict__
            }

        except Exception as e:
            self.logger.error(f"Full sync failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def verify_sync_status(self):
        """驗證同步狀態"""
        try:
            # 獲取本地狀態
            local_stats = self.get_sync_stats()
            
            # 生成批次ID
            batch_id = f"STATUS_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
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

class SyncTask:
    def __init__(self, sync_manager: SystemRecordSyncManager):
        self.sync_manager = sync_manager
        self.logger = logging.getLogger("sync_task")
        self.is_running = False

    async def run(self, interval_minutes: int = 5):
        """運行同步任務"""
        self.is_running = True
        while self.is_running:
            try:
                # 檢查同步狀態
                status = await self.sync_manager.verify_sync_status()
                
                if not status['is_synced']:
                    self.logger.info("Starting sync process...")
                    result = await self.sync_manager.perform_full_sync()
                    
                    if result['success']:
                        self.logger.info(
                            f"Sync completed. Total synced: {result['total_synced']}"
                        )
                    else:
                        self.logger.error(f"Sync failed: {result['error']}")
                
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                self.logger.error(f"Sync cycle failed: {str(e)}")
                await asyncio.sleep(60)  # 錯誤後等待1分鐘

    def stop(self):
        """停止同步任務"""
        self.is_running = False 