import json
import hashlib

# The exact items array from the user's request
items_json = '[{"serialnumber":"TEST123","computername":"TEST-PC-1","manufacturer":"Dell","model":"Latitude 5420","ram_gb":16,"disks":[{"size_gb":512}],"battery":{"design_capacity":6000,"cycle_count":50,"health":98}}]'
print(f"JSON string: {items_json}")

# Calculate checksum
checksum = hashlib.sha256(items_json.encode('utf-8')).hexdigest()
print(f"\nCalculated checksum: {checksum}")

# Print complete request body
body = {
    "source": "test",
    "timestamp": "2024-03-22T08:30:00.000Z",
    "batch_id": "TEST_001",
    "items": json.loads(items_json),
    "metadata": {
        "total_items": 1,
        "version": "1.0",
        "checksum": checksum
    }
}

print("\nComplete request body:")
print(json.dumps(body, indent=2)) 