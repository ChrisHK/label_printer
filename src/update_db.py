from sqldb import Database

def update_database_schema():
    """更新資料庫結構"""
    with Database() as db:
        try:
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
            print("Database schema updated successfully")
            return True
            
        except Exception as e:
            print(f"Error updating database schema: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    update_database_schema() 