import psycopg2
from psycopg2.extras import DictCursor

def get_db_connection(db_name='zerodev', host='192.168.0.10'):
    """Create database connection"""
    try:
        conn = psycopg2.connect(
            host=host,
            dbname=db_name,
            user='zero',
            password='zero'
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def check_table_constraints():
    """Check table constraints"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Query to get table constraints
        cur.execute("""
            SELECT con.conname as constraint_name,
                   pg_get_constraintdef(con.oid) as constraint_definition
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            WHERE rel.relname = 'system_records'
            AND nsp.nspname = 'public';
        """)
        
        constraints = cur.fetchall()
        print("\nTable Constraints:")
        for constraint in constraints:
            print(f"Name: {constraint[0]}")
            print(f"Definition: {constraint[1]}\n")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    check_table_constraints() 