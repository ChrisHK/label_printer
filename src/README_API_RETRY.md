# API 上傳重試功能

此功能用於處理因各種原因（如網絡問題、認證失敗等）而失敗的API上傳。該功能可以從日誌文件中查找失敗的上傳記錄，並提供重試機制。

## 功能特點

- 自動從日誌文件中分析並識別失敗的API上傳
- 支持分類不同類型的錯誤（認證錯誤、超時、網絡問題等）
- 提供命令行界面，可以查看失敗記錄、重試特定記錄、標記記錄為已解決等
- 自動跳過已達到最大重試次數的記錄
- 保存重試結果，便於後續跟進

## 使用方法

### 命令行工具

使用 `retry_api_uploads.py` 命令行工具來管理API重試：

```bash
# 顯示幫助信息
python src/retry_api_uploads.py --help

# 列出近7天的失敗上傳
python src/retry_api_uploads.py --list

# 列出近30天的失敗上傳
python src/retry_api_uploads.py --list --days 30

# 重試所有待處理的失敗上傳
python src/retry_api_uploads.py --retry

# 重試指定ID的上傳
python src/retry_api_uploads.py --retry-id 1234

# 將指定ID標記為已解決（不需要重試）
python src/retry_api_uploads.py --mark-resolved 1234

# 設置最大重試次數（默認為3）
python src/retry_api_uploads.py --retry --max-retries 5

# 運行完整流程（查找失敗上傳並嘗試重試）
python src/retry_api_uploads.py --days 14
```

### 添加到排程任務

建議將API重試功能添加到Windows排程任務中，定期自動運行：

1. 打開Windows任務計劃程序
2. 創建一個新任務
3. 設置運行時間（如每天凌晨2點）
4. 設置操作為運行程序：`python`
5. 添加參數：`C:\path\to\label_printer\src\retry_api_uploads.py --retry --days 7`

## 結果文件

API重試過程的結果會保存在 `results/api_retry_results.json` 文件中，包含以下信息：

- 記錄ID和序列號
- 錯誤類型和錯誤訊息
- 重試次數和最後重試時間
- 解決狀態和解決方法

## 日誌文件

API重試過程的日誌會寫入 `src/api_retry.log` 文件，以便查看詳細的運行過程和問題診斷。

## 故障排除

如果遇到問題，請檢查：

1. 確保日誌目錄（`logs/`）存在且包含 `sync_*.log` 文件
2. 確保API連接參數（用戶名/密碼）正確
3. 查看 `api_retry.log` 文件以獲取詳細錯誤信息 