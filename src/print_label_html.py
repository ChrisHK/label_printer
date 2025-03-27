import pandas as pd
import os
import time
import tempfile
import win32print
import subprocess
from jinja2 import Template
import re
import webbrowser
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
import csv
from sqldb import Database
from flask import Blueprint, request, jsonify
from flask_cors import CORS
from flask_basicauth import BasicAuth
import json

# Create Blueprint instead of app
app = Blueprint('label', __name__)
CORS(app)  # 允許跨域請求

# Basic authentication configuration
basic_auth = BasicAuth()

def init_basic_auth(flask_app):
    """Initialize basic auth with the Flask app"""
    flask_app.config['BASIC_AUTH_USERNAME'] = 'share'
    flask_app.config['BASIC_AUTH_PASSWORD'] = 'share'
    basic_auth.init_app(flask_app)

class LabelPrinterHTML:
    def __init__(self):
        # 標籤尺寸 (102mm x 76mm)
        self.label_width = 102
        self.label_height = 76
        # 確保 log_file 在類初始化時就被定義
        self.log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "print_log.txt")
        
    def create_html(self, data):
        """創建 HTML 標籤"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {
                    size: {{ width }}mm {{ height }}mm;
                    margin: 0;
                }
                body {
                    width: {{ width }}mm;
                    height: {{ height }}mm;
                    margin: 0;
                    padding: 0;
                    font-family: Arial, sans-serif;
                }
                .label {
                    padding: 20px 10px;
                }
                .field {
                    font-size: 10pt;
                    line-height: 1.1;
                    margin: 0;
                    padding: 0;
                }
            </style>
        </head>
        <body>
            <div class="label">
                {% for field, value in data %}
                <p class="field">{{ field }}: {{ value }}</p>
                {% endfor %}
            </div>
            <button onclick="reprintLabel('{{ serial_number }}')">Reprint Label</button>
        </body>
        </html>
        """
        
        template = Template(html_template)
        return template.render(
            width=self.label_width,
            height=self.label_height,
            data=data
        )

    def print_html(self, html_path):
        """將 HTML 轉換為 PDF 並使用 Adobe Acrobat 打印"""
        try:
            printer_name = win32print.GetDefaultPrinter()
            print(f"Printing to: {printer_name}")
            
            # 讀取 HTML 內容
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 提取數據
            label_content = re.search(r'<div class="label">(.*?)</div>', html_content, re.DOTALL)
            if not label_content:
                raise Exception("Label content not found")
                
            # 清理 HTML 標籤並提取序列號
            content = label_content.group(1)
            lines = []
            serial_number = None
            for line in content.split('\n'):
                cleaned = re.sub(r'<[^>]+>', '', line).strip()
                if cleaned:
                    lines.append(cleaned)
                    # 取序列號
                    if cleaned.startswith('SN:'):
                        serial_number = cleaned.split(':', 1)[1].strip()
            
            # 創建臨時 PDF 文件
            pdf_path = html_path + '.pdf'
            
            # 創建 PDF
            c = canvas.Canvas(
                pdf_path, 
                pagesize=(self.label_width * inch / 25.4, self.label_height * inch / 25.4)
            )
            
            # 設置字體和大小
            font_size = 10
            line_spacing = font_size * 1.1
            c.setFont("Helvetica", font_size)
            
            # 設置起始位置
            left_margin = font_size * 0.8 + 5
            top_margin = font_size * 2
            y_position = (self.label_height * inch / 25.4) - top_margin
            
            # 寫入內容
            for line in lines:
                c.drawString(left_margin, y_position, line)
                y_position -= line_spacing
            
            # 添加條形碼（如果有序列號）
            if serial_number:
                # 創建條形碼 - 設置 barWidth 為 1.0
                barcode = code128.Code128(
                    serial_number,
                    barWidth=1.0,     # 增加條碼寬度到 1.0
                    barHeight=20
                )
                
                # 計算條形碼位置（在底部居中）
                barcode_width = barcode.width
                x = ((self.label_width * inch / 25.4) - barcode_width) / 2
                y = font_size * 2  # 距離底部的距離
                
                # 繪製條形碼
                barcode.drawOn(c, x, y)
                
                # 在條形碼下方添加文字
                c.setFont("Helvetica", 8)
                text_width = c.stringWidth(serial_number, "Helvetica", 8)
                x = ((self.label_width * inch / 25.4) - text_width) / 2
                c.drawString(x, y - 10, serial_number)
            
            c.save()
            
            print("\nSending to printer...")
            
            # Adobe Acrobat 的可能路徑
            adobe_paths = [
                # Acrobat 2020 (64-bit)
                r"C:\Program Files\Adobe\Acrobat 2020\Acrobat\Acrobat.exe",
                # Acrobat 2020 (32-bit)
                r"C:\Program Files (x86)\Adobe\Acrobat 2020\Acrobat\Acrobat.exe",
                # 其他版本的路徑...
                r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
                r"C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\Acrobat.exe"
            ]
            
            # 搜索可能的安裝路徑
            adobe_exe = None
            for path in adobe_paths:
                if os.path.exists(path):
                    adobe_exe = path
                    print(f"Found Adobe Acrobat at: {path}")
                    break
                    
            if not adobe_exe:
                raise Exception("Adobe Acrobat not found")
            
            # Adobe Acrobat 打印命令
            adobe_cmd = [
                adobe_exe,
                "/h",  # 添加此参数以隐藏窗口
                "/t",
                pdf_path,
                printer_name
            ]
            
            # 執行打印命令，忽略錯誤輸出
            try:
                # 使用 CREATE_NO_WINDOW 标志
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                subprocess.run(
                    adobe_cmd,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=30,
                    startupinfo=startupinfo  # 添加此参数
                )
                print("Print job sent successfully")
                
                # 等待打印完成
                time.sleep(3)
                
            except subprocess.TimeoutExpired:
                print("Warning: Print command timed out, but job might have been sent")
            
            # 清理臨時文件
            try:
                os.unlink(pdf_path)
            except:
                pass
                
            return True
            
        except Exception as e:
            print(f"Error during printing process: {str(e)}")
            return False

    def read_csv_safely(self, csv_path):
        """安全讀取 CSV 文件"""
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                return pd.read_csv(f)
        except Exception as e:
            print(f"Error reading CSV file: {str(e)}")
            raise

    def simplify_data(self, field, value):
        """簡化數據顯示"""
        if value is None or pd.isna(value):
            return 'N/A'
            
        value = str(value)
        
        if field == 'SystemSKU':
            # 只保留 ThinkPad X1 Carbon Gen 8 部分
            if 'ThinkPad' in value:
                return value[value.find('ThinkPad'):]
            return value
            
        elif field == 'OperatingSystem':
            # 簡化為 Windows 11 Pro
            if 'Windows' in value:
                match = re.search(r'Windows (\d+) (\w+)', value)
                if match:
                    return f"Windows {match.group(1)} {match.group(2)}"
            return value
            
        elif field == 'CPU':
            # 簡化為 i5-10310U (4C/8T)
            if 'Intel' in value:
                match = re.search(r'i\d-\d+\w+', value)
                cores = re.search(r'\((\d+C/\d+T)\)', value)
                if match and cores:
                    return f"{match.group(0)} {cores.group(1)}"
            return value
            
        elif field == 'GraphicsCard':
            # 處理多個顯示卡的情況
            if ';' in value:
                cards = value.split(';')
                formatted_cards = []
                
                for card in cards:
                    card = card.strip()
                    # 處理 Intel 顯示卡
                    if 'Intel' in card:
                        card = card.replace('Intel(R) ', 'Intel ')
                        card = card.replace('Graphics', '')  # Remove "Graphics"
                        resolution = re.search(r'\[([\dx]+)\]', card)
                        base_name = card.split('[')[0].strip()
                        if resolution:
                            formatted_cards.append(f"{base_name} [{resolution.group(1)}]")
                        else:
                            formatted_cards.append(base_name)
                    # 處理 NVIDIA 顯示卡
                    elif 'NVIDIA' in card:
                        # 移除不必要的文字，但保留 NVIDIA
                        card = card.replace('[Not Active]', '').strip()
                        card = card.replace('with Max-Q Design', 'MQ').strip()
                        formatted_cards.append(card)
                    # 處理 AMD 顯示卡
                    elif 'AMD' in card:
                        card = card.replace('Radeon(TM) ', '').strip()
                        formatted_cards.append(card)
                    else:
                        formatted_cards.append(card)
                
                # 用換行符連接多個顯示卡
                return '\n'.join(formatted_cards)
            
            # 單個顯示卡的處理
            if 'Intel' in value:
                value = value.replace('Intel(R) ', 'Intel ')
                value = value.replace('Graphics', '')
                resolution = re.search(r'\[([\dx]+)\]', value)
                base_name = value.split('[')[0].strip()
                if resolution:
                    return f"{base_name} [{resolution.group(1)}]"
                return base_name
            elif 'NVIDIA' in value:
                value = value.replace('with Max-Q Design', 'MQ').strip()
                return value
            elif 'AMD' in value:
                value = value.replace('Radeon(TM) ', '').strip()
                return value
            return value
            
        elif field == 'Full_Charge_Capacity':
            # 處理雙電池格式的電池容量
            if isinstance(value, str) and ',' in value:
                # 處理雙電池格式 "44000, 40000"
                capacities = [c.strip() for c in value.split(',')]
                formatted_capacities = []
                for capacity in capacities:
                    try:
                        formatted_capacities.append(str(int(float(capacity))))
                    except:
                        formatted_capacities.append(capacity)
                return ' / '.join(formatted_capacities)
            else:
                # 單電池格式，移除小數點
                try:
                    return str(int(float(value)))
                except:
                    return value
                
        elif field == 'Battery_Health':
            # 處理雙電池格式的電池健康度
            if isinstance(value, str) and ',' in value:
                # 處理雙電池格式 "75, 80"
                health_values = [h.strip() for h in value.split(',')]
                formatted_health = []
                for health in health_values:
                    try:
                        formatted_health.append(f"{int(float(health))}%")
                    except:
                        formatted_health.append(f"{health}%")
                return ' / '.join(formatted_health)
            else:
                # 單電池格式，移除小數點並添加百分比符號
                try:
                    return f"{int(float(value))}%"
                except:
                    return value
                
        elif field == 'Cycle_Count':
            # 處理雙電池格式的循環次數
            if isinstance(value, str) and ',' in value:
                # 處理雙電池格式 "123, 145"
                counts = [c.strip() for c in value.split(',')]
                formatted_counts = []
                for count in counts:
                    try:
                        formatted_counts.append(str(int(float(count))))
                    except:
                        formatted_counts.append(count)
                return ' / '.join(formatted_counts)
            else:
                # 單電池格式，移除小數點
                try:
                    return str(int(float(value)))
                except:
                    return value
                
        elif field == 'TouchScreen':
            return process_touchscreen(value)
            
        elif field == 'RAM_GB':
            # 处理 RAM 显示，例如: "16GB"
            try:
                if 'GB' in value.upper():
                    return value
                # 如果只是数字，添加 GB
                return f"{value}GB"
            except:
                return value
            
        elif field == 'Disks':
            try:
                # 如果是 JSON 字符串，解析它
                if isinstance(value, str):
                    if value.startswith('['):
                        disks = json.loads(value)
                        if isinstance(disks, list):
                            total_size = 0
                            for disk in disks:
                                if isinstance(disk, dict) and 'size_gb' in disk:
                                    try:
                                        size_str = str(disk['size_gb'])
                                        # 檢查是否已經包含單位
                                        if 'TB' in size_str.upper():
                                            # 如果是 TB，轉換為 GB 進行計算
                                            size_num = float(size_str.upper().replace('TB', '').strip()) * 1024
                                        else:
                                            # 如果是 GB 或無單位，直接轉換
                                            size_num = float(size_str.upper().replace('GB', '').strip())
                                        total_size += size_num
                                    except ValueError:
                                        continue
                        
                            # 轉換為適當的單位
                            if total_size >= 1024:
                                return f"{total_size/1024:.0f}TB"
                            return f"{total_size:.0f}GB"
                    else:
                        # 處理單個磁盤大小
                        size_str = str(value).upper()
                        if 'TB' in size_str:
                            # 已經是 TB，保持原樣
                            size_num = float(size_str.replace('TB', '').strip())
                            return f"{size_num:.0f}TB"
                        else:
                            # 假設是 GB，檢查是否需要轉換為 TB
                            size_num = float(size_str.replace('GB', '').strip())
                            if size_num >= 1024:
                                return f"{size_num/1024:.0f}TB"
                            return f"{size_num:.0f}GB"
                return str(value)
            except Exception as e:
                print(f"Error formatting disk size: {str(e)}, value: {value}")
                return str(value)
        
        elif field == 'created_at':
            # 統一日期格式為 YYYY-MM-DD HH:MM
            try:
                # 檢查是否已經是 datetime 對象
                if hasattr(value, 'strftime'):
                    return value.strftime('%Y-%m-%d %H:%M')
                
                # 嘗試解析不同格式的日期字符串
                from datetime import datetime
                
                # 嘗試常見的日期格式
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return dt.strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        continue
                
                # 如果無法解析，返回原始值
                return value
            except Exception as e:
                print(f"Error formatting date: {str(e)}, value: {value}")
                return value
        
        return str(value)

    def is_sn_printed(self, serial_number):
        """檢查序列號是否在1分鐘內已經打印過"""
        try:
            if not os.path.exists(self.log_file):
                return False
            
            current_time = time.time()
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if serial_number in line:
                        try:
                            log_time_str = line.split(' - ')[0]
                            log_time = time.mktime(time.strptime(log_time_str, '%Y-%m-%d %H:%M:%S'))
                            
                            # 檢查是否在1分鐘內
                            if current_time - log_time < 60:  # 60 秒 = 1 分鐘
                                print(f"Warning: SN {serial_number} was printed less than 1 minute ago")
                                return True
                        except:
                            continue
            return False
        except:
            return False

    def log_print(self, serial_number):
        """記錄打印日誌"""
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Printed SN: {serial_number}\n")
        except:
            pass

    def print_latest_record(self, csv_path):
        """打印最新記錄"""
        html_path = None
        try:
            if not os.path.exists(csv_path):
                print(f"Error: File not found {csv_path}")
                return False
            
            if os.path.getsize(csv_path) == 0:
                print("Error: CSV file is empty")
                return False
            
            # 取 CSV
            df = self.read_csv_safely(csv_path)
            if df.empty:
                print("CSV file has no records")
                return False
            
            latest_record = df.iloc[-1].copy()  # 使用 copy 避免修改原始數據
            
            # 準備時間欄位
            if 'Timestamp' in latest_record:
                latest_record['created_at'] = latest_record['Timestamp']
            elif 'created_at' not in latest_record:
                latest_record['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 準備數據，使用 simplify_data 方法處理所有欄位
            data = []
            
            # 定義欄位映射和順序
            field_mapping = {
                'SerialNumber': ('SN', 'SerialNumber'),
                'Manufacturer': ('Brand', 'Manufacturer'),
                'Model': ('Model', 'Model'),
                'SystemSKU': ('SKU', 'SystemSKU'),
                'OperatingSystem': ('OS', 'OperatingSystem'),
                'CPU': ('CPU', 'CPU'),
                'GraphicsCard': ('GPU', 'GraphicsCard'),
                'RAM_GB': ('RAM', 'RAM_GB'),
                'Disks': ('Disk', 'Disks'),
                'Full_Charge_Capacity': ('Full Capacity', 'Full_Charge_Capacity'),
                'Cycle_Count': ('Cycle Count', 'Cycle_Count'),
                'Battery_Health': ('BT Health', 'Battery_Health'),
                'TouchScreen': ('Touch Screen', 'TouchScreen'),
                'created_at': ('Created', 'created_at')
            }
            
            # 按順序處理每個欄位
            for db_field, (display_name, simplify_field) in field_mapping.items():
                if db_field in latest_record and latest_record[db_field] is not None:
                    # 使用 simplify_data 方法處理值
                    value = self.simplify_data(simplify_field, latest_record[db_field])
                    data.append((display_name, value))
            
            # 創建臨時 HTML 文件
            with tempfile.NamedTemporaryFile(
                delete=False, suffix='.html', mode='w', encoding='utf-8'
            ) as tmp_file:
                html_path = tmp_file.name
                tmp_file.write(self.create_html(data))
            
            # 直接打印，不預覽
            if self.print_html(html_path):
                print(f"Label printed successfully for SN: {latest_record['SerialNumber']}")
                self.log_print(latest_record['SerialNumber'])  # 记录打印时间
                return True
            return False
            
        except Exception as e:
            print(f"Error during printing process: {str(e)}")
            return False
            
        finally:
            # 清理臨時文件
            if html_path and os.path.exists(html_path):
                try:
                    os.unlink(html_path)
                except Exception as e:
                    print(f"Error cleaning up temporary files: {str(e)}")

    def reprint_by_sn(self, serial_number):
        """Reprint a label for a specific serial number"""
        try:
            print(f"Attempting to reprint label for SN: {serial_number}")
            
            # Get database instance
            db = Database()
            # Query the record by SN
            with db:  # Use context manager
                record = db.get_record_by_sn(serial_number)
            
            if not record:
                print(f"No record found for SN: {serial_number}")
                return False
            
            print(f"Found record: {record}")
            
            # 處理時間欄位
            if 'Timestamp' in record:
                record['created_at'] = record['Timestamp']
            elif 'created_at' not in record:
                record['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 準備數據，使用 simplify_data 方法處理所有欄位
            data = []
            
            # 定義欄位映射和順序
            field_mapping = {
                'SerialNumber': ('SN', 'SerialNumber'),
                'Manufacturer': ('Brand', 'Manufacturer'),
                'Model': ('Model', 'Model'),
                'SystemSKU': ('SKU', 'SystemSKU'),
                'OperatingSystem': ('OS', 'OperatingSystem'),
                'CPU': ('CPU', 'CPU'),
                'GraphicsCard': ('GPU', 'GraphicsCard'),
                'RAM_GB': ('RAM', 'RAM_GB'),
                'Disks': ('Disk', 'Disks'),
                'Full_Charge_Capacity': ('Full Capacity', 'Full_Charge_Capacity'),
                'Cycle_Count': ('Cycle Count', 'Cycle_Count'),
                'Battery_Health': ('BT Health', 'Battery_Health'),
                'TouchScreen': ('Touch Screen', 'TouchScreen'),
                'created_at': ('Created', 'created_at')
            }
            
            # 按順序處理每個欄位
            for db_field, (display_name, simplify_field) in field_mapping.items():
                if db_field in record and record[db_field] is not None:
                    # 使用 simplify_data 方法處理值
                    value = self.simplify_data(simplify_field, record[db_field])
                    data.append((display_name, value))
            
            print(f"Prepared data for printing: {data}")
            
            if not data:
                print("No data prepared for printing")
                return False
            
            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(
                delete=False, suffix='.html', mode='w', encoding='utf-8'
            ) as tmp_file:
                html_path = tmp_file.name
                html_content = self.create_html(data)
                tmp_file.write(html_content)
                print(f"Created temporary HTML file: {html_path}")
            
            try:
                # Print the label
                success = self.print_html(html_path)
                if success:
                    print(f"Label printed successfully for SN: {serial_number}")
                    self.log_print(serial_number)
                    return True
                
                print("Failed to print label")
                return False
                
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(html_path):
                        os.unlink(html_path)
                except Exception as e:
                    print(f"Error cleaning up temporary file: {str(e)}")
            
        except Exception as e:
            print(f"Error during reprinting process: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def process_battery_value(self, value):
        """處理電池數據，支持雙電池格式
        
        Args:
            value: 電池數據值
            
        Returns:
            處理後的值 (字符串或浮點數)
        """
        if value is None or pd.isna(value):
            return None
        
        # 轉換為字符串
        str_value = str(value).strip()
        
        # 檢查是否包含逗號（雙電池格式）
        if ',' in str_value:
            # 處理雙電池格式
            parts = [part.strip() for part in str_value.split(',')]
            formatted_parts = []
            for part in parts:
                try:
                    # 嘗試轉換為整數顯示
                    formatted_parts.append(str(int(float(part))))
                except ValueError:
                    # 如果無法轉換，保留原樣
                    formatted_parts.append(part)
            # 連接並返回格式化的雙電池數據
            return ' / '.join(formatted_parts)
        else:
            # 單電池情況，嘗試轉換為整數
            try:
                return str(int(float(str_value)))
            except ValueError:
                # 如果無法轉換，返回原始值
                return str_value

def print_new_record(csv_path):
    """外部調用函數，只打印最新記錄"""
    try:
        printer = LabelPrinterHTML()
        return printer.print_latest_record(csv_path)
    except Exception as e:
        print(f"Error in print_new_record: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def format_display_text(text, max_length=50):
    """Format display text with line breaks if needed"""
    if len(text) <= max_length:
        return text
        
    # Split by semicolon for multiple GPUs
    if ';' in text:
        parts = text.split(';')
        formatted_parts = []
        for part in parts:
            part = part.strip()
            # Format NVIDIA GPU
            if 'NVIDIA' in part:
                # Remove '[Not Active]' and simplify name
                part = part.replace('[Not Active]', '').strip()
                part = part.replace('with Max-Q Design', 'MQ').strip()
                formatted_parts.append(part)
            # Format Intel GPU
            elif 'Intel' in part:
                part = part.replace('Intel(R) ', '')
                resolution = re.search(r'\[([\dx]+)\]', part)
                base_name = part.split('[')[0].strip()
                if resolution:
                    formatted_parts.append(f"{base_name} [{resolution.group(1)}]")
                else:
                    formatted_parts.append(base_name)
        
        # Join with line breaks if total length is too long
        result = ''
        current_line = ''
        for part in formatted_parts:
            if len(current_line) + len(part) > max_length and current_line:
                result += current_line.strip() + '\n'
                current_line = part + ' '
            else:
                current_line += part + ' '
        result += current_line.strip()
        return result
    
    # Single GPU case
    words = text.split()
    result = ''
    current_line = ''
    for word in words:
        if len(current_line) + len(word) > max_length and current_line:
            result += current_line.strip() + '\n'
            current_line = word + ' '
        else:
            current_line += word + ' '
    result += current_line.strip()
    return result

def find_record_by_sn(sn, csv_file_path):
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                if row.get('SN', '').strip() == sn.strip():
                    # Format GPU information if present
                    if 'GraphicsCard' in row:
                        row['GraphicsCard'] = format_display_text(row['GraphicsCard'])
                    return row
    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_file_path}")
        return None
    except Exception as e:
        print(f"Error reading CSV: {str(e)}")
        return None
    return None

def process_touchscreen(value):
    """統一處理 touchscreen 值的格式"""
    if not value or pd.isna(value):
        return 'Unknown'
    
    value = str(value).lower().strip()
    if 'yes' in value in value:
        return 'Yes Detected'
    if 'no' in value or 'not' in value:
        return 'No'
    return 'Not Detected'

def print_label_for_record(record):
    """Print label for a specific record"""
    try:
        printer = LabelPrinterHTML()
        
        # 準備數據
        field_names = {
            'serialnumber': 'SN',
            'manufacturer': 'Brand',
            'model': 'Model',
            'systemsku': 'SKU',
            'operatingsystem': 'OS',
            'cpu': 'CPU',
            'graphicscard': 'GPU',
            'ram_gb': 'RAM',
            'disks': 'Disk',
            'full_charge_capacity': 'Full Capacity',
            'battery_health': 'BT Health',
            'touchscreen': 'Touch Screen',
            'created_at': 'Created'
        }
        
        data = []
        for field, display_name in field_names.items():
            if field in record:
                value = printer.simplify_data(field.title(), record[field])
                data.append((display_name, value))
        
        # 創建臨時 HTML 文件並打印
        with tempfile.NamedTemporaryFile(
            delete=False, suffix='.html', mode='w', encoding='utf-8'
        ) as tmp_file:
            html_path = tmp_file.name
            tmp_file.write(printer.create_html(data))
            
        try:
            success = printer.print_html(html_path)
            if success:
                printer.log_print(record['serialnumber'])
            return success
        finally:
            if os.path.exists(html_path):
                try:
                    os.unlink(html_path)
                except:
                    pass
                    
    except Exception as e:
        print(f"Error printing label: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@app.route('/print_label/<serial_number>', methods=['POST'])
def print_label_route(serial_number):
    try:
        timestamp = request.args.get('timestamp')
        if not timestamp:
            return jsonify({'success': False, 'message': 'Timestamp is required'})
            
        # 創建打印實例
        printer = LabelPrinterHTML()
        
        # 檢查是否在1分鐘內已經打印過
        if printer.is_sn_printed(serial_number):
            return jsonify({
                'success': False, 
                'message': 'This label was printed less than 1 minute ago'
            })
            
        # 調用重新打印功能
        success = printer.reprint_by_sn(serial_number)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Failed to print label'})
            
    except Exception as e:
        print(f"Error in print_label_route: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})

def print_label_by_id(record_id):
    """根據記錄 ID 打印標籤"""
    try:
        with Database() as db:
            # 從數據庫獲取記錄
            db.cursor.execute("""
                SELECT 
                    serialnumber, manufacturer, model, systemsku,
                    operatingsystem, cpu, graphicscard, ram_gb,
                    disks, design_capacity, full_charge_capacity, 
                    cycle_count, battery_health, touchscreen, created_at
                FROM system_records 
                WHERE id = %s
            """, (record_id,))
            record = db.cursor.fetchone()
            
            if not record:
                print(f"Record not found with ID: {record_id}")
                return False
            
            # 創建打印實例
            printer = LabelPrinterHTML()
            
            # 準備標籤數據，使用 simplify_data 方法處理所有欄位
            label_data = []
            
            # 定義欄位映射和順序
            field_mapping = {
                'serialnumber': ('SN', 'SerialNumber'),
                'manufacturer': ('Brand', 'Manufacturer'),
                'model': ('Model', 'Model'),
                'systemsku': ('SKU', 'SystemSKU'),
                'operatingsystem': ('OS', 'OperatingSystem'),
                'cpu': ('CPU', 'CPU'),
                'graphicscard': ('GPU', 'GraphicsCard'),
                'ram_gb': ('RAM', 'RAM_GB'),
                'disks': ('Disk', 'Disks'),
                'full_charge_capacity': ('Full Capacity', 'Full_Charge_Capacity'),
                'cycle_count': ('Cycle Count', 'Cycle_Count'),
                'battery_health': ('BT Health', 'Battery_Health'),
                'touchscreen': ('Touch Screen', 'TouchScreen'),
                'created_at': ('Created', 'created_at')
            }
            
            # 按順序處理每個欄位
            for db_field, (display_name, simplify_field) in field_mapping.items():
                if record[db_field] is not None:
                    # 電池相關欄位需要特殊處理
                    if db_field in ['design_capacity', 'full_charge_capacity', 'cycle_count', 'battery_health']:
                        # 使用 process_battery_value 方法處理電池數據
                        value = printer.simplify_data(simplify_field, record[db_field])
                    else:
                        # 其他欄位使用標準 simplify_data 方法
                        value = printer.simplify_data(simplify_field, record[db_field])
                    label_data.append((display_name, value))
            
            # 創建臨時 HTML 文件
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as f:
                html_content = printer.create_html(label_data)
                f.write(html_content)
                temp_path = f.name
            
            try:
                # 打印標籤
                success = printer.print_html(temp_path)
                
                # 如果打印成功，記錄打印時間
                if success:
                    printer.log_print(record['serialnumber'])
                    print(f"Successfully printed label for SN: {record['serialnumber']}")
                else:
                    print(f"Failed to print label for SN: {record['serialnumber']}")
                
                return success
                
            finally:
                # 清理臨時文件
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass
            
    except Exception as e:
        print(f"Error printing label: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    app.run(port=5000)
    
    # # Original code (commented out)
    # # 使用空路径，由外部传入
    # print_new_record("")
    # 
    # # 测试数据路径（已注释）
    # csv_path = r"\\192.168.0.10\Files\03_IT\data\system_records-bak.csv"
    # print_new_record(csv_path)
  