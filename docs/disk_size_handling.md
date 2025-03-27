# Disk Size Handling Guide

This document outlines the methods for handling disk size data in both Python and Node.js implementations.

## Data Structure

The disk size data is stored in JSON format:
```json
[
  {"size_gb": "512.0"},
  {"size_gb": "1024.0"}
]
```

## Python Implementation

### 1. Data Storage Logic

```python
def process_disk_data(disk_input):
    """Convert input disk string to JSON format"""
    disks_data = []
    if isinstance(disk_input, str):
        # Handle comma-separated input
        for disk in disk_input.split(','):
            disk = disk.strip()
            if disk:
                # Remove unit suffixes if present
                size = disk.upper().replace('GB', '').replace('TB', '').strip()
                disks_data.append({'size_gb': size})
    return json.dumps(disks_data)

# Usage example:
disk_str = "512GB, 1TB"
json_data = process_disk_data(disk_str)
```

### 2. Display Logic

```python
def format_disk_size(disk_json):
    """Format disk size from JSON to readable string"""
    try:
        # Parse JSON string if needed
        if isinstance(disk_json, str):
            try:
                disks = json.loads(disk_json)
            except json.JSONDecodeError:
                return disk_json.strip()
        else:
            disks = disk_json

        # Process disk list
        if isinstance(disks, list):
            total_size = 0
            for disk in disks:
                if isinstance(disk, dict) and 'size_gb' in disk:
                    try:
                        size_str = str(disk['size_gb']).replace('GB', '').replace('TB', '').strip()
                        total_size += float(size_str)
                    except ValueError:
                        continue

            # Choose appropriate unit
            if total_size >= 1024:
                return f"{int(total_size/1024)}TB"
            return f"{int(total_size)}GB"

        return 'N/A'
    except Exception as e:
        print(f"Error formatting disk size: {str(e)}, value: {disk_json}")
        return str(disk_json) if disk_json else 'N/A'

# Usage example:
disk_json = '[{"size_gb": "512.0"}, {"size_gb": "1024.0"}]'
formatted_size = format_disk_size(disk_json)  # Output: "1536GB" or "1.5TB"
```

### 3. Duplicate Handling

```python
def check_duplicate(db_cursor, serial_number, timestamp):
    """Check for duplicate records"""
    db_cursor.execute("""
        SELECT id FROM system_records 
        WHERE serialnumber = %(serialnumber)s 
        AND created_at = %(created_at)s
    """, {
        'serialnumber': serial_number,
        'created_at': timestamp
    })
    return db_cursor.fetchone() is not None

# Usage example:
is_duplicate = check_duplicate(cursor, "ABC123", "2024-02-24 13:51:00")
```

## Node.js Implementation

### 1. Data Storage Logic

```javascript
function processDiskData(diskInput) {
  const disksData = [];
  
  if (typeof diskInput === 'string') {
    // Handle comma-separated input
    diskInput.split(',').forEach(disk => {
      const trimmed = disk.trim();
      if (trimmed) {
        // Remove unit suffixes if present
        const size = trimmed.toUpperCase()
          .replace('GB', '')
          .replace('TB', '')
          .trim();
        disksData.push({ size_gb: size });
      }
    });
  }
  
  return JSON.stringify(disksData);
}

// Usage example:
const diskStr = "512GB, 1TB";
const jsonData = processDiskData(diskStr);
```

### 2. Display Logic

```javascript
function formatDiskSize(diskJson) {
  try {
    // Parse JSON string if needed
    const disks = typeof diskJson === 'string' 
      ? JSON.parse(diskJson) 
      : diskJson;

    if (Array.isArray(disks)) {
      let totalSize = 0;
      
      disks.forEach(disk => {
        if (disk && typeof disk === 'object' && 'size_gb' in disk) {
          const sizeStr = String(disk.size_gb)
            .replace('GB', '')
            .replace('TB', '')
            .trim();
          totalSize += parseFloat(sizeStr) || 0;
        }
      });

      // Choose appropriate unit
      if (totalSize >= 1024) {
        return `${Math.floor(totalSize/1024)}TB`;
      }
      return `${Math.floor(totalSize)}GB`;
    }

    return 'N/A';
  } catch (error) {
    console.error(`Error formatting disk size: ${error.message}`, diskJson);
    return diskJson ? String(diskJson) : 'N/A';
  }
}

// Usage example:
const diskJson = '[{"size_gb": "512.0"}, {"size_gb": "1024.0"}]';
const formattedSize = formatDiskSize(diskJson); // Output: "1536GB" or "1.5TB"
```

### 3. Duplicate Handling

```javascript
async function checkDuplicate(pool, serialNumber, timestamp) {
  try {
    const query = `
      SELECT id FROM system_records 
      WHERE serialnumber = $1 
      AND created_at = $2
    `;
    
    const result = await pool.query(query, [serialNumber, timestamp]);
    return result.rows.length > 0;
  } catch (error) {
    console.error('Error checking duplicate:', error);
    throw error;
  }
}

// Usage example with async/await:
try {
  const isDuplicate = await checkDuplicate(pool, "ABC123", "2024-02-24 13:51:00");
  if (isDuplicate) {
    console.log("Record already exists");
  }
} catch (error) {
  console.error("Error:", error);
}
```

## Database Schema

```sql
CREATE TABLE system_records (
    id SERIAL PRIMARY KEY,
    serialnumber VARCHAR(100),
    disks TEXT,  -- Stores JSON array of disk sizes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- other fields...
    CONSTRAINT unique_record UNIQUE (serialnumber, created_at)
);
```

## Best Practices

1. **Data Validation**
   - Always validate input data format
   - Handle missing or malformed values gracefully
   - Convert units consistently (standardize to GB)

2. **Error Handling**
   - Implement comprehensive error handling
   - Log errors with meaningful messages
   - Provide fallback values when formatting fails

3. **Performance**
   - Use database indexes for duplicate checking
   - Cache formatted results when possible
   - Use prepared statements for database queries

4. **Maintenance**
   - Keep JSON schema consistent
   - Document any changes to data format
   - Regular cleanup of duplicate/outdated records

## Common Issues and Solutions

1. **Inconsistent Units**
   ```javascript
   // Convert TB to GB if needed
   function normalizeToGB(size, unit) {
     if (unit.toUpperCase() === 'TB') {
       return size * 1024;
     }
     return size;
   }
   ```

2. **Decimal Point Handling**
   ```javascript
   // Round to nearest integer for display
   function roundSize(size) {
     return Math.floor(size);
   }
   ```

3. **Invalid JSON Data**
   ```javascript
   function safeParse(jsonString) {
     try {
       return JSON.parse(jsonString);
     } catch {
       return [];
     }
   }
   ``` 