import asyncio
import aiohttp
import json
from datetime import datetime

async def test_erp_connection():
    """測試ERP連接"""
    url = "https://erp.zerounique.com/api/users/login"
    
    # 測試數據
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    print(f"Testing connection to {url}")
    print(f"Request data: {json.dumps(login_data, indent=2)}")
    
    # 設置超時
    timeout = aiohttp.ClientTimeout(total=10)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            start_time = datetime.now()
            print(f"\nStarting request at {start_time.strftime('%H:%M:%S')}")
            
            async with session.post(url, json=login_data) as response:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                print(f"Request completed in {duration:.2f} seconds")
                print(f"Status: {response.status}")
                
                try:
                    data = await response.json()
                    print(f"Response: {json.dumps(data, indent=2)}")
                except:
                    text = await response.text()
                    print(f"Raw response: {text}")
                
    except asyncio.TimeoutError:
        print("Request timed out after 10 seconds")
    except aiohttp.ClientError as e:
        print(f"Network error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    print("Starting ERP connection test...")
    asyncio.run(test_erp_connection()) 