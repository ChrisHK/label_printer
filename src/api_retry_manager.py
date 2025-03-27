import os
import re
import json
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from test_api import APIConnection, prepare_request_data
from sqldb import Database


# 自定義JSON編碼器，處理Decimal類型
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # 將Decimal轉換為float
        # 處理日期類型
        elif isinstance(obj, datetime):
            return obj.isoformat()
        # 讓父類處理其他類型
        return super(DecimalEncoder, self).default(obj)


class APIRetryManager:
    """處理API上傳重試的管理器類"""
    
    def __init__(self, log_dir: str = None):
        """初始化API重試管理器
        
        Args:
            log_dir: 日誌文件目錄，如果為None則使用默認目錄
        """
        # 設置日誌目錄
        if log_dir is None:
            # 使用默認目錄 (項目根目錄下的logs文件夾)
            self.log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        else:
            self.log_dir = log_dir
            
        # 結果保存目錄
        self.results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results")
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
            
        # 設置API重試日誌文件
        self.log_file = os.path.join(os.path.dirname(__file__), "api_retry.log")
        
        # 設置保存結果的文件
        self.results_file = os.path.join(self.results_dir, "api_retry_results.json")
        
        # 設置日誌
        self.setup_logging()
        
        # API連接
        self.api = None
        
    def setup_logging(self):
        """設置日誌配置"""
        self.logger = logging.getLogger("api_retry")
        self.logger.setLevel(logging.INFO)
        
        # 清除現有處理器
        self.logger.handlers.clear()
        
        # 文件處理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 控制台處理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 設置格式
        file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        console_formatter = logging.Formatter('%(message)s')
        
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def initialize_api(self) -> bool:
        """初始化API連接"""
        try:
            self.api = APIConnection(
                base_url="https://erp.zerounique.com",
                username="admin",
                password="admin123"
            )
            result = self.api.login()
            if result:
                self.logger.info("API連接成功")
            else:
                self.logger.error("API登錄失敗")
            return result
        except Exception as e:
            self.logger.error(f"API初始化失敗: {str(e)}")
            return False
    
    def find_failed_uploads(self, days_back: int = 7) -> List[Dict[str, Any]]:
        """從日誌文件中查找失敗的API上傳
        
        Args:
            days_back: 向前查找的天數
            
        Returns:
            List[Dict]: 失敗上傳的列表
        """
        self.logger.info(f"查找近 {days_back} 天內的失敗上傳...")
        
        # 計算開始日期
        start_date = datetime.now() - timedelta(days=days_back)
        
        # 失敗上傳記錄
        failed_uploads = []
        
        # 查找相關日誌文件
        log_files = []
        for file in os.listdir(self.log_dir):
            if file.startswith("sync_") and file.endswith(".log"):
                try:
                    # 從文件名解析日期
                    date_str = file[5:-4]  # 'sync_20250312.log' -> '20250312'
                    file_date = datetime.strptime(date_str, "%Y%m%d")
                    
                    # 如果文件在查找範圍內
                    if file_date >= start_date:
                        log_files.append(os.path.join(self.log_dir, file))
                except:
                    continue
        
        self.logger.info(f"找到 {len(log_files)} 個日誌文件進行分析")
        
        # 分析每個日誌文件
        for log_file in sorted(log_files):
            self.logger.info(f"分析日誌文件: {os.path.basename(log_file)}")
            failed_in_file = self._parse_log_file(log_file)
            if failed_in_file:
                failed_uploads.extend(failed_in_file)
                self.logger.info(f"在此文件中找到 {len(failed_in_file)} 條失敗記錄")
        
        self.logger.info(f"總共找到 {len(failed_uploads)} 條失敗的API上傳")
        return failed_uploads
    
    def _parse_log_file(self, log_file: str) -> List[Dict[str, Any]]:
        """解析單個日誌文件以查找失敗的API上傳
        
        Args:
            log_file: 日誌文件路徑
            
        Returns:
            List[Dict]: 失敗上傳的列表
        """
        failed_uploads = []
        
        # 定義匹配失敗上傳的模式
        api_error_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[ERROR\] API upload failed: (.+)')
        record_insert_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[INFO\] Successfully inserted record with ID: (\d+)')
        serial_number_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[INFO\] Processing record in zerodb: SerialNumber=([^,]+),')
        
        # 一次讀取整個日誌文件
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
                
            # 查找所有行
            lines = log_content.split('\n')
            
            # 處理每一行
            current_record_id = None
            current_serial = None
            
            for i, line in enumerate(lines):
                # 首先檢查是否有新記錄的插入
                insert_match = record_insert_pattern.search(line)
                if insert_match:
                    # 找到記錄ID
                    timestamp, record_id = insert_match.groups()
                    current_record_id = record_id
                    continue
                    
                # 檢查是否匹配序列號
                serial_match = serial_number_pattern.search(line)
                if serial_match:
                    # 找到序列號
                    timestamp, serial = serial_match.groups()
                    current_serial = serial
                    continue
                
                # 檢查是否有API上傳錯誤
                error_match = api_error_pattern.search(line)
                if error_match and current_record_id and current_serial:
                    # 找到錯誤，記錄上一個插入的記錄
                    error_time, error_message = error_match.groups()
                    
                    # 將日誌時間字符串轉換為datetime對象
                    try:
                        error_datetime = datetime.strptime(error_time, "%Y-%m-%d %H:%M:%S,%f")
                    except:
                        error_datetime = datetime.now()
                    
                    # 添加到失敗列表
                    failed_uploads.append({
                        "record_id": int(current_record_id),
                        "serial_number": current_serial,
                        "error_time": error_time,
                        "error_message": error_message,
                        "log_file": os.path.basename(log_file),
                        "resolved": False,
                        "retry_count": 0,
                        "last_retry": None
                    })
                    
                    # 重置當前記錄ID和序列號
                    current_record_id = None
                    current_serial = None
                
        except Exception as e:
            self.logger.error(f"解析日誌文件時出錯: {str(e)}")
            return []
        
        return failed_uploads
    
    def classify_errors(self, failed_uploads: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """將失敗的上傳分類
        
        Args:
            failed_uploads: 失敗上傳的列表
            
        Returns:
            Dict: 按錯誤類型分類的字典
        """
        error_types = {}
        
        for upload in failed_uploads:
            error_msg = upload.get("error_message", "").lower()
            
            # 分類錯誤類型
            if "authentication" in error_msg or "login" in error_msg:
                error_type = "authentication"
            elif "timeout" in error_msg:
                error_type = "timeout"
            elif "network" in error_msg or "connection" in error_msg:
                error_type = "network"
            elif "server" in error_msg:
                error_type = "server"
            else:
                error_type = "other"
            
            # 添加到相應的類別
            if error_type not in error_types:
                error_types[error_type] = []
            
            error_types[error_type].append(upload)
        
        # 輸出分類結果
        for error_type, uploads in error_types.items():
            self.logger.info(f"{error_type} 錯誤: {len(uploads)} 條")
        
        return error_types
    
    def load_results(self) -> List[Dict[str, Any]]:
        """從文件加載之前的重試結果"""
        if os.path.exists(self.results_file):
            try:
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"讀取結果文件時出錯: {str(e)}")
                return []
        return []
    
    def save_results(self, results: List[Dict[str, Any]]):
        """保存重試結果到文件"""
        try:
            with open(self.results_file, 'w', encoding='utf-8') as f:
                # 使用自定義編碼器處理Decimal類型
                json.dump(results, f, ensure_ascii=False, indent=2, cls=DecimalEncoder)
            self.logger.info(f"結果已保存到 {self.results_file}")
        except Exception as e:
            self.logger.error(f"保存結果時出錯: {str(e)}")
    
    def mark_as_resolved(self, record_id: int) -> bool:
        """將記錄標記為已解決
        
        Args:
            record_id: 記錄ID
            
        Returns:
            bool: 操作是否成功
        """
        results = self.load_results()
        
        for result in results:
            if result.get("record_id") == record_id:
                result["resolved"] = True
                result["resolution_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                result["resolution_method"] = "manual"
                
                self.save_results(results)
                self.logger.info(f"記錄 {record_id} 已標記為已解決")
                return True
                
        self.logger.error(f"未找到記錄 {record_id}")
        return False
    
    def get_record_data(self, record_id: int) -> Optional[Dict[str, Any]]:
        """從數據庫獲取記錄數據
        
        Args:
            record_id: 記錄ID
            
        Returns:
            Optional[Dict]: 記錄數據或None
        """
        try:
            with Database() as db:
                db.cursor.execute("""
                    SELECT 
                        serialnumber, computername, manufacturer, model,
                        systemsku, ram_gb, disks, created_at, operatingsystem,
                        cpu, resolution, graphicscard, touchscreen,
                        design_capacity, full_charge_capacity, cycle_count,
                        battery_health
                    FROM system_records
                    WHERE id = %s
                """, (record_id,))
                
                record = db.cursor.fetchone()
                
                if record:
                    # 將記錄轉換為字典，處理Decimal和datetime類型
                    record_dict = {}
                    for key, value in dict(record).items():
                        if isinstance(value, Decimal):
                            record_dict[key] = float(value)
                        elif isinstance(value, datetime):
                            # 將datetime轉換為ISO格式字符串
                            record_dict[key] = value.isoformat()
                        else:
                            record_dict[key] = value
                    return record_dict
                else:
                    self.logger.error(f"未找到記錄ID: {record_id}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"獲取記錄數據時出錯: {str(e)}")
            return None
    
    def retry_upload(self, record_id: int) -> Tuple[bool, str]:
        """重試上傳特定記錄
        
        Args:
            record_id: 記錄ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        self.logger.info(f"準備重試上傳記錄ID: {record_id}")
        
        # 獲取記錄數據
        record_data = self.get_record_data(record_id)
        if not record_data:
            return False, "找不到記錄數據"
        
        # 初始化API連接
        if not hasattr(self, 'api') or self.api is None:
            if not self.initialize_api():
                return False, "API連接初始化失敗"
        
        # 準備API請求數據
        try:
            # 確保數據格式正確
            if not isinstance(record_data, dict):
                return False, "記錄數據格式錯誤"
            
            # 檢查必要字段
            required_fields = ["serialnumber", "manufacturer", "model", "ram_gb", "disks"]
            missing_fields = [field for field in required_fields if field not in record_data]
            if missing_fields:
                return False, f"缺少必要字段: {', '.join(missing_fields)}"
            
            # 準備請求數據
            request_data = prepare_request_data([record_data])
            
            # 發送數據到API
            response = self.api.send_data(request_data)
            
            if response.get('error'):
                error_msg = response.get('error')
                self.logger.error(f"API上傳失敗: {error_msg}")
                return False, f"API上傳失敗: {error_msg}"
            else:
                self.logger.info(f"成功上傳記錄ID: {record_id}")
                return True, "上傳成功"
                
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"重試上傳時出錯: {error_msg}")
            return False, f"上傳過程中出錯: {error_msg}"
    
    def retry_all_pending(self, max_retries: int = 3) -> Dict[str, int]:
        """重試所有待處理的失敗上傳
        
        Args:
            max_retries: 每條記錄的最大重試次數
            
        Returns:
            Dict: 統計結果
        """
        # 加載當前結果
        results = self.load_results()
        
        # 查找待處理的記錄
        pending = [r for r in results if not r.get("resolved", False) and r.get("retry_count", 0) < max_retries]
        
        self.logger.info(f"找到 {len(pending)} 條待處理的失敗上傳")
        
        # 統計
        stats = {
            "total": len(pending),
            "success": 0,
            "failed": 0,
            "skipped": 0
        }
        
        # 重試每條記錄
        for record in pending:
            record_id = record.get("record_id")
            
            # 檢查重試次數
            retry_count = record.get("retry_count", 0)
            if retry_count >= max_retries:
                self.logger.info(f"記錄 {record_id} 已達到最大重試次數，跳過")
                stats["skipped"] += 1
                continue
            
            # 執行重試
            success, message = self.retry_upload(record_id)
            
            # 更新記錄
            record["retry_count"] = retry_count + 1
            record["last_retry"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record["last_retry_result"] = message
            
            if success:
                record["resolved"] = True
                record["resolution_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record["resolution_method"] = "retry"
                stats["success"] += 1
                self.logger.info(f"記錄 {record_id} 重試成功")
            else:
                stats["failed"] += 1
                self.logger.info(f"記錄 {record_id} 重試失敗: {message}")
            
            # 每次重試後保存結果
            self.save_results(results)
            
            # 休息一下，避免請求過於頻繁
            time.sleep(2)
        
        self.logger.info(f"重試完成: 總計 {stats['total']}, 成功 {stats['success']}, 失敗 {stats['failed']}, 跳過 {stats['skipped']}")
        return stats
    
    def run(self, days_back: int = 7):
        """運行API重試流程
        
        Args:
            days_back: 向前查找的天數
        """
        self.logger.info("===== 開始API上傳重試流程 =====")
        
        # 1. 從日誌中查找失敗的上傳
        failed_uploads = self.find_failed_uploads(days_back)
        
        if not failed_uploads:
            self.logger.info("沒有找到失敗的API上傳記錄")
            return
        
        # 2. 對錯誤進行分類
        error_types = self.classify_errors(failed_uploads)
        
        # 3. 加載之前的結果
        previous_results = self.load_results()
        
        # 4. 合併結果
        merged_results = previous_results.copy()
        new_count = 0
        
        # 查找新的失敗上傳
        existing_ids = {r.get("record_id") for r in previous_results}
        for upload in failed_uploads:
            if upload.get("record_id") not in existing_ids:
                # 確保所有datetime對象都被轉換為字符串
                if "error_time" in upload:
                    upload["error_time"] = upload["error_time"].strftime("%Y-%m-%d %H:%M:%S,%f")
                merged_results.append(upload)
                new_count += 1
        
        self.logger.info(f"找到 {new_count} 條新的失敗上傳")
        
        # 5. 保存合併後的結果
        self.save_results(merged_results)
        
        # 6. 重試所有待處理的失敗上傳
        stats = self.retry_all_pending()
        
        self.logger.info("===== API上傳重試流程完成 =====")
    

if __name__ == "__main__":
    # 創建API重試管理器
    retry_manager = APIRetryManager()
    
    # 運行重試流程
    retry_manager.run() 