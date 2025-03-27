-- 向上遷移：創建處理日誌相關表
-- ------------------------------------------------------------

-- 1. 創建處理日誌表
CREATE TABLE IF NOT EXISTS processing_logs (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(100) NOT NULL,
    source VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_items INTEGER DEFAULT 0,
    processed_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    errors JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    checksum VARCHAR(64)
);

-- 2. 創建處理日誌歸檔表
CREATE TABLE IF NOT EXISTS processing_logs_archive (
    id SERIAL PRIMARY KEY,
    original_id INTEGER,
    batch_id VARCHAR(100) NOT NULL,
    source VARCHAR(50),
    status VARCHAR(20) NOT NULL,
    total_items INTEGER,
    processed_count INTEGER,
    error_count INTEGER,
    errors JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    archived_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    checksum VARCHAR(64)
);

-- 3. 創建索引
CREATE INDEX IF NOT EXISTS idx_processing_logs_batch_id ON processing_logs(batch_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_status ON processing_logs(status);
CREATE INDEX IF NOT EXISTS idx_processing_logs_started_at ON processing_logs(started_at);
CREATE INDEX IF NOT EXISTS idx_processing_logs_completed_at ON processing_logs(completed_at);
CREATE INDEX IF NOT EXISTS idx_processing_logs_source ON processing_logs(source);

CREATE INDEX IF NOT EXISTS idx_processing_logs_archive_batch_id ON processing_logs_archive(batch_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_archive_status ON processing_logs_archive(status);
CREATE INDEX IF NOT EXISTS idx_processing_logs_archive_archived_at ON processing_logs_archive(archived_at);

-- 4. 創建清理舊日誌的函數
CREATE OR REPLACE FUNCTION cleanup_old_processing_logs(days_to_keep INTEGER)
RETURNS INTEGER AS $$
DECLARE
    moved_count INTEGER;
BEGIN
    -- 將舊記錄移動到歸檔表
    WITH moved_rows AS (
        DELETE FROM processing_logs
        WHERE completed_at < NOW() - (days_to_keep || ' days')::INTERVAL
        RETURNING *
    )
    INSERT INTO processing_logs_archive (
        original_id, batch_id, source, status,
        total_items, processed_count, error_count,
        errors, error_message, started_at,
        completed_at, created_at, metadata, checksum
    )
    SELECT 
        id, batch_id, source, status,
        total_items, processed_count, error_count,
        errors, error_message, started_at,
        completed_at, created_at, metadata, checksum
    FROM moved_rows
    RETURNING 1
    INTO moved_count;

    RETURN moved_count;
END;
$$ LANGUAGE plpgsql;

-- 向下遷移：刪除所有創建的對象
-- ------------------------------------------------------------

-- 1. 刪除清理函數
DROP FUNCTION IF EXISTS cleanup_old_processing_logs(INTEGER);

-- 2. 刪除索引
DROP INDEX IF EXISTS idx_processing_logs_batch_id;
DROP INDEX IF EXISTS idx_processing_logs_status;
DROP INDEX IF EXISTS idx_processing_logs_started_at;
DROP INDEX IF EXISTS idx_processing_logs_completed_at;
DROP INDEX IF EXISTS idx_processing_logs_source;

DROP INDEX IF EXISTS idx_processing_logs_archive_batch_id;
DROP INDEX IF EXISTS idx_processing_logs_archive_status;
DROP INDEX IF EXISTS idx_processing_logs_archive_archived_at;

-- 3. 刪除表
DROP TABLE IF EXISTS processing_logs_archive;
DROP TABLE IF EXISTS processing_logs; 