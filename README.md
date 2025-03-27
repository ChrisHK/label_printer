# Label Printer Application

A comprehensive label printing system for managing and printing system information labels with barcode support.

## Features

### 1. Label Printing
- Automatic label printing for new system records
- Support for reprinting existing labels
- Barcode generation for serial numbers
- Customizable label layout and formatting
- Print rate limiting (1-minute cooldown between prints)
- Print logging and history tracking

### 2. Data Management
- CSV file monitoring and processing
- Automatic database synchronization
- Support for multiple database connections
- Data validation and error handling
- Record deduplication

### 3. API Integration
- Automatic API uploads for new records
- API retry mechanism for failed uploads
- Configurable API endpoints and authentication
- Error handling and logging for API operations

### 4. Web Interface
- HTML preview generation
- Real-time data updates
- Search and filter functionality
- Label reprint interface
- Basic authentication protection

### 5. System Information Tracking
- Comprehensive system details capture:
  - Serial Number
  - Manufacturer/Brand
  - Model
  - System SKU
  - Operating System
  - CPU
  - Graphics Card
  - RAM
  - Disk Information
  - Battery Information (Capacity, Health, Cycle Count)
  - Touch Screen Status
  - Timestamps

## Technical Requirements

- Python 3.x
- Adobe Acrobat (for PDF printing)
- Windows OS (for printer integration)
- Required Python packages:
  - Flask
  - pandas
  - reportlab
  - win32print
  - jinja2
  - flask-cors
  - flask-basicauth

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd label_printer
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Configure your environment:
   - Set up your database connections
   - Configure API credentials
   - Set up printer settings

## Usage

### Command Line Tools

1. **CSV Sync Manager**
```bash
python src/csv_sync_manager.py [options]
```
Options:
- `--sync`: Execute synchronization
- `--check`: Check sync status
- `--clean`: Clean sync logs
- `--status`: Display sync status

2. **API Upload Retry Tool**
```bash
python src/retry_api_uploads.py [options]
```
Options:
- `--days N`: Find failed uploads from last N days
- `--list`: List all failed uploads
- `--retry`: Retry all pending failed uploads
- `--retry-id ID`: Retry specific upload ID
- `--mark-resolved ID`: Mark specific ID as resolved
- `--max-retries N`: Set max retries per record

3. **Label Printer**
```bash
python src/print_label_html.py [options]
```
Options:
- `--id ID`: Print label for specific ID
- `--batch`: Batch print labels
- `--preview`: Preview label

### Web Interface

1. Start the web server:
```bash
python src/app.py
```

2. Access the web interface at `http://localhost:5000`
3. Use the interface to:
   - View system records
   - Search and filter data
   - Reprint labels
   - Monitor sync status

## Security

- Basic authentication for web interface
- API authentication support
- Secure database connections
- Input validation and sanitization

## Error Handling

- Comprehensive error logging
- Automatic retry mechanisms
- User-friendly error messages
- Transaction rollback support

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

[Your License Here]

## Support

For support, please contact [Your Contact Information] 