-- 向上遷移
BEGIN;

-- 修改 sync_version 列的類型
ALTER TABLE system_records
    ALTER COLUMN sync_version TYPE VARCHAR(10);

-- 更新現有記錄的版本號
UPDATE system_records
SET sync_version = '1.0'
WHERE sync_version = '1';

COMMIT;

-- 向下遷移
BEGIN;

-- 將 sync_version 列的類型改回 INTEGER
ALTER TABLE system_records
    ALTER COLUMN sync_version TYPE INTEGER
    USING (CASE 
        WHEN sync_version = '1.0' THEN 1
        ELSE CAST(sync_version AS INTEGER)
    END);

COMMIT; 