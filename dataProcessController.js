const pool = require('../db');
const { createLogger } = require('../utils/logger');
const ChecksumCalculator = require('../utils/checksumCalculator');
const logger = createLogger('data-processing');

// 處理時間戳和時區
const ensureTimestamp = (timestamp) => {
    if (!timestamp) {
        return new Date().toISOString();
    }
    try {
        // 解析 ISO 格式的時間戳
        const date = new Date(timestamp);
        if (isNaN(date.getTime())) {
            throw new Error('Invalid timestamp');
        }
        // 如果時間戳沒有時區信息，假定為 UTC
        return date.toISOString();
    } catch (error) {
        logger.warn('Invalid timestamp format, using current time:', {
            original: timestamp,
            error: error.message
        });
        return new Date().toISOString();
    }
};

// 確保數值為有效的數字
const ensureNumeric = (value, defaultValue = 0) => {
    if (value === null || value === undefined) {
        return defaultValue;
    }
    const num = parseFloat(value);
    return isNaN(num) ? defaultValue : num;
};

// Process inventory data
const processInventoryData = async (req, res) => {
    const client = await pool.connect();
    let processingLogId = null;
    let currentTransaction = false;

    try {
        const { batch_id, items, source = 'api', metadata } = req.body;
        
        logger.info('Starting inventory data processing:', {
            batch_id,
            source,
            itemCount: items?.length || 0,
            metadata
        });

        // 驗證輸入
        if (!Array.isArray(items) || items.length === 0) {
            throw new Error('No items to process');
        }

        // 開始新的事務
        await client.query('BEGIN');
        currentTransaction = true;

        // 1. 創建處理日誌
        logger.debug('Creating processing log entry');
        const createLogResult = await client.query(`
            INSERT INTO processing_logs 
            (batch_id, source, status, total_items, processed_count, error_count, started_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            RETURNING id
        `, [batch_id, source, 'processing', items.length, 0, 0]);

        processingLogId = createLogResult.rows[0].id;
        logger.info('Created processing log:', { id: processingLogId, batch_id });

        // 2. 處理每個項目
        const errors = [];
        let processedCount = 0;
        let errorCount = 0;

        // 使用 Promise.all 並行處理所有項目
        await Promise.all(items.map(async (item) => {
            try {
                logger.debug('Processing item:', { 
                    serialnumber: item.serialnumber,
                    batch_id,
                    processingLogId 
                });

                // 檢查必要字段
                if (!item.serialnumber) {
                    throw new Error('Missing serial number');
                }

                // 標記現有記錄為非當前
                await client.query(`
                    UPDATE system_records 
                    SET is_current = false 
                    WHERE serialnumber = $1 
                    AND is_current = true
                `, [item.serialnumber]);

                // 準備時間戳
                const now = new Date().toISOString();
                const created_at = item.created_at ? new Date(item.created_at).toISOString() : now;
                const started_at = item.started_at ? new Date(item.started_at).toISOString() : now;
                const last_updated_at = item.last_updated_at ? new Date(item.last_updated_at).toISOString() : now;

                // 插入新記錄
                await client.query(`
                    INSERT INTO system_records (
                        serialnumber,
                        computername,
                        manufacturer,
                        model,
                        systemsku,
                        operatingsystem,
                        cpu,
                        resolution,
                        graphicscard,
                        touchscreen,
                        ram_gb,
                        disks,
                        design_capacity,
                        full_charge_capacity,
                        cycle_count,
                        battery_health,
                        is_current,
                        outbound_status,
                        sync_status,
                        data_source,
                        validation_status,
                        validation_message,
                        disks_gb,
                        sync_version,
                        created_at,
                        started_at,
                        last_updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 
                             $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                             $21, $22, $23, $24, $25, $26, $27)
                `, [
                    item.serialnumber,
                    item.computername || '',
                    item.manufacturer || '',
                    item.model || '',
                    item.systemsku || '',
                    item.operatingsystem || '',
                    item.cpu || '',
                    item.resolution || '',
                    item.graphicscard || '',
                    item.touchscreen || false,
                    parseFloat(item.ram_gb) || 0,
                    item.disks || '',
                    parseInt(item.design_capacity) || 0,
                    parseInt(item.full_charge_capacity) || 0,
                    parseInt(item.cycle_count) || 0,
                    parseFloat(item.battery_health) || 0,
                    true,
                    item.outbound_status || 'pending',
                    item.sync_status || 'pending',
                    item.data_source || source,
                    item.validation_status || 'pending',
                    item.validation_message || '',
                    parseFloat(item.disks_gb) || 0,
                    item.sync_version || '1.0',
                    created_at,
                    started_at,
                    last_updated_at
                ]);

                processedCount++;
                logger.debug('Processed item successfully:', { serialnumber: item.serialnumber });

            } catch (itemError) {
                logger.error('Error processing item:', {
                    serialnumber: item.serialnumber,
                    error: itemError.message,
                    stack: itemError.stack
                });
                errorCount++;
                errors.push({
                    serialnumber: item.serialnumber,
                    error: itemError.message
                });
                // 不拋出錯誤，讓其他項目繼續處理
            }
        }));

        // 3. 更新處理日誌
        const status = errorCount === 0 ? 'completed' : 'completed_with_errors';
        logger.debug('Updating processing log:', {
            id: processingLogId,
            status,
            processedCount,
            errorCount
        });

        await client.query(`
            UPDATE processing_logs SET
                status = $1,
                processed_count = $2,
                error_count = $3,
                completed_at = NOW(),
                errors = $4::jsonb
            WHERE id = $5
        `, [status, processedCount, errorCount, JSON.stringify(errors), processingLogId]);

        // 提交事務
        await client.query('COMMIT');
        currentTransaction = false;
        logger.info('Transaction committed successfully');

        // 4. 返回處理結果
        const response = {
            success: true,
            message: 'Data processing completed',
            batchId: batch_id,
            details: {
                batch_id,
                total_items: items.length,
                processed_count: processedCount,
                error_count: errorCount,
                status,
                errors: errors.length > 0 ? errors : undefined
            }
        };

        logger.info('Processing completed:', response);
        res.json(response);

    } catch (error) {
        logger.error('Error in processInventoryData:', {
            error: error.message,
            stack: error.stack,
            processingLogId,
            currentTransaction
        });

        if (currentTransaction) {
            try {
                await client.query('ROLLBACK');
                logger.info('Transaction rolled back');
            } catch (rollbackError) {
                logger.error('Error during rollback:', rollbackError);
            }
            currentTransaction = false;
        }
        
        // 如果處理日誌已創建，嘗試在新事務中更新為失敗狀態
        if (processingLogId) {
            try {
                await client.query('BEGIN');
                await client.query(`
                    UPDATE processing_logs SET
                        status = 'failed',
                        error_message = $1,
                        completed_at = NOW()
                    WHERE id = $2
                `, [error.message, processingLogId]);
                await client.query('COMMIT');
                logger.info('Processing log updated to failed status');
            } catch (logError) {
                logger.error('Failed to update processing log:', logError);
                try {
                    await client.query('ROLLBACK');
                } catch (rollbackError) {
                    logger.error('Error during log update rollback:', rollbackError);
                }
            }
        }

        res.status(500).json({
            success: false,
            error: 'Failed to process inventory data',
            details: error.message
        });
    } finally {
        try {
            client.release();
            logger.info('Database client released');
        } catch (releaseError) {
            logger.error('Error releasing client:', releaseError);
        }
    }
};

// Get processing logs
const getLogs = async (req, res) => {
    try {
        const { page = 1, limit = 20, status } = req.query;
        const offset = (page - 1) * limit;

        // 構建基礎查詢，使用 AT TIME ZONE 轉換時間戳
        let query = `
            SELECT 
                id, 
                batch_id, 
                source, 
                status,
                total_items, 
                processed_count, 
                error_count,
                started_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/New_York' as started_at,
                completed_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/New_York' as completed_at,
                error_message,
                errors
            FROM processing_logs
        `;

        const params = [];
        if (status) {
            query += ` WHERE status = $1`;
            params.push(status);
        }

        // 按照處理開始時間降序排序
        query += ` ORDER BY started_at DESC LIMIT $${params.length + 1} OFFSET $${params.length + 2}`;
        params.push(limit, offset);

        // 執行查詢並記錄結果
        logger.debug('Executing logs query:', {
            query,
            params,
            timestamp: new Date().toISOString()
        });

        const result = await pool.query(query, params);

        // 獲取總數
        const countQuery = 'SELECT COUNT(*) FROM processing_logs' + (status ? ' WHERE status = $1' : '');
        const countResult = await pool.query(countQuery, status ? [status] : []);

        // 格式化時間戳
        const formattedLogs = result.rows.map(log => ({
            ...log,
            started_at: log.started_at ? new Date(log.started_at).toISOString() : null,
            completed_at: log.completed_at ? new Date(log.completed_at).toISOString() : null
        }));

        logger.debug('Logs query result:', {
            count: formattedLogs.length,
            firstLog: formattedLogs[0],
            lastLog: formattedLogs[formattedLogs.length - 1],
            timestamp: new Date().toISOString()
        });

        res.json({
            success: true,
            logs: formattedLogs,
            total: parseInt(countResult.rows[0].count),
            page: parseInt(page),
            totalPages: Math.ceil(parseInt(countResult.rows[0].count) / limit),
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        logger.error('Error fetching logs:', {
            error: error.message,
            stack: error.stack,
            timestamp: new Date().toISOString()
        });
        res.status(500).json({
            success: false,
            error: 'Failed to fetch logs',
            details: error.message,
            timestamp: new Date().toISOString()
        });
    }
};

// Get processing status
const getProcessingStatus = async (req, res) => {
    try {
        const { batchId } = req.params;
        const result = await pool.query(
            `SELECT 
                id, batch_id, source, status,
                total_items, processed_count, error_count,
                started_at, completed_at, error_message,
                errors
            FROM processing_logs
            WHERE batch_id = $1`,
            [batchId]
        );

        if (result.rows.length === 0) {
            return res.status(404).json({
                success: false,
                error: 'Batch not found'
            });
        }

        res.json({
            success: true,
            status: result.rows[0]
        });
    } catch (error) {
        logger.error('Error fetching status:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to fetch status'
        });
    }
};

// Clear logs
const clearLogs = async (req, res) => {
    let client = null;
    let transactionActive = false;

    try {
        client = await pool.connect();
        
        // 開始新事務
        await client.query('BEGIN');
        transactionActive = true;

        // 先檢查是否有需要歸檔的日誌
        const checkResult = await client.query(`
            SELECT COUNT(*) as count
            FROM processing_logs
            WHERE completed_at < NOW() - INTERVAL '30 days'
        `);

        if (parseInt(checkResult.rows[0].count) === 0) {
            await client.query('COMMIT');
            transactionActive = false;
            return res.json({
                success: true,
                cleared: 0,
                message: 'No logs to archive'
            });
        }

        // 歸檔舊日誌
        const archiveResult = await client.query(`
            WITH moved_rows AS (
                INSERT INTO processing_logs_archive (
                    original_id, batch_id, source, status,
                    total_items, processed_count, error_count,
                    errors, error_message, started_at,
                    completed_at, created_at, archived_at
                )
                SELECT 
                    id, batch_id, source, status,
                    total_items, processed_count, error_count,
                    errors, error_message, started_at,
                    completed_at, created_at, NOW()
                FROM processing_logs
                WHERE completed_at < NOW() - INTERVAL '30 days'
                RETURNING id
            )
            SELECT COUNT(*) as count FROM moved_rows
        `);

        // 刪除已歸檔的日誌
        await client.query(`
            DELETE FROM processing_logs
            WHERE completed_at < NOW() - INTERVAL '30 days'
        `);

        await client.query('COMMIT');
        transactionActive = false;

        res.json({
            success: true,
            cleared: parseInt(archiveResult.rows[0].count),
            message: `${archiveResult.rows[0].count} logs archived successfully`
        });

    } catch (error) {
        logger.error('Error clearing logs:', {
            error: error.message,
            stack: error.stack,
            timestamp: new Date().toISOString()
        });

        try {
            if (client && transactionActive) {
                await client.query('ROLLBACK');
                transactionActive = false;
            }
        } catch (rollbackError) {
            logger.error('Rollback failed during log clearing:', {
                error: rollbackError.message,
                originalError: error.message,
                timestamp: new Date().toISOString()
            });
        }

        res.status(500).json({
            success: false,
            error: 'Failed to clear logs',
            details: error.message
        });

    } finally {
        if (client) {
            try {
                if (transactionActive) {
                    await client.query('ROLLBACK');
                }
            } catch (finalError) {
                logger.error('Final rollback failed during log clearing:', finalError);
            }
            client.release();
        }
    }
};

// Delete specific log
const deleteLog = async (req, res) => {
    const { batchId } = req.params;
    const client = await pool.connect();
    
    try {
        await client.query('BEGIN');

        // Check if log exists
        const checkResult = await client.query(
            'SELECT id FROM processing_logs WHERE batch_id = $1',
            [batchId]
        );

        if (checkResult.rows.length === 0) {
            return res.status(404).json({
                success: false,
                error: 'Log record not found'
            });
        }

        // Delete the log
        await client.query(
            'DELETE FROM processing_logs WHERE batch_id = $1',
            [batchId]
        );

        await client.query('COMMIT');

        res.json({
            success: true,
            message: 'Log record deleted successfully'
        });
    } catch (error) {
        await client.query('ROLLBACK');
        logger.error('Error deleting log:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to delete log record'
        });
    } finally {
        client.release();
    }
};

// Get sync status
const getSyncStatus = async (req, res) => {
    try {
        const { serialnumbers } = req.body;
        
        if (!Array.isArray(serialnumbers)) {
            return res.status(400).json({
                success: false,
                error: 'serialnumbers must be an array'
            });
        }

        const result = await pool.query(
            `SELECT 
                serialnumber,
                sync_status,
                sync_version,
                last_sync_time,
                is_current
            FROM system_records 
            WHERE serialnumber = ANY($1)
            ORDER BY serialnumber, created_at DESC`,
            [serialnumbers]
        );

        // 組織返回數據
        const statusMap = {};
        for (const record of result.rows) {
            if (!statusMap[record.serialnumber] || record.is_current) {
                statusMap[record.serialnumber] = {
                    sync_status: record.sync_status,
                    sync_version: record.sync_version,
                    last_sync_time: record.last_sync_time
                };
            }
        }

        res.json({
            success: true,
            statuses: statusMap
        });
    } catch (error) {
        logger.error('Error getting sync status:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to get sync status'
        });
    }
};

module.exports = {
    processInventoryData,
    getLogs,
    getProcessingStatus,
    clearLogs,
    deleteLog,
    getSyncStatus
}; 