# Checksum Calculation Specification

## Overview
This document specifies the checksum calculation method for inventory data synchronization.

## Input Data Format
The input data should be an array of inventory items. Each item contains the following fields:

```json
[{
  "serialnumber": "TEST123",
  "computername": "TEST-PC-1", 
  "manufacturer": "Dell",
  "model": "Latitude 5420",
  "ram_gb": 16,
  "disks": [{"size_gb": 512}],
  "battery": {
    "cycle_count": 50,
    "design_capacity": 6000,
    "health": 98
  }
}]
```

## Calculation Steps

1. Sort items by `serialnumber`

2. For each item, extract and format required fields:
   - All numeric values should be converted to float
   - All string values should be kept as is
   - Sort `disks` array by `size_gb`

3. Required fields and their types:
```json
{
  "battery": {
    "cycle_count": float,
    "design_capacity": float,
    "health": float
  },
  "disks": [
    {
      "size_gb": float
    }
  ],
  "manufacturer": string,
  "model": string,
  "ram_gb": float,
  "serialnumber": string
}
```

4. JSON Serialization:
   - Use `json.dumps()` with `separators=(',', ':')`
   - No whitespace
   - UTF-8 encoding
   - Field order must be exactly as shown above

5. Calculate SHA-256 hash of the serialized string

## Example

### Input Data
```json
[{
  "serialnumber": "TEST123",
  "computername": "TEST-PC-1", 
  "manufacturer": "Dell",
  "model": "Latitude 5420",
  "ram_gb": 16,
  "disks": [{"size_gb": 512}],
  "battery": {
    "cycle_count": 50,
    "design_capacity": 6000,
    "health": 98
  }
}]
```

### Normalized JSON String
```json
[{"battery":{"cycle_count":50.0,"design_capacity":6000.0,"health":98.0},"disks":[{"size_gb":512.0}],"manufacturer":"Dell","model":"Latitude 5420","ram_gb":16.0,"serialnumber":"TEST123"}]
```

### Resulting Checksum
```
044fb0a54927680111e2de595f181e22246c682fa1c13a43f1c1c82ca0bf87d5
```

## Implementation Notes

1. Field Order:
   - Fields must be in alphabetical order
   - Nested objects must also maintain alphabetical order

2. Number Formatting:
   - All numbers should be converted to float
   - Use `.0` for whole numbers (e.g., `50` becomes `50.0`)

3. String Values:
   - Keep original case
   - No trimming
   - UTF-8 encoding

4. Array Handling:
   - `disks` array must be sorted by `size_gb`
   - Each disk object should only contain `size_gb` field

5. Error Handling:
   - Missing fields should raise an error
   - Invalid numeric values should raise an error
   - Invalid field types should raise an error

## Code Example (Python)

```python
import json
import hashlib

def calculate_checksum(items):
    # Sort items by serialnumber
    sorted_items = sorted(items, key=lambda x: x['serialnumber'])
    
    # Prepare checksum data
    checksum_items = []
    for item in sorted_items:
        # Format disks array
        disks = []
        for disk in item['disks']:
            disk_obj = {
                'size_gb': float(disk.get('size_gb', 0))
            }
            disks.append(disk_obj)
        
        # Sort disks by size_gb
        disks.sort(key=lambda x: x['size_gb'])
        
        # Build checksum item
        checksum_item = {
            'battery': {
                'cycle_count': float(item['cycle_count']),
                'design_capacity': float(item['design_capacity']),
                'health': float(item['battery_health'])
            },
            'disks': disks,
            'manufacturer': str(item['manufacturer']),
            'model': str(item['model']),
            'ram_gb': float(item['ram_gb']),
            'serialnumber': str(item['serialnumber'])
        }
        checksum_items.append(checksum_item)
    
    # Convert to JSON string
    json_str = json.dumps(checksum_items, separators=(',', ':'))
    
    # Calculate SHA-256
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
``` 