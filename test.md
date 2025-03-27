檢查下遠端host的資料:
Remote host資料: nodejs version 20.12.2
Backend和Frontend: erp.zerounique.com:80 
數據網址27.0.0.200:5432
數據庫:zerouniq_db
數據庫帳號:zerouniq_admin
數據庫密碼:is-Admin

首先是backend, 一打開 api.zerounique.com, 會彈出https://api.zerounique.com/cgi-sys/defaultwebpage.cgi.
如何在cpanel解決這個問題?

讓我們重新開始, 幫我把在system-monitor-prod 下的 backend-v20 和frontend-v20的文件按照部署到chemicloud的 erp.zerounique.com 的路徑格式, 搬到到文件夾system-monitor-prod/website裡面, 
production 的package.json 文件, 需要安裝的依賴全部寫到 package.json 裡面.

# DO NOT REMOVE. CLOUDLINUX PASSENGER CONFIGURATION BEGIN
PassengerAppRoot "/home/zerouniq/erp.zerounique.com"
PassengerBaseURI "/"
PassengerNodejs "/home/zerouniq/nodevenv/erp.zerounique.com/20/bin/node"
PassengerAppType node
PassengerStartupFile src/app.js
# DO NOT REMOVE. CLOUDLINUX PASSENGER CONFIGURATION END
不要start.sh 文件.


然後我們development 模式下, 我們的database 是
localhost:5432, 我們的database 是 zerodev, 我們的database 帳號是 zero, 我們的database 密碼是 zero.
production 模式下, 我們的database 是
127.0.0.200:5432, 我們的database 是 zerouniq_db, 我們的database 帳號是 zerouniq, 我們的database 密碼是 is-Admin.


如何在遠端伺服器執行它?



 

1. Default Language english and chinese
2. input english and chinese
3. google chrome
4. google meeting
5. office 2021 english and chinese
6. PDF
7. shoutcut: https://myeliteschool.com/
Logo:
desktop background
login icon

Folder:




1首先，清理處理日誌：
# 清理日誌
$headers = @{
    "Authorization" = "Bearer your_token_here"
}

Invoke-RestMethod -Method Delete `
    -Uri "https://erp.zerounique.com/api/data-process/logs" `
    -Headers $headers
2. 檢查當前處理狀態：
# 獲取所有日誌
Invoke-RestMethod -Method Get `
    -Uri "https://erp.zerounique.com/api/data-process/logs" `
    -Headers $headers


群組的權限設置了01 Main Store, 但是sitebar 的menu 沒有更新01 Main Store.
, 需要增加01 Main Store

依然沒看到01 Main Store在sitebar 的menu.



