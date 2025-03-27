import asyncio
from inventory_sync.sync_manager import InventorySync

async def test_login():
    """測試登入功能"""
    sync_manager = InventorySync(env="prod")
    
    print("Testing login to production environment...")
    success = await sync_manager.login("admin", "admin123")
    
    if success:
        print("Login successful!")
        print(f"Token: {sync_manager.auth_token}")
    else:
        print("Login failed!")

if __name__ == "__main__":
    asyncio.run(test_login()) 