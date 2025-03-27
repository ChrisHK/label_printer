#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
添加 battery_json 欄位到 system_records 表。
此欄位用於保存完整的電池數據 JSON 字符串。
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
logger = logging.getLogger('add_battery_json_column')

def add_battery_json_column(db_name='zerodb'):
    """
    在 system_records 表中添加 battery_json 欄位

    Args:
        db_name: 資料庫名稱（默認為 zerodb）
    
    Returns:
        bool: 操作是否成功
    """
    logger.info(f"正在處理資料庫: {db_name}")
    
    try:
        with Database(db_name=db_name) as db:
            # 檢查欄位是否已存在
            db.cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'system_records' 
                AND column_name = 'battery_json'
            """)
            
            column_exists = db.cursor.fetchone() is not None
            
            if column_exists:
                logger.info("battery_json 欄位已存在，無需添加")
                return True
            
            # 添加 battery_json 欄位
            logger.info("添加 battery_json 欄位")
            db.cursor.execute("""
                ALTER TABLE system_records 
                ADD COLUMN battery_json TEXT
            """)
            
            db.connection.commit()
            logger.info("成功添加 battery_json 欄位")
            
            # 更新現有記錄，填充 battery_json 欄位
            logger.info("開始更新現有記錄...")
            
            # 獲取所有具有雙電池格式的記錄
            db.cursor.execute("""
                SELECT id, design_capacity, full_charge_capacity, cycle_count, battery_health 
                FROM system_records 
                WHERE 
                (design_capacity IS NOT NULL AND design_capacity::text LIKE '%,%') OR
                (full_charge_capacity IS NOT NULL AND full_charge_capacity::text LIKE '%,%') OR
                (cycle_count IS NOT NULL AND cycle_count::text LIKE '%,%') OR
                (battery_health IS NOT NULL AND battery_health::text LIKE '%,%')
            """)
            
            dual_battery_records = db.cursor.fetchall()
            logger.info(f"找到 {len(dual_battery_records)} 條雙電池記錄")
            
            import json
            for record in dual_battery_records:
                battery_json = {}
                
                if record['design_capacity'] and ',' in str(record['design_capacity']):
                    battery_json['design_capacity_full'] = str(record['design_capacity'])
                
                if record['full_charge_capacity'] and ',' in str(record['full_charge_capacity']):
                    battery_json['full_charge_capacity_full'] = str(record['full_charge_capacity'])
                
                if record['cycle_count'] and ',' in str(record['cycle_count']):
                    battery_json['cycle_count_full'] = str(record['cycle_count'])
                
                if record['battery_health'] and ',' in str(record['battery_health']):
                    battery_json['battery_health_full'] = str(record['battery_health'])
                
                if battery_json:
                    db.cursor.execute("""
                        UPDATE system_records 
                        SET battery_json = %s 
                        WHERE id = %s
                    """, (json.dumps(battery_json), record['id']))
            
            db.connection.commit()
            logger.info("完成更新現有雙電池記錄")
            
            return True
            
    except Exception as e:
        logger.error(f"添加欄位時發生錯誤: {str(e)}")
        return False

def main():
    """
    主函數：為兩個資料庫添加 battery_json 欄位
    """
    try:
        # 首先處理主資料庫
        success_main = add_battery_json_column('zerodb')
        
        # 然後處理開發資料庫
        success_dev = add_battery_json_column('zerodev')
        
        if success_main and success_dev:
            logger.info("成功為兩個資料庫添加 battery_json 欄位")
            return 0
        else:
            logger.error("為部分或全部資料庫添加欄位失敗")
            return 1
    
    except Exception as e:
        logger.error(f"執行過程中發生錯誤: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 