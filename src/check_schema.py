import psycopg2
from psycopg2.extras import DictCursor
import os

def get_table_schema():
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', '192.168.0.10'),
            dbname='zerodev',
            user=os.getenv('DB_USER', 'zero'),
            password=os.getenv('DB_PASSWORD', 'zero')
        )
        cur = conn.cursor()
        
        # Get column information
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = 'system_records'
            ORDER BY ordinal_position;
        """)
        
        columns = cur.fetchall()
        print("\nTable structure:")
        print("-" * 50)
        for col in columns:
            print(f"Column: {col[0]}")
            print(f"Type: {col[1]}")
            if col[2]:
                print(f"Length: {col[2]}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    get_table_schema() 