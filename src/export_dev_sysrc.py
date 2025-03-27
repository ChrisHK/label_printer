import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime
import os
import sys

def get_db_connection(db_name='zerodev'):
    """Create database connection"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', '192.168.0.10'),
            dbname=db_name,
            user=os.getenv('DB_USER', 'zero'),
            password=os.getenv('DB_PASSWORD', 'zero')
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def export_system_records(batch_size=1000):
    """Export system_records table data to SQL file"""
    try:
        # Create connection
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Get total count
        cur.execute("SELECT COUNT(*) FROM system_records")
        total_records = cur.fetchone()[0]
        
        # Create export directory if not exists
        export_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sql_exports')
        os.makedirs(export_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'zerodev_system_records_export_{timestamp}.sql'
        filepath = os.path.join(export_dir, filename)
        
        # Write SQL file
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"-- System Records Export from zerodev\n")
            f.write(f"-- Generated at: {datetime.now().isoformat()}\n")
            f.write("-- Compatible with PostgreSQL 10.23\n\n")
            
            # Write transaction start
            f.write("BEGIN;\n\n")
            
            # Write table schema
            f.write("""-- Create table if not exists
CREATE TABLE IF NOT EXISTS system_records (
    id SERIAL PRIMARY KEY,
    serialnumber VARCHAR(100),
    computername VARCHAR(200),
    manufacturer VARCHAR(200),
    model VARCHAR(200),
    systemsku TEXT,
    operatingsystem TEXT,
    cpu TEXT,
    resolution VARCHAR(100),
    graphicscard TEXT,
    touchscreen VARCHAR(100),
    ram_gb NUMERIC,
    disks TEXT,
    design_capacity BIGINT,
    full_charge_capacity BIGINT,
    cycle_count BIGINT,
    battery_health NUMERIC,
    created_at TIMESTAMP,
    is_current BOOLEAN,
    sync_status VARCHAR(20),
    last_sync_time TIMESTAMP,
    sync_version VARCHAR(255),
    started_at TIMESTAMP WITH TIME ZONE
);\n\n""")

            # Add new columns if they don't exist
            f.write("""-- Add new columns if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_records' AND column_name = 'outbound_status') THEN
        ALTER TABLE system_records ADD COLUMN outbound_status VARCHAR(20);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_records' AND column_name = 'disks_gb') THEN
        ALTER TABLE system_records ADD COLUMN disks_gb NUMERIC;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_records' AND column_name = 'last_updated_at') THEN
        ALTER TABLE system_records ADD COLUMN last_updated_at TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_records' AND column_name = 'data_source') THEN
        ALTER TABLE system_records ADD COLUMN data_source VARCHAR(255);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_records' AND column_name = 'validation_status') THEN
        ALTER TABLE system_records ADD COLUMN validation_status VARCHAR(255);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_records' AND column_name = 'validation_message') THEN
        ALTER TABLE system_records ADD COLUMN validation_message TEXT;
    END IF;
END $$;\n\n""")
            
            # Optional cleanup
            f.write("-- Clear existing data and reset sequence\n")
            f.write("TRUNCATE TABLE system_records CASCADE;\n")
            f.write("ALTER SEQUENCE system_records_id_seq RESTART WITH 1;\n\n")
            
            # Export data in batches
            offset = 0
            while offset < total_records:
                cur.execute("""
                    SELECT * FROM system_records 
                    ORDER BY id 
                    LIMIT %s OFFSET %s
                """, (batch_size, offset))
                
                records = cur.fetchall()
                if not records:
                    break
                
                for record in records:
                    # Build INSERT statement
                    columns = record.keys()
                    values = []
                    for value in record.values():
                        if value is None:
                            values.append('NULL')
                        elif isinstance(value, bool):
                            values.append(str(value).lower())
                        elif isinstance(value, (int, float)):
                            values.append(str(value))
                        elif isinstance(value, datetime):
                            values.append(f"'{value.isoformat()}'")
                        else:
                            values.append(f"'{str(value).replace(chr(39), chr(39)+chr(39))}'")
                    
                    sql = f"INSERT INTO system_records ({', '.join(columns)}) VALUES ({', '.join(values)});\n"
                    f.write(sql)
                
                offset += batch_size
                progress = min(100, round(offset * 100 / total_records))
                print(f"Progress: {progress}% ({offset}/{total_records} records)")
            
            # Write transaction end
            f.write("\nCOMMIT;\n")
        
        print(f"\nExport completed successfully!")
        print(f"File saved as: {filepath}")
        
    except Exception as e:
        print(f"Error during export: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    export_system_records()
