import os
from datetime import datetime
from sqldb import Database
import pandas as pd
from jinja2 import Template
import json
from flask import Flask, render_template
from print_label_html import app as print_app

app = Flask(__name__)
app.register_blueprint(print_app)

@app.route('/')
def index():
    return generate_html_preview()

def generate_html_preview():
    """Generate HTML preview of database records"""
    try:
        # Get template path
        template_path = os.path.join(os.path.dirname(__file__), 'static', 'template.html')
        
        # Create template content with search functionality
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Database Records Preview</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        tr:hover { background-color: #f5f5f5; }
        .yes { color: green; }
        .no { color: red; }
        .unknown { color: gray; }
        .search-container {
            background-color: #f8f8f8;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }
        .search-wrapper {
            display: flex;
            align-items: center;
            gap: 10px;
            max-width: 600px;
            margin: 0 auto;
        }
        .search-select {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            min-width: 120px;
            background-color: white;
            cursor: pointer;
        }
        .search-select:focus {
            outline: none;
            border-color: #4CAF50;
            box-shadow: 0 0 5px rgba(76,175,80,0.3);
        }
        #searchInput {
            flex: 1;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            min-width: 200px;
        }
        #searchInput:focus {
            outline: none;
            border-color: #4CAF50;
            box-shadow: 0 0 5px rgba(76,175,80,0.3);
        }
        .search-btn {
            position: relative;
            padding: 8px 20px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            min-width: 100px;
            transition: background-color 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .search-btn:hover {
            background-color: #45a049;
        }
        .no-results {
            padding: 20px;
            text-align: center;
            color: #666;
            font-style: italic;
            display: none;
            margin-top: 10px;
            background-color: #fff3e0;
            border: 1px solid #ffe0b2;
            border-radius: 4px;
        }
        .pagination {
            margin: 20px 0;
            padding: 10px;
            text-align: center;
        }
        .pagination button {
            margin: 0 5px;
            padding: 5px 10px;
            cursor: pointer;
        }
        .pagination button.active {
            background-color: #4CAF50;
            color: white;
            border: 1px solid #4CAF50;
        }
        .pagination button:hover:not(.active) {
            background-color: #ddd;
        }
        .database-section {
            margin-bottom: 40px;
            border: 1px solid #ddd;
            padding: 20px;
            border-radius: 5px;
        }
        .database-section h2 {
            margin-top: 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #4CAF50;
        }
        .tab {
            overflow: hidden;
            border: 1px solid #ccc;
            background-color: #f1f1f1;
            margin-top: 20px;
        }
        .tab button {
            background-color: inherit;
            float: left;
            border: none;
            outline: none;
            cursor: pointer;
            padding: 14px 16px;
            transition: 0.3s;
            font-size: 16px;
        }
        .tab button:hover {
            background-color: #ddd;
        }
        .tab button.active {
            background-color: #4CAF50;
            color: white;
        }
        .tabcontent {
            display: none;
            padding: 6px 12px;
            border: 1px solid #ccc;
            border-top: none;
        }
        .tabcontent.active {
            display: block;
        }
        
        /* 打印樣式 */
        @media print {
            body * {
                visibility: hidden;
            }
            #printSection, #printSection * {
                visibility: visible;
            }
            #printSection {
                position: absolute;
                left: 0;
                top: 0;
                width: 100%;
            }
            .no-print {
                display: none;
            }
        }
        
        /* 打印預覽對話框樣式 */
        .print-modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.4);
        }
        
        .print-modal-content {
            background-color: #fefefe;
            margin: 15% auto;
            padding: 20px;
            border: 1px solid #888;
            width: 80%;
            max-width: 600px;
        }
        
        .print-modal-close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        
        .print-modal-close:hover {
            color: black;
        }
        
        .print-btn {
            background-color: #4CAF50;
            color: white;
            padding: 5px 10px;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            margin-right: 5px;
        }
        
        .print-btn:hover {
            background-color: #45a049;
        }
        
        .detail-btn {
            background-color: #2196F3;
            color: white;
            padding: 5px 10px;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }
        
        .detail-btn:hover {
            background-color: #0b7dda;
        }
        
        /* Loading indicator styles */
        .loader {
            display: none;
            width: 16px;
            height: 16px;
            border: 2px solid #ffffff;
            border-radius: 50%;
            border-top: 2px solid transparent;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .searching .loader {
            display: block;
        }
        
        .searching .btn-text {
            display: none;
        }
        
        /* Search options styles */
        .search-options {
            margin-top: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 14px;
            color: #666;
        }
        
        .search-options label {
            display: flex;
            align-items: center;
            gap: 5px;
            cursor: pointer;
        }
        
        .search-options input[type="checkbox"] {
            cursor: pointer;
        }
        
        .tooltip {
            position: relative;
            display: inline-block;
            width: 16px;
            height: 16px;
            background-color: #f0f0f0;
            border-radius: 50%;
            text-align: center;
            line-height: 16px;
            cursor: help;
        }
        
        .tooltip:hover::after {
            content: attr(title);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            padding: 5px 10px;
            background-color: #333;
            color: white;
            border-radius: 4px;
            font-size: 12px;
            white-space: nowrap;
            z-index: 1000;
        }
        
        /* Highlight match styles */
        .highlight {
            background-color: #fff176;
            padding: 2px;
            border-radius: 2px;
        }
        
        /* Database Section Styles */
        .database-section {
            margin-bottom: 2rem;
            padding: 1rem;
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .database-section h2 {
            color: #2c3e50;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #eee;
        }
        
        /* Search Container Styles */
        .search-container {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 6px;
            margin-bottom: 1rem;
        }
        
        .search-wrapper {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }
        
        .search-select {
            min-width: 120px;
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: white;
        }
        
        #zerodb_searchInput,
        #zerodev_searchInput {
            flex: 1;
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            transition: border-color 0.2s;
        }
        
        #zerodb_searchInput:focus,
        #zerodev_searchInput:focus {
            border-color: #4CAF50;
            outline: none;
            box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
        }
        
        .search-options {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.9rem;
            color: #666;
        }
        
        .search-options label {
            display: flex;
            align-items: center;
            gap: 0.25rem;
            cursor: pointer;
        }
        
        .search-options input[type="checkbox"] {
            margin: 0;
        }
        
        .tooltip {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background-color: #e0e0e0;
            color: #666;
            font-size: 12px;
            cursor: help;
        }
        
        .tooltip:hover {
            background-color: #666;
            color: white;
        }
        
        .no-results {
            margin-top: 0.5rem;
            padding: 0.5rem;
            border-radius: 4px;
            font-size: 0.9rem;
            display: none;
        }
        
        /* Search Button Styles */
        .search-btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .search-btn:hover {
            background-color: #45a049;
        }
        
        .search-btn.searching {
            background-color: #666;
            cursor: not-allowed;
        }
        
        .loader {
            display: none;
            width: 16px;
            height: 16px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        .searching .loader {
            display: inline-block;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    <script>
    // Global variables
    const ITEMS_PER_PAGE = 50;
    let currentPages = {
        'zerodb': 1,
        'zerodev': 1
    };
    let filteredRows = {
        'zerodb': [],
        'zerodev': []
    };
    let searchTimeout = null;
    let isSearching = false;

    // 確保頁面加載完成後立即執行初始化
    document.addEventListener('DOMContentLoaded', function() {
        console.log('DOM fully loaded, initializing...');
        initializeEventListeners();
        updateDiskSizes();
        
        // Initialize pagination
        ['zerodb', 'zerodev'].forEach(dbName => {
            const table = document.getElementById(dbName + '_systemRecordsTable');
            if (table) {
                filteredRows[dbName] = Array.from(table.getElementsByTagName('tr')).slice(1);
                updatePagination(dbName);
                showPage(dbName, 1);
            }
        });
    });

    // Event Handlers
    function initializeEventListeners() {
        console.log('Initializing event listeners...');
        
        // Print buttons - 直接使用內聯函數處理
        document.querySelectorAll('.print-btn').forEach(btn => {
            btn.addEventListener('click', function(event) {
                event.preventDefault();
                const sn = this.getAttribute('data-sn');
                const time = this.getAttribute('data-time');
                console.log('Print button clicked for SN:', sn, 'Time:', time);
                if (sn && time) {
                    printLabel(sn, time);
                }
            });
        });

        // Details buttons - 直接使用內聯函數處理
        document.querySelectorAll('.detail-btn').forEach(btn => {
            btn.addEventListener('click', function(event) {
                event.preventDefault();
                const sn = this.getAttribute('data-sn');
                console.log('Detail button clicked for SN:', sn);
                if (sn) {
                    viewDetails(sn);
                }
            });
        });

        // Modal close button
    const modal = document.getElementById('printModal');
    const closeBtn = document.getElementsByClassName('print-modal-close')[0];
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
        modal.style.display = "none";
            });
    }
    
        // Click outside modal to close
        window.addEventListener('click', function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
        });
        
        // 打印預覽對話框中的打印按鈕
        const doPrintBtn = document.getElementById('doPrintBtn');
        if (doPrintBtn) {
            doPrintBtn.addEventListener('click', function(event) {
                event.preventDefault();
                console.log('Print preview button clicked');
                doPrint();
            });
        }

        // Search functionality
        const searchInput = document.getElementById('zerodb_searchInput');
        const searchType = document.getElementById('zerodb_searchType');
        const fuzzySearchCheckbox = document.getElementById('zerodb_fuzzySearch');
        const searchBtn = document.getElementById('zerodb_searchBtn');
        
        console.log('Search elements found:', {
            searchInput: !!searchInput,
            searchType: !!searchType,
            fuzzySearchCheckbox: !!fuzzySearchCheckbox,
            searchBtn: !!searchBtn
        });
        
        if (searchInput && searchType && fuzzySearchCheckbox && searchBtn) {
            console.log('Binding search events...');
            
            // Input event with debounce
            searchInput.addEventListener('input', function() {
                console.log('Search input changed');
                if (searchTimeout) {
                    clearTimeout(searchTimeout);
                }
                searchTimeout = setTimeout(performSearch, 300);
            });
            
            // Change events
            searchType.addEventListener('change', function() {
                console.log('Search type changed');
                if (searchInput.value.trim()) {
                    performSearch();
                }
            });
            
            fuzzySearchCheckbox.addEventListener('change', function() {
                console.log('Fuzzy search toggled');
                if (searchInput.value.trim()) {
                    performSearch();
                }
            });
            
            // Enter key event
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    console.log('Enter key pressed');
                    e.preventDefault();
                    if (searchTimeout) {
                        clearTimeout(searchTimeout);
                    }
                    performSearch();
                }
            });
            
            // Search button click event
            searchBtn.addEventListener('click', function(e) {
                console.log('Search button clicked');
                e.preventDefault();
                if (searchTimeout) {
                    clearTimeout(searchTimeout);
                }
                performSearch();
            });
            
            console.log('Search events bound successfully');
        } else {
            console.error('Some search elements are missing');
        }
    }

    // Print Label Function
    function printLabel(serialNumber, timestamp) {
        console.log('Printing label for SN:', serialNumber, 'Time:', timestamp);
        
        // Disable all print buttons for this serial number
        const printButtons = document.querySelectorAll('.print-btn');
        printButtons.forEach(btn => {
            if (btn.getAttribute('data-sn') === serialNumber) {
                btn.disabled = true;
                btn.style.opacity = '0.5';
            }
        });
        
        // Send print request
        fetch(`/print_label/${serialNumber}?timestamp=${timestamp}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + btoa('share:share')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Label printed successfully');
            } else {
                alert('Failed to print label: ' + (data.message || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error printing label: ' + error.message);
        })
        .finally(() => {
            // Re-enable buttons after 1 minute
            setTimeout(() => {
                printButtons.forEach(btn => {
                    if (btn.getAttribute('data-sn') === serialNumber) {
                        btn.disabled = false;
                        btn.style.opacity = '1';
                    }
                });
            }, 60000);
        });
    }

    // View Details Function
    function viewDetails(serialNumber) {
        console.log('Viewing details for SN:', serialNumber);
        const row = document.querySelector(`tr[data-sn="${serialNumber}"]`);
        if (!row) {
            console.error('Row not found for SN:', serialNumber);
            return;
        }

        // 從行屬性中獲取電池數據（優先使用）
        const designCapacity = row.getAttribute('data-design-capacity') || row.cells[12].textContent;
        const fullCapacity = row.getAttribute('data-full-capacity') || row.cells[13].textContent;
        const cycleCount = row.getAttribute('data-cycle-count') || row.cells[14].textContent;
        const batteryHealth = row.getAttribute('data-battery-health') || row.cells[15].textContent;
        
        // 使用已經被正確格式化的表格數據
        const data = {
            'SN': row.cells[0].textContent || 'N/A',
            'Brand': row.cells[2].textContent || 'N/A',
            'Model': row.cells[3].textContent || 'N/A',
            'SKU': row.cells[4].textContent || 'N/A',
            'OS': row.cells[5].textContent || 'N/A',
            'CPU': row.cells[6].textContent || 'N/A',
            'Resolution': row.cells[7].textContent || 'N/A',
            'GPU': row.cells[8].textContent || 'N/A',
            'Touch Screen': row.cells[9].textContent || 'N/A',
            'RAM': row.cells[10].textContent || 'N/A',
            'Disk': row.cells[11].textContent || 'N/A',
            'Design Capacity': designCapacity,
            'Full Capacity': fullCapacity,
            'Cycle Count': cycleCount,
            'Battery Health': batteryHealth,
            'Created': row.cells[16].textContent || 'N/A'
        };

        let previewHtml = '<div style="font-family: Arial, sans-serif; padding: 20px;">';
        for (const [key, value] of Object.entries(data)) {
            // 確保不顯示 'N/A'，使用格式化後的值
            previewHtml += `<p style="margin: 5px 0; font-size: 12px;"><strong>${key}:</strong> ${value}</p>`;
        }
        
        previewHtml += '</div>';

        const printSection = document.getElementById('printSection');
        printSection.innerHTML = previewHtml;

        const modal = document.getElementById('printModal');
        modal.style.display = 'block';
    }

    // Print Function
    function doPrint() {
        const printContent = document.getElementById('printSection');
        const originalContents = document.body.innerHTML;
        
        document.body.innerHTML = printContent.innerHTML;
        window.print();
        document.body.innerHTML = originalContents;
        
        // Reinitialize event listeners after printing
        initializeEventListeners();
    }

    // Fuzzy search implementation
    function fuzzyMatch(str, pattern) {
        try {
            // 檢查輸入
            if (!str || !pattern) return false;
            if (typeof str !== 'string' || typeof pattern !== 'string') {
                str = String(str);
                pattern = String(pattern);
            }
            
            // 轉換為小寫進行比較
            str = str.toLowerCase();
            pattern = pattern.toLowerCase();
            
            // 精確匹配檢查
            if (str.includes(pattern)) return true;
            
            // 模糊匹配算法
            let patternIdx = 0;
            let strIdx = 0;
            
            while (strIdx < str.length && patternIdx < pattern.length) {
                if (str[strIdx] === pattern[patternIdx]) {
                    patternIdx++;
                }
                strIdx++;
            }
            
            // 如果模式中的所有字符都被匹配，則返回 true
            return patternIdx === pattern.length;
        } catch (error) {
            console.error('Error in fuzzyMatch:', error);
            return false;
        }
    }

    // Highlight search matches
    function highlightText(text, searchTerm) {
        try {
            if (!text || !searchTerm) return text;
            
            // 簡單的字符串替換方法，避免使用正則表達式
            const textLower = text.toLowerCase();
            const termLower = searchTerm.toLowerCase();
            
            // 如果沒有匹配，直接返回原文本
            if (!textLower.includes(termLower)) {
                return text;
            }
            
            // 使用簡單的字符串操作來高亮顯示匹配項
            let result = '';
            let lastIndex = 0;
            let index = textLower.indexOf(termLower);
            
            while (index !== -1) {
                // 添加匹配前的文本
                result += text.substring(lastIndex, index);
                // 添加高亮的匹配文本（使用原始大小寫）
                result += '<span class="highlight">' + text.substring(index, index + searchTerm.length) + '</span>';
                
                // 更新索引
                lastIndex = index + searchTerm.length;
                index = textLower.indexOf(termLower, lastIndex);
            }
            
            // 添加剩餘文本
            result += text.substring(lastIndex);
            return result;
        } catch (error) {
            console.error('Error in highlightText:', error);
            return text;
        }
    }

    // Perform search function
    function performSearch() {
        try {
            console.log('Starting search...');
            
            // 獲取必要的元素
            const searchInput = document.getElementById('zerodb_searchInput');
            const searchType = document.getElementById('zerodb_searchType');
            const fuzzySearchCheckbox = document.getElementById('zerodb_fuzzySearch');
            const searchBtn = document.getElementById('zerodb_searchBtn');
            const noResultsDiv = document.getElementById('zerodb_noResults');
            const table = document.getElementById('zerodb_systemRecordsTable');
            
            // 檢查必要元素是否存在
            if (!searchInput || !searchType || !table) {
                console.error('Required elements not found');
                return;
            }

            // 獲取搜索參數
            const searchTerm = searchInput.value ? searchInput.value.trim() : '';
            const searchTypeValue = searchType.value || 'sn';
            const searchColumn = {
                'sn': 0,  // Serial Number column index
                'sku': 4, // System SKU column index
                'model': 3 // Model column index
            }[searchTypeValue];
            
            // 如果搜索列不存在，使用默認值
            const finalSearchColumn = (searchColumn !== undefined) ? searchColumn : 0;
            
            console.log('Search parameters:', {
                searchTerm,
                searchType: searchTypeValue,
                searchColumn: finalSearchColumn,
                fuzzySearch: fuzzySearchCheckbox ? fuzzySearchCheckbox.checked : false
            });
            
            // 顯示搜索狀態
            if (searchBtn) searchBtn.classList.add('searching');
            
            // 獲取所有行（除了表頭）
            const rows = Array.from(table.getElementsByTagName('tr') || []).slice(1);
            console.log(`Found ${rows.length} rows to search`);
            
            let matchCount = 0;

            // 處理每一行
            rows.forEach((row, index) => {
                try {
                    // 檢查行是否有足夠的單元格
                    if (!row.cells || row.cells.length <= finalSearchColumn) {
                        console.warn(`Row ${index} has insufficient cells`);
                        return;
                    }
                    
                    const cell = row.cells[finalSearchColumn];
                    if (!cell) {
                        console.warn(`No cell found at column ${finalSearchColumn} for row ${index}`);
                        return;
                    }

                    // 獲取單元格文本
                    const cellText = cell.textContent ? cell.textContent.trim() : '';
                    let isMatch = false;

                    // 根據搜索類型進行匹配
                    if (!searchTerm) {
                        // 空搜索顯示所有結果
                        isMatch = true;
                    } else if (fuzzySearchCheckbox && fuzzySearchCheckbox.checked) {
                        // 模糊搜索
                        isMatch = fuzzyMatch(cellText, searchTerm);
                    } else {
                        // 精確搜索（不區分大小寫）
                        isMatch = cellText.toLowerCase().includes(searchTerm.toLowerCase());
                    }

                    // 根據匹配結果顯示/隱藏行
                    row.style.display = isMatch ? '' : 'none';
                    
                    // 高亮顯示匹配項
                    if (isMatch && searchTerm) {
                        try {
                            cell.innerHTML = highlightText(cellText, searchTerm);
                            matchCount++;
                            console.log(`Match found in row ${index}:`, cellText);
                        } catch (highlightError) {
                            console.error('Error highlighting text:', highlightError);
                            cell.textContent = cellText; // 回退到原始文本
                        }
                    } else {
                        cell.textContent = cellText;
                    }
                } catch (rowError) {
                    console.error(`Error processing row ${index}:`, rowError);
                }
            });

            console.log(`Search completed. Found ${matchCount} matches`);

            // 更新無結果消息
            if (noResultsDiv) {
                noResultsDiv.style.display = matchCount === 0 && searchTerm ? 'block' : 'none';
                noResultsDiv.textContent = `No matching records found for "${searchTerm}"`;
            }

            // 移除搜索狀態
            if (searchBtn) searchBtn.classList.remove('searching');

            // 更新分頁
            filteredRows['zerodb'] = rows.filter(row => row.style.display !== 'none');
            currentPages['zerodb'] = 1;
            updatePagination('zerodb');
            showPage('zerodb', 1);
            
            // 重新初始化事件監聽器，確保按鈕正常工作
            setTimeout(function() {
                initializeEventListeners();
            }, 0);

        } catch (error) {
            console.error('Error in performSearch:', error);
            const searchBtn = document.getElementById('zerodb_searchBtn');
            if (searchBtn) {
                searchBtn.classList.remove('searching');
            }
        }
    }

    function updateDiskSizes() {
        // 這個函數不需要特別處理，因為磁盤數據是文本數據
        console.log('Disk sizes updated');
    }

    function openTab(evt, tabName) {
        var i, tabcontent, tablinks;
        
        // Get all tab content elements in the same database section
        const dbSection = evt.currentTarget.closest('.database-section');
        tabcontent = dbSection.getElementsByClassName("tabcontent");
        for (i = 0; i < tabcontent.length; i++) {
            tabcontent[i].style.display = "none";
            tabcontent[i].classList.remove("active");
        }
        
        // Get all tab buttons in the same database section
        tablinks = dbSection.getElementsByClassName("tablinks");
        for (i = 0; i < tablinks.length; i++) {
            tablinks[i].classList.remove("active");
        }
        
        // Show the selected tab content and mark button as active
        document.getElementById(tabName).style.display = "block";
        document.getElementById(tabName).classList.add("active");
        evt.currentTarget.classList.add("active");
        
        // If switching to System Records tab, update pagination
        if (tabName.endsWith('SystemRecords')) {
            const dbName = tabName.split('_')[0];
            filterAndPaginate(dbName);
        }
    }

    function filterAndPaginate(dbName) {
        const skuSearch = document.getElementById(dbName + '_skuSearch').value.toLowerCase();
        const modelSearch = document.getElementById(dbName + '_modelSearch').value.toLowerCase();
        const table = document.getElementById(dbName + '_systemRecordsTable');
        const rows = Array.from(table.getElementsByTagName('tr')).slice(1); // Skip header row

        // Filter rows
        filteredRows[dbName] = rows.filter(row => {
            const sku = row.cells[4].textContent.toLowerCase();
            const model = row.cells[3].textContent.toLowerCase();
            return sku.includes(skuSearch) && model.includes(modelSearch);
        });

        // Reset to first page when filtering
        currentPages[dbName] = 1;
        updatePagination(dbName);
        showPage(dbName, 1);
    }

    function updatePagination(dbName) {
        const totalPages = Math.ceil(filteredRows[dbName].length / ITEMS_PER_PAGE);
        const pagination = document.getElementById(dbName + '_pagination');
        let html = '';

        // Previous button
        html += `<button onclick="changePage('${dbName}', -1)" ${currentPages[dbName] === 1 ? 'disabled' : ''}>Previous</button>`;

        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            html += `<button onclick="showPage('${dbName}', ${i})" class="${currentPages[dbName] === i ? 'active' : ''}">${i}</button>`;
        }

        // Next button
        html += `<button onclick="changePage('${dbName}', 1)" ${currentPages[dbName] === totalPages ? 'disabled' : ''}>Next</button>`;

        pagination.innerHTML = html;
    }

    function showPage(dbName, page) {
        currentPages[dbName] = page;
        const start = (page - 1) * ITEMS_PER_PAGE;
        const end = start + ITEMS_PER_PAGE;

        // Hide all rows first
        filteredRows[dbName].forEach(row => row.style.display = 'none');

        // Show only rows for current page
        filteredRows[dbName].slice(start, end).forEach(row => row.style.display = '');

        updatePagination(dbName);
    }

    function changePage(dbName, delta) {
        const newPage = currentPages[dbName] + delta;
        const totalPages = Math.ceil(filteredRows[dbName].length / ITEMS_PER_PAGE);
        
        if (newPage >= 1 && newPage <= totalPages) {
            showPage(dbName, newPage);
        }
    }
    </script>
</head>
<body>
    <h1>Database Records Preview</h1>
    <p>Generated at: {{ timestamp }}</p>
    
    <!-- Primary Database (zerodb) Section -->
    <div class="database-section">
        <h2>Primary Database (zerodb)</h2>
        <!-- Search container for zerodb -->
        <div class="search-container">
            <div class="search-wrapper">
                <select id="zerodb_searchType" class="search-select">
                    <option value="sn">Serial Number</option>
                    <option value="sku">System SKU</option>
                    <option value="model">Model</option>
                </select>
                <input type="text" id="zerodb_searchInput" placeholder="Search in Primary Database...">
                <button id="zerodb_searchBtn" class="search-btn">
                    <span class="btn-text">Search</span>
                    <div class="loader"></div>
                </button>
            </div>
            <div class="search-options">
                <label>
                    <input type="checkbox" id="zerodb_fuzzySearch" checked>
                    Enable fuzzy search
                </label>
                <span class="tooltip" title="Fuzzy search will find similar matches. For example, 'lenvo' will match 'Lenovo'">?</span>
            </div>
            <div id="zerodb_noResults" class="no-results">
                No matching records found.
        </div>
    </div>
    
        <div class="tab">
            <button class="tablinks active" onclick="openTab(event, 'zerodb_SystemRecords')">System Records ({{ system_records_count }})</button>
            <button class="tablinks" onclick="openTab(event, 'zerodb_ProductKeys')">Product Keys ({{ product_keys_count }})</button>
        </div>

        <div id="zerodb_SystemRecords" class="tabcontent active">
            <table id="zerodb_systemRecordsTable">
                <thead>
                    <tr>
                        <th>Serial Number</th>
                        <th>Computer Name</th>
                        <th>Manufacturer</th>
                        <th>Model</th>
                        <th>System SKU</th>
                        <th>Operating System</th>
                        <th>CPU</th>
                        <th>Resolution</th>
                        <th>Graphics Card</th>
                        <th>TouchScreen</th>
                        <th>RAM</th>
                        <th>Disks</th>
                        <th>Design Capacity</th>
                        <th>Full Charge Capacity</th>
                        <th>Cycle Count</th>
                        <th>Battery Health</th>
                        <th>Created At</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {{ system_records_pages }}
                </tbody>
            </table>
            <div id="zerodb_pagination" class="pagination"></div>
        </div>

        <div id="zerodb_ProductKeys" class="tabcontent">
            <table id="zerodb_productKeysTable">
                <thead>
                    <tr>
                        <th>Computer Name</th>
                        <th>Windows OS</th>
                        <th>Product Key</th>
                        <th>Created At</th>
                    </tr>
                </thead>
                <tbody>
                    {{ product_keys_pages }}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Development Database (zerodev) Section -->
    <div class="database-section">
        <h2>Development Database (zerodev)</h2>
        <div class="tab">
            <button class="tablinks" onclick="openTab(event, 'zerodev_SystemRecords')">System Records ({{ dev_system_records_count }})</button>
            <button class="tablinks" onclick="openTab(event, 'zerodev_ProductKeys')">Product Keys ({{ dev_product_keys_count }})</button>
        </div>

        <div id="zerodev_SystemRecords" class="tabcontent">
            <table id="zerodev_systemRecordsTable">
                <thead>
                    <tr>
                        <th>Serial Number</th>
                        <th>Computer Name</th>
                        <th>Manufacturer</th>
                        <th>Model</th>
                        <th>System SKU</th>
                        <th>Operating System</th>
                        <th>CPU</th>
                        <th>Resolution</th>
                        <th>Graphics Card</th>
                        <th>TouchScreen</th>
                        <th>RAM</th>
                        <th>Disks</th>
                        <th>Design Capacity</th>
                        <th>Full Charge Capacity</th>
                        <th>Cycle Count</th>
                        <th>Battery Health</th>
                        <th>Created At</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {{ dev_system_records_pages }}
                </tbody>
            </table>
            <div id="zerodev_pagination" class="pagination"></div>
        </div>

        <div id="zerodev_ProductKeys" class="tabcontent">
            <table id="zerodev_productKeysTable">
                <thead>
                    <tr>
                        <th>Computer Name</th>
                        <th>Windows OS</th>
                        <th>Product Key</th>
                        <th>Created At</th>
                    </tr>
                </thead>
                <tbody>
                    {{ dev_product_keys_pages }}
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- 打印預覽對話框 -->
    <div id="printModal" class="print-modal">
        <div class="print-modal-content">
            <span class="print-modal-close">&times;</span>
            <h2>Print Preview</h2>
            <div id="printSection">
                <!-- 打印內容將在這裡動態生成 -->
            </div>
            <button id="doPrintBtn" class="print-btn">Print</button>
        </div>
    </div>
</body>
</html>
"""
        
        # Create Template object
        template = Template(template_content)
        
        # Get current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Constants
        ITEMS_PER_PAGE = 50
        
        # Get data from both databases
        data = {}
        for db_name in ['zerodb', 'zerodev']:
            with Database(db_name=db_name) as db:
                # Get system records
                db.cursor.execute("""
                    SELECT * FROM system_records 
                    ORDER BY created_at DESC, serialnumber
                """)
                system_records = db.cursor.fetchall()
                
                # Get product keys
                db.cursor.execute("""
                    SELECT * FROM product_keys 
                    ORDER BY created_at DESC, computername
                """)
                product_keys = db.cursor.fetchall()
                
                data[db_name] = {
                    'system_records': system_records,
                    'product_keys': product_keys
                }

        # Generate HTML content for both databases
        html_content = template.render(
            timestamp=current_time,
            # Primary database (zerodb)
            system_records_count=len(data['zerodb']['system_records']),
            system_records_pages=generate_records_html(data['zerodb']['system_records']),
            product_keys_count=len(data['zerodb']['product_keys']),
            product_keys_pages=generate_keys_html(data['zerodb']['product_keys']),
            # Development database (zerodev)
            dev_system_records_count=len(data['zerodev']['system_records']),
            dev_system_records_pages=generate_records_html(data['zerodev']['system_records']),
            dev_product_keys_count=len(data['zerodev']['product_keys']),
            dev_product_keys_pages=generate_keys_html(data['zerodev']['product_keys'])
        )
        
        # Write to file
        preview_path = os.path.join(os.path.dirname(__file__), 'preview.html')
        with open(preview_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return preview_path
        
    except Exception as e:
        print(f"Error generating preview: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def get_touchscreen_class(value):
    """Get CSS class for touchscreen value"""
    if not value or pd.isna(value):
        return 'unknown'
    value = str(value).lower()
    if value in ['yes', 'true', '1']:
        return 'yes'
    if value in ['no', 'false', '0']:
        return 'no'
    return 'unknown'

def format_disk_size(disk_json):
    """Format disk size from JSON to readable string"""
    try:
        if disk_json is None or pd.isna(disk_json):
            return 'N/A'

        # 直接返回文本數據，不做特別處理
        return str(disk_json).strip()
    except Exception as e:
        print(f"Error formatting disk size: {str(e)}, value: {disk_json}")
        return str(disk_json) if disk_json else 'N/A'

def format_value(value, field):
    """Format different types of values"""
    if value is None or pd.isna(value):
        return 'N/A'
        
    if field in ['design_capacity', 'full_charge_capacity']:
        # 處理雙電池格式的電池容量
        if isinstance(value, str) and ',' in value:
            # 處理雙電池格式 "44000, 40000"
            capacities = [c.strip() for c in value.split(',')]
            formatted_capacities = []
            for capacity in capacities:
                try:
                    # 嘗試轉換為整數
                    formatted_capacities.append(f"{int(float(capacity))}")
                except (ValueError, TypeError):
                    # 如果無法轉換，保留原始值
                    formatted_capacities.append(capacity)
            return ' / '.join(formatted_capacities)
        else:
            try:
                # 單電池情況，嘗試轉換為整數
                return f"{int(float(value))}"
            except (ValueError, TypeError):
                # 如果無法轉換，返回原始值（避免返回 'N/A'）
                return str(value)
    elif field == 'cycle_count':
        # 處理雙電池格式的循環次數
        if isinstance(value, str) and ',' in value:
            # 處理雙電池格式 "123, 145"
            counts = [c.strip() for c in value.split(',')]
            formatted_counts = []
            for count in counts:
                try:
                    # 嘗試轉換為整數
                    formatted_counts.append(f"{int(float(count))}")
                except (ValueError, TypeError):
                    # 如果無法轉換，保留原始值
                    formatted_counts.append(count)
            return ' / '.join(formatted_counts)
        else:
            try:
                # 單電池情況，嘗試轉換為整數
                return f"{int(float(value))}"
            except (ValueError, TypeError):
                # 如果無法轉換，返回原始值（避免返回 'N/A'）
                return str(value)
    elif field == 'battery_health':
        # 處理雙電池格式的電池健康度
        if isinstance(value, str) and ',' in value:
            # 處理雙電池格式 "75, 80"
            health_values = [h.strip() for h in value.split(',')]
            formatted_health = []
            for health in health_values:
                try:
                    # 嘗試轉換為浮點數，顯示兩位小數和百分比
                    health_float = float(health)
                    # 如果值已經是百分比格式（>1），不進行除法
                    if health_float > 1:
                        formatted_health.append(f"{health_float:.2f}%")
                    else:
                        # 如果是小數（<1），轉換為百分比
                        formatted_health.append(f"{health_float * 100:.2f}%")
                except (ValueError, TypeError):
                    # 如果無法轉換，檢查是否已經包含百分比符號
                    if '%' not in health:
                        formatted_health.append(f"{health}%")
                    else:
                        formatted_health.append(health)
            return ' / '.join(formatted_health)
        else:
            try:
                # 單電池情況，嘗試轉換為浮點數
                health_float = float(value)
                # 如果值已經是百分比格式（>1），不進行除法
                if health_float > 1:
                    return f"{health_float:.2f}%"
                else:
                    # 如果是小數（<1），轉換為百分比
                    return f"{health_float * 100:.2f}%"
            except (ValueError, TypeError):
                # 如果無法轉換，檢查是否已經包含百分比符號
                if '%' not in str(value):
                    return f"{value}%"
                else:
                    return str(value)
    elif field == 'ram_gb':
        try:
            return f"{float(value):.0f}GB"
        except (ValueError, TypeError):
            return str(value)
            
    return str(value)

def generate_records_html(records):
    """Generate HTML table rows for system records"""
    # 使用字典來存儲最新的記錄，只以序列號為鍵
    latest_records = {}
    
    # 只保留每個序列號的最新記錄
    for record in records:
        sn = record['serialnumber']
        # 檢查是否有序列號
        if not sn:
            continue
            
        # 檢查更新時間並保留最新記錄
        if sn not in latest_records or (
            record['created_at'] and 
            latest_records[sn]['created_at'] and 
            record['created_at'] > latest_records[sn]['created_at']
        ):
            latest_records[sn] = record

    # 按更新時間排序（最新的在前）
    sorted_records = sorted(
        latest_records.values(), 
        key=lambda x: x['created_at'] if x['created_at'] else datetime.min, 
        reverse=True
    )

    # 生成HTML
    html = ""
    for record in sorted_records:
        # 格式化時間
        created_time = (record['created_at'].strftime('%Y-%m-%d %H:%M:%S') 
                       if record['created_at'] else 'N/A')
        
        # 直接使用原始電池欄位數據
        design_capacity = record['design_capacity']
        full_charge_capacity = record['full_charge_capacity']
        cycle_count = record['cycle_count']
        battery_health = record['battery_health']
        
        html += f"""
        <tr data-sn="{record['serialnumber']}"
            data-design-capacity="{design_capacity if design_capacity is not None else ''}"
            data-full-capacity="{full_charge_capacity if full_charge_capacity is not None else ''}"
            data-cycle-count="{cycle_count if cycle_count is not None else ''}"
            data-battery-health="{battery_health if battery_health is not None else ''}">
            <td>{format_value(record['serialnumber'], 'serialnumber')}</td>
            <td>{format_value(record['computername'], 'computername')}</td>
            <td>{format_value(record['manufacturer'], 'manufacturer')}</td>
            <td>{format_value(record['model'], 'model')}</td>
            <td>{format_value(record['systemsku'], 'systemsku')}</td>
            <td>{format_value(record['operatingsystem'], 'operatingsystem')}</td>
            <td>{format_value(record['cpu'], 'cpu')}</td>
            <td>{format_value(record['resolution'], 'resolution')}</td>
            <td>{format_value(record['graphicscard'], 'graphicscard')}</td>
            <td class="{get_touchscreen_class(record['touchscreen'])}">{format_value(record['touchscreen'], 'touchscreen')}</td>
            <td>{format_value(record['ram_gb'], 'ram_gb')}</td>
            <td data-disk-size="{record['disks']}">{record['disks']}</td>
            <td>{format_value(design_capacity, 'design_capacity')}</td>
            <td>{format_value(full_charge_capacity, 'full_charge_capacity')}</td>
            <td>{format_value(cycle_count, 'cycle_count')}</td>
            <td>{format_value(battery_health, 'battery_health')}</td>
            <td>{created_time}</td>
            <td>
                <button class="print-btn" 
                        data-sn="{record['serialnumber']}" 
                        data-time="{created_time}">Print</button>
                <button class="detail-btn"
                        data-sn="{record['serialnumber']}">Details</button>
            </td>
        </tr>
        """
    return html

def generate_keys_html(records):
    """Generate HTML table rows for product keys"""
    html = ""
    for record in records:
        html += f"""
        <tr>
            <td>{record['computername']}</td>
            <td>{record['windowsos_new']}</td>
            <td>{record['productkey_new']}</td>
            <td>{record['created_at'].strftime('%Y-%m-%d %H:%M:%S') if record['created_at'] else ''}</td>
        </tr>
        """
    return html

if __name__ == '__main__':
    app.run(port=5000)