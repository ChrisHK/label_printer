-- 向上遷移
BEGIN;

-- 修改 sync_version 列的類型
ALTER TABLE system_records
    ALTER COLUMN sync_version TYPE NUMERIC USING sync_version::numeric;

-- 更新現有記錄的版本號
UPDATE system_records
SET sync_version = 1.0
WHERE sync_version = 1;

-- 設置默認值
ALTER TABLE system_records
    ALTER COLUMN sync_version SET DEFAULT 1.0;

-- 添加檢查約束確保數值有效
ALTER TABLE system_records
    ADD CONSTRAINT check_sync_version_positive CHECK (sync_version >= 0);

COMMIT;

-- 向下遷移
BEGIN;

-- 移除檢查約束
ALTER TABLE system_records
    DROP CONSTRAINT IF EXISTS check_sync_version_positive;

-- 將 sync_version 列的類型改回 INTEGER
ALTER TABLE system_records
    ALTER COLUMN sync_version TYPE INTEGER
    USING (CASE 
        WHEN sync_version = 1.0 THEN 1
        ELSE CAST(sync_version AS INTEGER)
    END);

-- 恢復默認值
ALTER TABLE system_records
    ALTER COLUMN sync_version SET DEFAULT 1;

COMMIT; 