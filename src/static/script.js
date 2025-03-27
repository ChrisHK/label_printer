function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    document.getElementById(tabName).classList.add('active');
    document.querySelector(`button[onclick="showTab('${tabName}')"]`).classList.add('active');
}

function performSearch() {
    const searchField = document.getElementById('searchField').value;
    const searchText = document.getElementById('searchInput').value.toLowerCase();
    const table = document.querySelector('.tab-content.active table');
    const rows = table.getElementsByTagName('tr');
    let visibleCount = 0;
    
    // 從第二行開始（跳過表頭）
    for (let i = 1; i < rows.length; i++) {
        const row = rows[i];
        const cell = row.querySelector(`td:nth-child(${getColumnIndex(searchField)})`);
        
        if (cell) {
            const text = cell.textContent.toLowerCase();
            if (text.includes(searchText)) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        }
    }
    
    // 更新記錄計數
    const summary = document.querySelector('.summary');
    const totalRecords = table.getAttribute('data-total-records');
    summary.textContent = `Total records: ${totalRecords} (Showing: ${visibleCount})`;
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    const table = document.querySelector('.tab-content.active table');
    const rows = table.getElementsByTagName('tr');
    
    // 顯示所有行
    for (let i = 1; i < rows.length; i++) {
        rows[i].style.display = '';
    }
    
    // 重置記錄計數
    const summary = document.querySelector('.summary');
    const totalRecords = table.getAttribute('data-total-records');
    summary.textContent = `Total records: ${totalRecords} (CSV records: ${totalRecords})`;
}

function getColumnIndex(field) {
    const columns = {
        'serialnumber': 1,
        'computername': 2,
        'manufacturer': 3,
        'model': 4,
        'operatingsystem': 6
    };
    return columns[field] || 1;
}

// 添加回車鍵搜索功能
document.getElementById('searchInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        performSearch();
    }
});

// 打印標籤功能
async function reprintLabel(serialNumber) {
    try {
        const response = await fetch('http://127.0.0.1:5000/reprint_label', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + btoa('share:share')
            },
            body: JSON.stringify({ serial_number: serialNumber })
        });

        const result = await response.json();
        
        if (result.success) {
            alert(`Label for SN: ${serialNumber} has been sent to printer`);
        } else {
            alert(`Failed to print label: ${result.error}`);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to send print request. Please ensure the server is running.');
    }
}

// Auto refresh every 30 seconds
setInterval(() => { location.reload(); }, 30000);

function showPage(pageNum) {
    const pages = document.querySelectorAll('#system-records .page');
    const buttons = document.querySelectorAll('#system-records .page-btn');
    
    pages.forEach(page => {
        if (page.getAttribute('data-page') == pageNum) {
            page.style.display = 'table-row-group';
        } else {
            page.style.display = 'none';
        }
    });
    
    buttons.forEach(btn => {
        if (btn.getAttribute('data-page') == pageNum) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

function showKeyPage(pageNum) {
    const pages = document.querySelectorAll('#product-keys .page');
    const buttons = document.querySelectorAll('#product-keys .page-btn');
    
    pages.forEach(page => {
        if (page.getAttribute('data-page') == pageNum) {
            page.style.display = 'table-row-group';
        } else {
            page.style.display = 'none';
        }
    });
    
    buttons.forEach(btn => {
        if (btn.getAttribute('data-page') == pageNum) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// 初始化顯示第一頁
document.addEventListener('DOMContentLoaded', function() {
    showPage(1);
    showKeyPage(1);
}); 