# Label Printer 功能菜單

## 獨立執行程序

### **retry_api_uploads.py**
API 上傳重試工具
```bash
python src/retry_api_uploads.py [選項]
```
選項：
- `--days N`: 查找最近 N 天的失敗上傳（默認：7天）
- `--list`: 列出所有失敗的上傳
- `--retry`: 重試所有待處理的失敗上傳
- `--retry-id ID`: 重試特定 ID 的上傳
- `--mark-resolved ID`: 將特定 ID 標記為已解決
- `--max-retries N`: 設置每條記錄的最大重試次數（默認：3）

### **csv_sync_manager.py**
CSV 數據同步管理工具
```bash
python src/csv_sync_manager.py [選項]
```
選項：
- `--sync`: 執行同步
- `--check`: 檢查同步狀態
- `--clean`: 清理同步日誌
- `--status`: 顯示同步狀態

### **print_label_html.py**
標籤打印工具
```bash
python src/print_label_html.py [選項]
```
選項：
- `--id ID`: 打印特定 ID 的標籤
- `--batch`: 批量打印標籤
- `--preview`: 預覽標籤

## 核心功能模塊

### api_retry_manager.py
API 重試管理核心類
- 處理失敗的 API 上傳
- 管理重試邏輯
- 記錄重試結果
- 錯誤分類和處理

### csv_sync_manager.py
CSV 同步管理核心類
- 處理 CSV 文件導入
- 數據驗證和轉換
- 同步狀態管理
- 錯誤處理和日誌記錄

### html_preview.py
HTML 預覽生成器
- 生成數據預覽頁面
- 提供搜索和過濾功能
- 支持標籤打印預覽
- 數據展示格式化

### sqldb.py
數據庫管理模塊
- 數據庫連接管理
- 查詢執行
- 事務處理
- 錯誤處理

### test_api.py
API 測試和連接模塊
- API 連接管理
- 請求數據準備
- 響應處理
- 錯誤處理

## 輔助工具

### initdb.py
數據庫初始化工具
- 創建數據表
- 設置索引
- 初始化配置
- 數據庫結構管理

### utils.py
通用工具函數
- 日期時間處理
- 數據格式轉換
- 文件操作
- 日誌處理

## 使用建議

1. **日常使用**：
   - 使用 `csv_sync_manager.py` 進行數據同步
   - 使用 `print_label_html.py` 打印標籤
   - 使用 `retry_api_uploads.py` 處理失敗的上傳

2. **故障排除**：
   - 檢查日誌文件
   - 使用 `--list` 和 `--status` 選項查看狀態
   - 使用 `--retry` 重試失敗的操作

3. **維護任務**：
   - 定期運行 `--clean` 清理日誌
   - 檢查數據庫狀態
   - 更新配置信息

## 注意事項

1. 所有獨立執行程序都支持 `--help` 選項查看詳細使用說明
2. 建議定期備份數據庫和日誌文件
3. 重要操作前先使用預覽功能確認
4. 保持日誌目錄的足夠空間 