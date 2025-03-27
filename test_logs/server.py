def sync_data(items):
    """同步數據到生產環境"""
    try:
        # 準備數據
        data = prepare_data_for_api(items)
        
        # 發送請求
        response = requests.post(
            f"{API_BASE_URL}/data-process/inventory",
            json=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {API_TOKEN}'
            }
        )
        
        # 檢查響應
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                logger.info(f"Sync successful: {len(items)} items processed")
                return True, result
            else:
                logger.error(f"Sync failed: {result.get('error')}")
                return False, result
        else:
            error_msg = f"API request failed with status {response.status_code}"
            try:
                error_details = response.json()
                error_msg = f"{error_msg}: {error_details.get('details', 'No details provided')}"
            except:
                pass
            logger.error(error_msg)
            return False, {'error': error_msg}
                
    except Exception as e:
        logger.error(f"Sync error: {str(e)}", exc_info=True)
        return False, {'error': str(e)}

def retry_with_backoff(func, max_retries=3, initial_delay=1):
    """使用退避策略重試函數"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = initial_delay * (2 ** attempt)  # 指數退避
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay} seconds...")
            time.sleep(delay)

# 使用示例
def process_batch(items):
    try:
        success, result = retry_with_backoff(
            lambda: sync_data(items)
        )
        if not success:
            logger.error(f"Failed to process batch after retries: {result.get('error')}")
            # 可以在這裡添加額外的錯誤處理邏輯
    except Exception as e:
        logger.error(f"Fatal error processing batch: {str(e)}", exc_info=True)