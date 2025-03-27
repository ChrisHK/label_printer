import psycopg
from psycopg.rows import dict_row
import os
from typing import Optional, Any, Dict, List
from datetime import datetime

class Database:
    def __init__(self, db_name: str = 'zerodb'):
        """Initialize database connection parameters"""
        self.connection = None
        self.cursor = None
        # 新增: 支援多數據庫配置
        self.db_configs = {
            'zerodb': {
                'host': os.getenv('DB_HOST', '192.168.0.10'),
                'dbname': 'zerodb',
                'user': os.getenv('DB_USER', 'zero'),
                'password': os.getenv('DB_PASSWORD', 'zero')
            },
            'zerodev': {  # 新數據庫配置
                'host': os.getenv('DB_HOST', '192.168.0.10'),
                'dbname': 'zerodev',
                'user': os.getenv('DB_USER', 'zero'),
                'password': os.getenv('DB_PASSWORD', 'zero')
            }
        }
        self.config = self.db_configs[db_name]

    def connect(self) -> None:
        """Establish connection to the PostgreSQL database"""
        try:
            # Create connection string
            conn_string = " ".join(f"{key}={value}" for key, value in self.config.items())
            self.connection = psycopg.connect(conn_string)
            self.cursor = self.connection.cursor(row_factory=dict_row)
        except Exception as e:
            raise Exception(f"Error connecting to PostgreSQL: {str(e)}")

    def disconnect(self) -> None:
        """Close database connection and cursor"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> None:
        """
        Execute a SQL query
        
        Args:
            query: SQL query string
            params: Query parameters (optional)
        """
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise Exception(f"Query execution failed: {str(e)}")

    def get_record_by_sn(self, serial_number):
        """Get a record by serial number"""
        try:
            self.cursor.execute("""
                SELECT 
                    serialnumber as "SerialNumber",
                    manufacturer as "Manufacturer",
                    model as "Model",
                    systemsku as "SystemSKU",
                    operatingsystem as "OperatingSystem",
                    cpu as "CPU",
                    graphicscard as "GraphicsCard",
                    ram_gb as "RAM_GB",
                    disks as "Disks",
                    full_charge_capacity as "Full_Charge_Capacity",
                    battery_health as "Battery_Health",
                    touchscreen as "TouchScreen"
                FROM system_records 
                WHERE serialnumber = %s 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (serial_number,))
            record = self.cursor.fetchone()
            if record:
                # Convert Decimal types to float for JSON serialization
                record_dict = dict(record)
                for key in ['Full_Charge_Capacity', 'Battery_Health']:
                    if key in record_dict and record_dict[key] is not None:
                        record_dict[key] = float(record_dict[key])
                return record_dict
            return None
        except Exception as e:
            print(f"Error getting record by SN: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def get_updated_records(self, last_sync_time: Optional[datetime] = None) -> List[Dict]:
        """獲取上次同步後更新的記錄"""
        try:
            query = """
                SELECT 
                    serialnumber,
                    manufacturer,
                    model,
                    ram_gb,
                    disks,
                    full_charge_capacity,
                    battery_health,
                    updated_at
                FROM system_records 
                WHERE updated_at > %s
                ORDER BY updated_at DESC
            """
            
            self.cursor.execute(query, (last_sync_time or datetime.min,))
            records = self.cursor.fetchall()
            
            # Convert Decimal types to float for JSON serialization
            for record in records:
                for key in ['full_charge_capacity', 'battery_health']:
                    if key in record and record[key] is not None:
                        record[key] = float(record[key])
            
            return records
        except Exception as e:
            print(f"Error getting updated records: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
