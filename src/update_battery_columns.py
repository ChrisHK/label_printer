#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
執行 SQL 檔案來修改系統記錄表中的電池欄位結構。
將電池相關欄位從數值型態改為文字型態，以支持雙電池格式的數據。
"""

import os
import sys
import logging
from sqldb import Database

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('update_battery_columns')

def execute_sql_file(db_name):
    """
    在指定的資料庫中執行 SQL 檔案
    
    Args:
        db_name: 資料庫名稱
    
    Returns:
        bool: 操作是否成功
    """
    logger.info(f"正在處理資料庫: {db_name}")
    
    # SQL 腳本內容 - 直接在代碼中定義，避免讀取文件
    sql_script = """
    -- 將 design_capacity 從 BIGINT 改為 TEXT
    ALTER TABLE system_records ALTER COLUMN design_capacity TYPE TEXT;
    
    -- 將 full_charge_capacity 從 BIGINT 改為 TEXT
    ALTER TABLE system_records ALTER COLUMN full_charge_capacity TYPE TEXT;
    
    -- 將 cycle_count 從 BIGINT 改為 TEXT
    ALTER TABLE system_records ALTER COLUMN cycle_count TYPE TEXT;
    
    -- 將 battery_health 從 DOUBLE PRECISION 改為 TEXT
    ALTER TABLE system_records ALTER COLUMN battery_health TYPE TEXT;
    """
    
    try:
        with Database(db_name=db_name) as db:
            logger.info(f"正在執行 SQL 腳本...")
            
            # 分別執行每條 SQL 命令
            for command in sql_script.split(';'):
                if command.strip():
                    logger.info(f"執行: {command.strip()}")
                    db.cursor.execute(command)
            
            # 提交更改
            db.connection.commit()
            logger.info(f"成功更新 {db_name} 資料庫中的電池欄位結構")
            return True
            
    except Exception as e:
        logger.error(f"執行 SQL 時發生錯誤: {str(e)}")
        return False

def main():
    """
    主函數：為兩個資料庫更新電池欄位結構
    """
    try:
        # 首先處理主資料庫
        success_main = execute_sql_file('zerodb')
        
        # 然後處理開發資料庫
        success_dev = execute_sql_file('zerodev')
        
        if success_main and success_dev:
            logger.info("成功更新兩個資料庫的電池欄位結構")
            return 0
        else:
            if not success_main:
                logger.error("更新 zerodb 失敗")
            if not success_dev:
                logger.error("更新 zerodev 失敗")
            return 1
    
    except Exception as e:
        logger.error(f"執行過程中發生錯誤: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 