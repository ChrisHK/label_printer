#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API上傳重試工具

用法:
    python retry_api_uploads.py [options]

選項:
    --days N             查找最近N天的失敗上傳 (默認: 7)
    --list               列出所有失敗的上傳
    --retry              重試所有待處理的失敗上傳
    --retry-id ID        重試指定ID的上傳
    --mark-resolved ID   將指定ID標記為已解決
    --max-retries N      設置每條記錄的最大重試次數 (默認: 3)
    --help               顯示幫助信息
"""

import os
import sys
import json
import argparse
from api_retry_manager import APIRetryManager
from datetime import datetime


def parse_arguments():
    """解析命令行參數"""
    parser = argparse.ArgumentParser(description="API上傳重試工具")
    
    parser.add_argument("--days", type=int, default=7,
                        help="查找最近N天的失敗上傳 (默認: 7)")
    
    parser.add_argument("--list", action="store_true", 
                        help="列出所有失敗的上傳")
    
    parser.add_argument("--retry", action="store_true",
                        help="重試所有待處理的失敗上傳")
    
    parser.add_argument("--retry-id", type=int,
                        help="重試指定ID的上傳")
    
    parser.add_argument("--mark-resolved", type=int,
                        help="將指定ID標記為已解決")
    
    parser.add_argument("--max-retries", type=int, default=3,
                        help="設置每條記錄的最大重試次數 (默認: 3)")
    
    # 如果沒有參數，顯示幫助
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
        
    return parser.parse_args()


def print_failed_uploads(failed_uploads):
    """打印失敗的上傳列表"""
    if not failed_uploads:
        print("沒有失敗的上傳記錄")
        return
        
    print("\n失敗的API上傳記錄:")
    print("-" * 80)
    print(f"{'ID':<8} {'序列號':<15} {'錯誤訊息':<30} {'狀態':<10} {'重試':<5}")
    print("-" * 80)
    
    for upload in failed_uploads:
        record_id = upload.get("record_id", "N/A")
        serial = upload.get("serial_number", "N/A")
        error = upload.get("error_message", "N/A")
        resolved = "已解決" if upload.get("resolved", False) else "待處理"
        retry_count = upload.get("retry_count", 0)
        
        # 截斷錯誤訊息
        if len(error) > 27:
            error = error[:24] + "..."
            
        print(f"{record_id:<8} {serial:<15} {error:<30} {resolved:<10} {retry_count:<5}")
    
    print("-" * 80)
    
    # 打印統計信息
    total = len(failed_uploads)
    resolved = sum(1 for u in failed_uploads if u.get("resolved", False))
    pending = total - resolved
    
    print(f"總計: {total} 條記錄, 已解決: {resolved}, 待處理: {pending}")


def main():
    """主函數"""
    args = parse_arguments()
    
    # 創建API重試管理器
    retry_manager = APIRetryManager()
    
    # 如果只是列出失敗的上傳
    if args.list:
        # 查找失敗的上傳
        failed_uploads = retry_manager.find_failed_uploads(args.days)
        # 分類錯誤
        error_types = retry_manager.classify_errors(failed_uploads)
        # 加載之前的結果
        previous_results = retry_manager.load_results()
        
        # 合併結果 (以之前的結果為基礎)
        if previous_results:
            # 查找新的失敗上傳
            existing_ids = {r.get("record_id") for r in previous_results}
            for upload in failed_uploads:
                if upload.get("record_id") not in existing_ids:
                    previous_results.append(upload)
            
            # 打印結果
            print_failed_uploads(previous_results)
        else:
            # 直接打印新查找的結果
            print_failed_uploads(failed_uploads)
            
    # 如果是重試特定ID的上傳
    elif args.retry_id:
        record_id = args.retry_id
        print(f"重試上傳記錄ID: {record_id}")
        
        success, message = retry_manager.retry_upload(record_id)
        
        if success:
            print(f"重試成功: {message}")
            
            # 更新結果文件
            results = retry_manager.load_results()
            for result in results:
                if result.get("record_id") == record_id:
                    result["resolved"] = True
                    result["resolution_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    result["resolution_method"] = "manual_retry"
                    result["retry_count"] = result.get("retry_count", 0) + 1
                    retry_manager.save_results(results)
                    break
        else:
            print(f"重試失敗: {message}")
    
    # 如果是標記特定ID為已解決
    elif args.mark_resolved:
        record_id = args.mark_resolved
        print(f"將記錄ID: {record_id} 標記為已解決")
        
        if retry_manager.mark_as_resolved(record_id):
            print("操作成功")
        else:
            print("操作失敗")
            
    # 如果是重試所有待處理的失敗上傳
    elif args.retry:
        print(f"重試所有待處理的失敗上傳 (最大重試次數: {args.max_retries})")
        stats = retry_manager.retry_all_pending(args.max_retries)
        
        print(f"\n重試結果:")
        print(f"總計: {stats['total']}")
        print(f"成功: {stats['success']}")
        print(f"失敗: {stats['failed']}")
        print(f"跳過: {stats['skipped']}")
    
    # 如果沒有指定操作，運行完整流程
    else:
        print(f"運行完整的API重試流程 (查找最近 {args.days} 天的失敗上傳)")
        retry_manager.run(args.days)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n錯誤: {str(e)}")
        sys.exit(1) 