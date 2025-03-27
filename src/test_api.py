import requests
import json
import hashlib
import time
import random
import string
from datetime import datetime, timezone
from typing import Dict, Any
import urllib3
import warnings
import collections
import functools

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def generate_nonce(length=8):
    """Generate a random nonce string"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def sort_dict(d):
    if isinstance(d, dict):
        return {k: sort_dict(v) for k, v in sorted(d.items())}
    elif isinstance(d, list):
        return [sort_dict(x) for x in d]
    return d

def validate_required_fields(item):
    # Validate required fields
    required_fields = [
        "serialnumber",
        "manufacturer",
        "model",
        "ram_gb",
        "disks"
    ]

    missing_fields = [field for field in required_fields if field not in item]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

def normalize_item(item):
    """只保留並規範化 serialnumber
    
    Args:
        item: 單個項目字典
        
    Returns:
        dict: 只包含 serialnumber 的字典
    """
    return {
        "serialnumber": str(item.get("serialnumber", ""))
    }

def calculate_checksum(items):
    """計算校驗和（只使用 serialnumber）
    
    Args:
        items: 項目列表
        
    Returns:
        str: SHA-256 校驗和
    """
    if not isinstance(items, list):
        raise ValueError("Input must be an array")

    print("\nDebug: Original items:")
    print(json.dumps(items, indent=2))

    # 格式化並排序項目
    normalized_items = [normalize_item(item) for item in items]
    sorted_items = sorted(normalized_items, key=lambda x: x["serialnumber"])
    
    print("\nDebug: Normalized and sorted items:")
    print(json.dumps(sorted_items, indent=2))

    # 轉換為 JSON 字符串（無空格）
    json_string = json.dumps(sorted_items, separators=(',', ':'))
    
    print("\nDebug: Final JSON string for checksum:")
    print(json_string)
    print("\nDebug: JSON string length:", len(json_string))

    # 計算 SHA-256
    checksum = hashlib.sha256(json_string.encode('utf-8')).hexdigest()
    
    print("\nDebug: Calculated checksum:", checksum)
    
    return checksum

def prepare_request_data(items):
    """準備請求數據
    
    Args:
        items: 項目列表
        
    Returns:
        dict: 格式化的請求數據
    """
    # 計算校驗和
    checksum = calculate_checksum(items)
    
    # 準備請求數據
    request_data = {
        'source': 'python_sync',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'batch_id': f'SYNC_{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'items': items,
        'metadata': {
            'total_items': len(items),
            'version': '1.0',
            'checksum': checksum
        }
    }
    
    return request_data

def retry_with_backoff(func, max_retries=2, initial_delay=10):
    """使用退避策略重試函數
    
    Args:
        func: 要重試的函數
        max_retries: 最大重試次數
        initial_delay: 初始延遲時間（秒）
        
    Returns:
        tuple: (success, result)
    """
    for attempt in range(max_retries):
        try:
            # 在每次嘗試前等待
            if attempt > 0:
                delay = initial_delay * (2 ** attempt)  # 指數退避
                print(f"\nAttempt {attempt + 1} of {max_retries}, waiting {delay} seconds...")
                time.sleep(delay)
            
            result = func()
            return True, result
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if "transaction is aborted" in str(e):
                print("Transaction abort detected, waiting longer...")
                time.sleep(10)  # 事務錯誤時等待更長時間
            if attempt == max_retries - 1:
                return False, {'error': str(e)}
    
    return False, {'error': 'Max retries exceeded'}

class APIConnection:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
        self.session = requests.Session()
        # 禁用 SSL 警告
        requests.packages.urllib3.disable_warnings()
        self.session.verify = False
        # 設置超時
        self.timeout = (5, 10)  # (連接超時, 讀取超時)
    
    def login(self) -> bool:
        """登入並獲取 token"""
        try:
            print(f"\nAttempting to login to {self.base_url}...")
            response = self.session.post(
                f"{self.base_url}/api/users/login",  # 修正登入 URL
                json={
                    "username": self.username,
                    "password": self.password
                },
                timeout=self.timeout
            )
            
            if response.ok:
                data = response.json()
                self.token = data.get('token')
                self.session.headers.update({
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json'
                })
                print("Login successful")
                return True
                
            print(f"Login failed with status {response.status_code}")
            if response.status_code == 404:
                print("Login endpoint not found. Please check the API URL and port.")
            return False
            
        except requests.exceptions.ConnectTimeout:
            print(f"Connection to {self.base_url} timed out")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error: {str(e)}")
            print("Please check if the server is running and the port is correct.")
            return False
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False
    
    def validate_token(self) -> bool:
        """驗證 token"""
        try:
            print("\nValidating token...")
            response = self.session.get(f"{self.base_url}/api/users/me")
            if response.ok:
                print("Token validation response:")
                print(json.dumps(response.json(), indent=2))
                return True
            return False
        except Exception as e:
            print(f"Token validation error: {str(e)}")
            return False
    
    def refresh_token_if_needed(self) -> bool:
        """如果需要則刷新 token"""
        if not self.validate_token():
            print("\nToken invalid, refreshing...")
            return self.login()
        return True
    
    def check_cleaning_status(self) -> bool:
        """檢查清理狀態"""
        try:
            print("\nChecking cleaning status...")
            response = self.session.get(f"{self.base_url}/api/data-process/status")
            if response.ok:
                status = response.json()
                print(f"Current status: {json.dumps(status, indent=2)}")
                if status.get('is_cleaning'):
                    print("System is currently cleaning logs")
                    return False
                return True
            print(f"Failed to check status: {response.status_code}")
            return False
        except Exception as e:
            print(f"Error checking status: {str(e)}")
            return False

    def wait_for_cleaning_complete(self, timeout=60, check_interval=5) -> bool:
        """等待清理完成
        
        Args:
            timeout: 最大等待時間（秒）
            check_interval: 檢查間隔（秒）
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.check_cleaning_status():
                return True
            print(f"Waiting {check_interval} seconds before next check...")
            time.sleep(check_interval)
        return False

    def clean_logs(self) -> bool:
        """清理處理日誌"""
        try:
            print("\nCleaning up processing logs...")
            response = self.session.delete(f"{self.base_url}/api/data-process/logs")
            if response.ok:
                print("Logs cleaned successfully")
                return True
            
            # 如果返回 500，等待後重試
            if response.status_code == 500:
                print("Server busy, waiting 10 seconds before retry...")
                time.sleep(10)
                # 再試一次
                print("Retrying clean logs...")
                response = self.session.delete(f"{self.base_url}/api/data-process/logs")
                if response.ok:
                    print("Logs cleaned successfully on retry")
                    return True
            
            print(f"Failed to clean logs: {response.status_code}")
            return False
        except Exception as e:
            print(f"Error cleaning logs: {str(e)}")
            return False
    
    def check_logs(self) -> Dict:
        """檢查處理日誌"""
        try:
            print("\nChecking processing logs...")
            response = self.session.get(f"{self.base_url}/api/data-process/logs")
            if response.ok:
                logs = response.json()
                print("Current logs:")
                print(json.dumps(logs, indent=2))
                return logs
            print(f"Failed to get logs: {response.status_code}")
            return {}
        except Exception as e:
            print(f"Error checking logs: {str(e)}")
            return {}
    
    def send_data(self, data: Dict[str, Any]) -> Dict:
        """發送數據到 API"""
        def _send():
            if not self.refresh_token_if_needed():
                raise Exception("Authentication failed")
            
            try:
                # 檢查服務器狀態
                print("\nChecking server status...")
                status_response = self.session.get(f"{self.base_url}/api/health")
                if not status_response.ok:
                    raise Exception("Server is not healthy")
                
                # 發送請求並啟用流式響應
                print("\nSending request with body:")
                print(json.dumps(data, indent=2))
                
                response = self.session.post(
                    f"{self.base_url}/api/data-process/inventory",
                    json=data,
                    timeout=300,  # 5 分鐘超時
                    stream=True   # 啟用流式響應
                )
                
                # 處理流式響應
                for line in response.iter_lines():
                    if line:
                        try:
                            progress_data = json.loads(line.decode('utf-8'))
                            print(f"Processing progress: {progress_data}")
                            
                            # 如果處理完成，返回結果
                            if progress_data.get('status') == 'completed':
                                return progress_data
                                
                        except json.JSONDecodeError:
                            print(f"Invalid JSON in response: {line}")
                
                # 如果沒有收到完成信號，拋出異常
                raise Exception("Processing incomplete")
                    
            except Exception as e:
                print(f"Error during data send: {str(e)}")
                raise e
        
        # 使用退避重試
        success, result = retry_with_backoff(_send, max_retries=2, initial_delay=10)
        return result

class ChecksumCalculator:
    @staticmethod
    def parse_disk_string(disk_str: str) -> dict:
        """Parse disk string into disk object
        
        Args:
            disk_str: Disk string in format "type:size:model"
            
        Returns:
            dict: Disk object
        """
        try:
            type_, size, model = disk_str.split(':')
            return {
                "type": type_,
                "size": size,
                "model": model
            }
        except:
            return {
                "type": "",
                "size": "",
                "model": ""
            }

    @staticmethod
    def normalize_items(items):
        """Normalize items to ensure consistent format
        
        Args:
            items: List of item dictionaries
            
        Returns:
            list: List of normalized items
        """
        normalized_items = []
        for item in items:
            # 解析磁盤字符串為數組
            disks_str = str(item.get('disks', ''))
            disks = []
            if disks_str:
                disk_parts = disks_str.split(',')
                for disk_str in disk_parts:
                    if disk_str.strip():
                        try:
                            type_, size, model = disk_str.strip().split(':')
                            # 解析大小為數字
                            size_num = float(size.replace('TB', '000').replace('GB', ''))
                            disks.append({
                                'size_gb': size_num
                            })
                        except:
                            # 如果解析失敗，添加一個空的磁盤記錄
                            disks.append({
                                'size_gb': 0
                            })
            
            # 確保字段順序與數據庫列名完全匹配，並使用正確的數據類型
            normalized_item = {
                'id': None,  # 由數據庫自動生成
                'serialnumber': str(item.get('serialnumber', ''))[:100],  # varchar(100)
                'computername': str(item.get('computername', ''))[:200],  # varchar(200)
                'manufacturer': str(item.get('manufacturer', ''))[:200],  # varchar(200)
                'model': str(item.get('model', ''))[:200],  # varchar(200)
                'systemsku': str(item.get('systemsku', '')),  # text
                'operatingsystem': str(item.get('operatingsystem', '')),  # text
                'cpu': str(item.get('cpu', '')),  # text
                'resolution': str(item.get('resolution', ''))[:100],  # varchar(100)
                'graphicscard': str(item.get('graphicscard', '')),  # text
                'touchscreen': str(item.get('touchscreen', 'false'))[:100],  # varchar(100)
                'ram_gb': float(item.get('ram_gb', 0)),  # numeric
                'disks': str(item.get('disks', '')),  # text
                'design_capacity': int(item.get('design_capacity', 0)),  # bigint
                'full_charge_capacity': int(item.get('full_charge_capacity', 0)),  # bigint
                'cycle_count': int(item.get('cycle_count', 0)),  # bigint
                'battery_health': float(item.get('battery_health', 0)),  # numeric
                'created_at': datetime.now(timezone.utc).isoformat(),  # timestamp
                'is_current': bool(item.get('is_current', True)),  # boolean
                'outbound_status': str(item.get('outbound_status', ''))[:20],  # varchar(20)
                'sync_status': str(item.get('sync_status', ''))[:20],  # varchar(20)
                'last_sync_time': datetime.now(timezone.utc).isoformat() if item.get('last_sync_time') else None,  # timestamp
                'sync_version': str(item.get('sync_version', '1.0'))[:255],  # varchar(255)
                'started_at': datetime.now(timezone.utc).isoformat(),  # timestamp with time zone
                'disks_gb': float(item.get('disks_gb', 0)),  # numeric
                'last_updated_at': datetime.now(timezone.utc).isoformat(),  # timestamp with time zone
                'data_source': str(item.get('data_source', 'api'))[:255],  # varchar(255)
                'validation_status': str(item.get('validation_status', 'pending'))[:255],  # varchar(255)
                'validation_message': str(item.get('validation_message', ''))  # text
            }
            normalized_items.append(normalized_item)
        return normalized_items

def main():
    # 初始化連接
    api = APIConnection(
        base_url="https://erp.zerounique.com",
        #base_url="http://192.168.0.10:3000",
        username="admin",
        password="admin123"
    )
    
    # 登入
    if not api.login():
        print("Failed to login")
        return
    
    # 準備測試數據
    items = [{
        "serialnumber": "PC10ADA1",
        "computername": "DESKTOP-BVOJOGI",
        "manufacturer": "LENOVO",
        "model": "20L8S21300",
        "systemsku": "LENOVO_MT_20L8_BU_Think_FM_ThinkPad T480s",
        "operatingsystem": "Microsoft Windows 11 Pro 10.0.26100",
        "cpu": "Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz (4C/8T)",
        "resolution": "1920x1080",
        "graphicscard": "Intel(R) UHD Graphics 620 [1920x1080]",
        "touchscreen": "Not Detected",
        "ram_gb": 16.0,
        "disks": "256GB",
        "design_capacity": 57000.0,
        "full_charge_capacity": 43290.0,
        "cycle_count": 375.0,
        "battery_health": 75.95,
        "created_at": "2025-02-25T10:42:00",
        "is_current": True,
        "outbound_status": "pending",
        "sync_status": "pending",
        "data_source": "csv_sync",
        "validation_status": "pending"
    }]
    
    # 準備請求數據
    request_data = prepare_request_data(items)
    
    # 發送數據
    result = api.send_data(request_data)
    print(f"\nAPI Response: {json.dumps(result, indent=2)}")
    
    if result.get('success') and result.get('batchId'):
        max_retries = 6  # 最多重試 6 次
        retry_interval = 10  # 每次等待 10 秒
        
        for attempt in range(max_retries):
            print(f"\nAttempt {attempt + 1} of {max_retries}")
            print(f"Waiting {retry_interval} seconds for processing...")
            time.sleep(retry_interval)
            
            # 檢查處理狀態
            try:
                # 使用 check_logs 方法
                logs = api.check_logs()
                
                if logs:
                    # 找到對應的批次記錄
                    batch_log = next(
                        (log for log in logs.get('logs', []) 
                         if log.get('batch_id') == result['batchId']), 
                        None
                    )
                    
                    if batch_log:
                        print("\nProcessing Status:")
                        print(json.dumps(batch_log, indent=2))
                        
                        # 檢查同步狀態
                        if batch_log.get('status') == 'completed':
                            sync_response = api.session.post(
                                f"{api.base_url}/api/data-process/sync-status",
                                json={"serialnumbers": ["PC10ADA1"]},
                                timeout=api.timeout
                            )
                            
                            if sync_response.ok:
                                sync_data = sync_response.json()
                                print("\nSync Status:")
                                print(json.dumps(sync_data, indent=2))
                                break  # 成功獲取同步狀態後退出
                            else:
                                print(f"\nFailed to get sync status: {sync_response.status_code}")
                        else:
                            print(f"\nProcessing not completed yet, status: {batch_log.get('status', 'unknown')}")
                    else:
                        print(f"\nNo log found for batch ID: {result['batchId']}")
                else:
                    print("\nNo processing logs available")
                    
            except Exception as e:
                print(f"\nError checking status: {str(e)}")
            
            # 如果是最後一次嘗試，顯示警告
            if attempt == max_retries - 1:
                print("\nWarning: Maximum retries reached, processing might still be ongoing")

if __name__ == "__main__":
    main() 