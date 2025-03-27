const crypto = require('crypto');
const { createLogger } = require('./logger');
const logger = createLogger('checksum-calculator');

class ChecksumCalculator {
    /**
     * 計算庫存項目的 checksum
     * @param {Array} items - 庫存項目數組
     * @returns {string} - SHA-256 checksum
     */
    static calculate(items) {
        try {
            // 1. 驗證輸入
            if (!Array.isArray(items)) {
                throw new Error('Input must be an array');
            }

            logger.debug('Input items:', {
                count: items.length,
                firstItem: JSON.stringify(items[0], null, 2),
                allItems: JSON.stringify(items, null, 2)
            });

            // 2. 按 serialnumber 排序
            const sortedItems = [...items].sort((a, b) => 
                String(a.serialnumber).localeCompare(String(b.serialnumber))
            );

            logger.debug('Sorted items:', {
                firstItem: JSON.stringify(sortedItems[0], null, 2),
                allItems: JSON.stringify(sortedItems, null, 2)
            });

            // 3. 格式化每個項目，只保留serialnumber
            const normalizedItems = sortedItems.map(item => {
                const normalized = this.normalizeItem(item);
                logger.debug('Normalized item:', {
                    original: JSON.stringify(item, null, 2),
                    normalized: JSON.stringify(normalized, null, 2)
                });
                return normalized;
            });

            logger.debug('All normalized items:', JSON.stringify(normalizedItems, null, 2));

            // 4. 序列化為 JSON 字符串（無空格）
            const jsonString = JSON.stringify(normalizedItems);
            
            logger.debug('Final JSON string for checksum (with length):', {
                length: jsonString.length,
                string: jsonString
            });

            // 5. 計算 SHA-256
            const checksum = crypto
                .createHash('sha256')
                .update(jsonString, 'utf8')
                .digest('hex');

            logger.debug('Checksum calculation complete:', {
                jsonStringLength: jsonString.length,
                checksum: checksum
            });

            return checksum;

        } catch (error) {
            logger.error('Checksum calculation failed:', {
                error: error.message,
                stack: error.stack,
                timestamp: new Date().toISOString()
            });
            throw error;
        }
    }

    /**
     * 規範化單個庫存項目
     * @param {Object} item - 庫存項目
     * @returns {Object} - 規範化後的項目
     */
    static normalizeItem(item) {
        // Only keep serialnumber
        return {
            serialnumber: String(item.serialnumber || '')
        };
    }

    /**
     * 驗證 checksum
     * @param {Array} items - 庫存項目數組
     * @param {string} providedChecksum - 提供的 checksum
     * @returns {boolean} - 驗證結果
     */
    static verify(items, providedChecksum) {
        try {
            const calculatedChecksum = this.calculate(items);
            const isValid = calculatedChecksum === providedChecksum;
            
            logger.debug('Checksum verification:', {
                provided: providedChecksum,
                calculated: calculatedChecksum,
                isValid,
                items: JSON.stringify(items, null, 2)
            });

            return isValid;
        } catch (error) {
            logger.error('Checksum verification failed:', {
                error: error.message,
                stack: error.stack,
                timestamp: new Date().toISOString()
            });
            return false;
        }
    }
}

module.exports = ChecksumCalculator; 