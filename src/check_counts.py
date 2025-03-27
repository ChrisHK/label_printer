from sqldb import Database

def check_counts():
    """檢查兩個數據庫的記錄數量"""
    # 檢查主數據庫
    with Database() as db:
        db.cursor.execute("SELECT COUNT(*) as count FROM system_records")
        prod_system_count = db.cursor.fetchone()['count']
        
        db.cursor.execute("SELECT COUNT(*) as count FROM product_keys")
        prod_product_count = db.cursor.fetchone()['count']
        
        print("\n主數據庫 (zerodb):")
        print(f"System Records: {prod_system_count}")
        print(f"Product Keys: {prod_product_count}")
    
    # 檢查開發數據庫
    with Database(db_name='zerodev') as db:
        db.cursor.execute("SELECT COUNT(*) as count FROM system_records")
        dev_system_count = db.cursor.fetchone()['count']
        
        db.cursor.execute("SELECT COUNT(*) as count FROM product_keys")
        dev_product_count = db.cursor.fetchone()['count']
        
        print("\n開發數據庫 (zerodev):")
        print(f"System Records: {dev_system_count}")
        print(f"Product Keys: {dev_product_count}")
        
        # 檢查是否一致
        if (dev_system_count == prod_system_count and 
            dev_product_count == prod_product_count):
            print("\n兩個數據庫的記錄數量一致！")
        else:
            print("\n警告：數據庫記錄數量不一致！")

if __name__ == "__main__":
    check_counts() 