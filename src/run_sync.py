import asyncio
import logging
import os
import sys

# 添加 src 目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqldb import Database
from inventory_sync.sync_manager import InventorySync
from sync_manager import SystemRecordSyncManager, SyncTask

async def update_database_schema(db: Database):
    """更新數據庫結構以支持同步功能"""
    try:
        with db:
            # 添加同步相關欄位
            query = """
                ALTER TABLE system_records 
                    ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending',
                    ADD COLUMN IF NOT EXISTS last_sync_time TIMESTAMP,
                    ADD COLUMN IF NOT EXISTS sync_version NUMERIC DEFAULT 1.0,
                    ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
            """
            db.cursor.execute(query)
            
            # 創建索引
            index_queries = [
                """
                CREATE INDEX IF NOT EXISTS idx_system_records_sync_status 
                ON system_records(sync_status);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_system_records_sync_version 
                ON system_records(sync_version);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_system_records_last_sync_time 
                ON system_records(last_sync_time);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_system_records_started_at 
                ON system_records(started_at);
                """
            ]
            
            for query in index_queries:
                db.cursor.execute(query)
            
            db.connection.commit()
            
            logging.info("Database schema updated successfully")
            return True
    except Exception as e:
        logging.error(f"Error updating database schema: {str(e)}")
        return False

async def main():
    # 設置日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("sync_main")

    try:
        # 初始化數據庫連接
        logger.info("Initializing database connection...")
        db = Database()
        
        # 更新數據庫結構
        logger.info("Updating database schema...")
        if not await update_database_schema(db):
            logger.error("Failed to update database schema")
            return

        # 初始化 API 連接
        logger.info("Initializing API connection...")
        api = InventorySync(env="prod")
        
        # 嘗試登錄
        logger.info("Attempting to login to API...")
        if not await api.login("admin", "admin123"):
            logger.error("Failed to login to API")
            return
        logger.info("Successfully logged in to API")

        # 創建同步管理器
        logger.info("Creating sync manager...")
        sync_manager = SystemRecordSyncManager(db, api)
        
        # 創建並運行同步任務
        logger.info("Creating sync task...")
        sync_task = SyncTask(sync_manager)
        
        logger.info("Starting sync task...")
        await sync_task.run()

    except KeyboardInterrupt:
        logger.info("Stopping sync task...")
        sync_task.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 