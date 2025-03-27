# Create test items
$items = @(
    @{
        serialnumber = 'TEST123'
        manufacturer = 'Dell'
        ram_gb = 16
        model = 'Latitude 5420'
        disks = @(@{size_gb = 512})
        battery = @{
            cycle_count = 50
            design_capacity = 6000
            health = 98
        }
        computername = 'TEST-PC-1'
    }
)

# Convert to JSON
$itemsJson = ConvertTo-Json -InputObject $items -Compress
Write-Host "JSON string:"
Write-Host $itemsJson

# Calculate checksum
$stringAsStream = [System.IO.MemoryStream]::new([System.Text.Encoding]::UTF8.GetBytes($itemsJson))
$sha256 = [System.Security.Cryptography.SHA256]::Create()
$hash = $sha256.ComputeHash($stringAsStream)
$checksum = [System.BitConverter]::ToString($hash).Replace("-", "").ToLower()

Write-Host "`nCalculated checksum:"
Write-Host $checksum

# Create complete request body
$body = @{
    source = "test"
    timestamp = "2024-03-22T08:30:00.000Z"
    batch_id = "TEST_001"
    items = $items
    metadata = @{
        total_items = 1
        version = "1.0"
        checksum = $checksum
    }
}

Write-Host "`nComplete request body:"
$bodyJson = ConvertTo-Json -InputObject $body -Depth 10
Write-Host $bodyJson 