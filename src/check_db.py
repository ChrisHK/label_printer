from sqldb import Database

def check_database_structure():
    """Check database structure"""
    with Database() as db:
        try:
            # Check if table exists
            db.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'system_records'
                ) as exists;
            """)
            result = db.cursor.fetchone()
            table_exists = result['exists']
            
            if not table_exists:
                print("\nTable 'system_records' does not exist!")
                return False
            
            # Check table structure
            db.cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'system_records'
                ORDER BY ordinal_position;
            """)
            columns = db.cursor.fetchall()
            
            print("\nTable structure:")
            for column in columns:
                print(f"Column: {column['column_name']}")
                print(f"Type: {column['data_type']}")
                print(f"Nullable: {column['is_nullable']}")
                print("-" * 50)
            
            # Check record count
            db.cursor.execute("SELECT COUNT(*) as count FROM system_records")
            count = db.cursor.fetchone()['count']
            print(f"\nTotal records: {count}")
            
            return True
            
        except Exception as e:
            print(f"Error checking database structure: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def check_system_records():
    """Check system records table data"""
    with Database() as db:
        try:
            # Get records with started_at and sync_status
            db.cursor.execute("""
                SELECT id, serialnumber, started_at, created_at, sync_status
                FROM system_records 
                ORDER BY id DESC
            """)
            records = db.cursor.fetchall()
            
            print("\nSystem records:")
            for record in records:
                print(f"ID: {record['id']}")
                print(f"Serial Number: {record['serialnumber']}")
                print(f"Started At: {record['started_at']}")
                print(f"Created At: {record['created_at']}")
                print(f"Sync Status: {record['sync_status']}")
                print("-" * 50)
            
            return True
            
        except Exception as e:
            print(f"Error checking system records: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    check_database_structure()
    check_system_records() 