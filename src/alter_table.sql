-- Drop existing backup table if exists
DROP TABLE IF EXISTS system_records_backup;

-- Backup the table first
CREATE TABLE system_records_backup AS SELECT * FROM system_records;

-- Add new columns if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_records' AND column_name = 'outbound_status') THEN
        ALTER TABLE system_records ADD COLUMN outbound_status VARCHAR(20);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_records' AND column_name = 'disks_gb') THEN
        ALTER TABLE system_records ADD COLUMN disks_gb NUMERIC;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_records' AND column_name = 'last_updated_at') THEN
        ALTER TABLE system_records ADD COLUMN last_updated_at TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_records' AND column_name = 'data_source') THEN
        ALTER TABLE system_records ADD COLUMN data_source VARCHAR(255);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_records' AND column_name = 'validation_status') THEN
        ALTER TABLE system_records ADD COLUMN validation_status VARCHAR(255);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_records' AND column_name = 'validation_message') THEN
        ALTER TABLE system_records ADD COLUMN validation_message TEXT;
    END IF;
END $$;

-- Handle NaN values before conversion
UPDATE system_records 
SET design_capacity = 0 
WHERE design_capacity IS NOT NULL 
AND design_capacity::TEXT = 'NaN';

UPDATE system_records 
SET full_charge_capacity = 0 
WHERE full_charge_capacity IS NOT NULL 
AND full_charge_capacity::TEXT = 'NaN';

UPDATE system_records 
SET cycle_count = 0 
WHERE cycle_count IS NOT NULL 
AND cycle_count::TEXT = 'NaN';

-- Modify existing columns
ALTER TABLE system_records
    ALTER COLUMN design_capacity TYPE BIGINT USING CASE 
        WHEN design_capacity IS NULL THEN 0 
        ELSE design_capacity::BIGINT 
    END,
    ALTER COLUMN full_charge_capacity TYPE BIGINT USING CASE 
        WHEN full_charge_capacity IS NULL THEN 0 
        ELSE full_charge_capacity::BIGINT 
    END,
    ALTER COLUMN cycle_count TYPE BIGINT USING CASE 
        WHEN cycle_count IS NULL THEN 0 
        ELSE cycle_count::BIGINT 
    END;

-- Handle sync_version conversion separately
-- Add temporary column
ALTER TABLE system_records ADD COLUMN sync_version_new VARCHAR(255);

-- Update the new column
UPDATE system_records 
SET sync_version_new = CASE 
    WHEN sync_version IS NULL THEN '1.0'
    ELSE sync_version::TEXT
END;

-- Drop the old column
ALTER TABLE system_records DROP COLUMN sync_version;

-- Rename the new column
ALTER TABLE system_records RENAME COLUMN sync_version_new TO sync_version;

-- Update default values
ALTER TABLE system_records
    ALTER COLUMN ram_gb DROP DEFAULT,
    ALTER COLUMN design_capacity DROP DEFAULT,
    ALTER COLUMN full_charge_capacity DROP DEFAULT,
    ALTER COLUMN cycle_count DROP DEFAULT,
    ALTER COLUMN battery_health DROP DEFAULT;

-- Set outbound_status default value
UPDATE system_records SET outbound_status = 'available' WHERE outbound_status IS NULL; 