import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

class SyncLogger:
    def __init__(self, log_dir: str = "logs"):
        """初始化日誌系統"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger("inventory_sync")
        self.logger.setLevel(logging.INFO)
        
        # 如果已經有處理器，不重複添加
        if not self.logger.handlers:
            # 文件處理器 - 按日期分割
            log_file = self.log_dir / f"inventory_sync_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file)
            
            # 控制台處理器
            console_handler = logging.StreamHandler()
            
            # 格式化
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def info(self, message: str):
        """記錄信息級別的日誌"""
        self.logger.info(message)
    
    def error(self, message: str, exc_info: Optional[Exception] = None):
        """記錄錯誤級別的日誌"""
        if exc_info:
            self.logger.error(message, exc_info=True)
        else:
            self.logger.error(message)
    
    def debug(self, message: str):
        """記錄調試級別的日誌"""
        self.logger.debug(message)
    
    def warning(self, message: str):
        """記錄警告級別的日誌"""
        self.logger.warning(message)
    
    def log_sync_start(self, batch_id: str):
        """記錄同步開始"""
        self.info(f"Starting sync batch: {batch_id}")
    
    def log_sync_complete(self, batch_id: str, stats: dict):
        """記錄同步完成"""
        self.info(
            f"Completed sync batch: {batch_id}\n"
            f"Total records: {stats['total']}\n"
            f"Successful: {stats['success']}\n"
            f"Failed: {stats['failed']}"
        )
    
    def log_api_response(self, batch_id: str, status: int, response: dict):
        """記錄API響應"""
        if 200 <= status < 300:
            self.info(f"API success for batch {batch_id}: {response}")
        else:
            self.error(f"API error for batch {batch_id}: Status {status}, Response: {response}") 