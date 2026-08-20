-- 修复 lcmdb 告警中 content 字段的转义换行符
-- 将字面量 \n 替换为实际换行符

-- 1. 查看受影响的记录数量
SELECT COUNT(*) as affected_count
FROM alerts
WHERE source = 'lcmdb'
  AND content LIKE '%\\n%';

-- 2. 预览修复效果（不执行）
SELECT
    id,
    alert_key,
    LEFT(content, 200) as content_preview,
    REPLACE(content, '\n', CHR(10)) as fixed_content_preview
FROM alerts
WHERE source = 'lcmdb'
  AND content LIKE '%\\n%'
LIMIT 10;

-- 3. 执行修复（取消注释后运行）
-- UPDATE alerts
-- SET content = REPLACE(content, '\n', CHR(10))
-- WHERE source = 'lcmdb'
--   AND content LIKE '%\\n%';

-- 4. 修复后验证
-- SELECT COUNT(*) as remaining_count
-- FROM alerts
-- WHERE source = 'lcmdb'
--   AND content LIKE '%\\n%';
