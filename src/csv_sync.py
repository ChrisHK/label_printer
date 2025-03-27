def insert_product_key(self, record):
    """Insert a product key record into the database"""
    try:
        self.cursor.execute("""
            INSERT INTO product_keys 
            (computername, windowsos_new, productkey_new, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (computername, productkey_new)
            DO UPDATE SET
                windowsos_new = EXCLUDED.windowsos_new,
                created_at = EXCLUDED.created_at,
                is_current = true
            RETURNING id
        """, (
            record['ComputerName'],
            record['WindowsOS'],
            record['ProductKey'],
            record['Timestamp'] if 'Timestamp' in record else None
        ))
        return self.cursor.fetchone()[0]
    except Exception as e:
        self.logger.error(f"Error inserting product key: {str(e)}")
        raise 