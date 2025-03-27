-- Up Migration
CREATE TABLE IF NOT EXISTS processing_logs (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_items INTEGER NOT NULL DEFAULT 0,
    processed_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    errors JSONB,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    checksum VARCHAR(64)
);

-- Create indexes for better query performance
CREATE INDEX idx_processing_logs_batch_id ON processing_logs(batch_id);
CREATE INDEX idx_processing_logs_status ON processing_logs(status);
CREATE INDEX idx_processing_logs_created_at ON processing_logs(created_at);

-- Create archive table for old logs
CREATE TABLE IF NOT EXISTS processing_logs_archive (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    total_items INTEGER NOT NULL,
    processed_count INTEGER NOT NULL,
    error_count INTEGER NOT NULL,
    errors JSONB,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    checksum VARCHAR(64)
);

-- Create indexes for archive table
CREATE INDEX idx_processing_logs_archive_batch_id ON processing_logs_archive(batch_id);
CREATE INDEX idx_processing_logs_archive_created_at ON processing_logs_archive(created_at);
CREATE INDEX idx_processing_logs_archive_archived_at ON processing_logs_archive(archived_at);

-- Create function to move old logs to archive
CREATE OR REPLACE FUNCTION archive_old_processing_logs(retention_days INTEGER)
RETURNS INTEGER AS $$
DECLARE
    moved_count INTEGER;
BEGIN
    WITH moved_rows AS (
        DELETE FROM processing_logs
        WHERE created_at < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL
        RETURNING *
    )
    INSERT INTO processing_logs_archive (
        batch_id, source, status, total_items, processed_count, error_count,
        errors, error_message, started_at, completed_at, created_at,
        metadata, checksum
    )
    SELECT
        batch_id, source, status, total_items, processed_count, error_count,
        errors, error_message, started_at, completed_at, created_at,
        metadata, checksum
    FROM moved_rows
    RETURNING 1
    INTO moved_count;

    RETURN moved_count;
END;
$$ LANGUAGE plpgsql;

-- Down Migration
DROP FUNCTION IF EXISTS archive_old_processing_logs(INTEGER);
DROP TABLE IF EXISTS processing_logs_archive;
DROP TABLE IF EXISTS processing_logs; 