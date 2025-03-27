-- 將 system_records 表中的電池相關欄位型態更改為 TEXT
-- 這樣可以直接存儲雙電池格式的數據，如 "44000, 40000"

-- 處理 zerodb 數據庫

-- 將 design_capacity 從 BIGINT 改為 TEXT
ALTER TABLE system_records ALTER COLUMN design_capacity TYPE TEXT;

-- 將 full_charge_capacity 從 BIGINT 改為 TEXT
ALTER TABLE system_records ALTER COLUMN full_charge_capacity TYPE TEXT;

-- 將 cycle_count 從 BIGINT 改為 TEXT
ALTER TABLE system_records ALTER COLUMN cycle_count TYPE TEXT;

-- 將 battery_health 從 DOUBLE PRECISION 改為 TEXT
ALTER TABLE system_records ALTER COLUMN battery_health TYPE TEXT;

-- 處理 zerodev 數據庫
-- 注意：需要在 zerodev 數據庫執行以下語句
-- 若是命令行，可使用：psql -d zerodev -f alter_battery_columns.sql

-- 將 design_capacity 從 BIGINT 改為 TEXT
ALTER TABLE system_records ALTER COLUMN design_capacity TYPE TEXT;

-- 將 full_charge_capacity 從 BIGINT 改為 TEXT
ALTER TABLE system_records ALTER COLUMN full_charge_capacity TYPE TEXT;

-- 將 cycle_count 從 BIGINT 改為 TEXT
ALTER TABLE system_records ALTER COLUMN cycle_count TYPE TEXT;

-- 將 battery_health 從 DOUBLE PRECISION 改為 TEXT
ALTER TABLE system_records ALTER COLUMN battery_health TYPE TEXT; 