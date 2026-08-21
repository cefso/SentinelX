-- 修复 lcmdb 告警中 content 字段
-- 从 raw_data->'markdown'->>'text' 重新生成 content（保留 HTML 标签）

-- 1. 预览修复结果（查看前 10 条）
SELECT
    id,
    LEFT(content, 80) AS current_content,
    LEFT(
        REPLACE(raw_data->'markdown'->>'text', '\n', CHR(10)),
        80
    ) AS fixed_content
FROM alerts
WHERE source = 'lcmdb'
  AND raw_data->'markdown'->>'text' IS NOT NULL
LIMIT 10;

-- 2. 统计需要修复的记录数
SELECT COUNT(*) AS need_fix_count
FROM alerts
WHERE source = 'lcmdb'
  AND raw_data->'markdown'->>'text' IS NOT NULL
  AND content != REPLACE(raw_data->'markdown'->>'text', '\n', CHR(10));

-- 3. 执行修复（取消注释后运行）
UPDATE alerts
SET content = REPLACE(raw_data->'markdown'->>'text', '\n', CHR(10))
WHERE source = 'lcmdb'
  AND raw_data->'markdown'->>'text' IS NOT NULL;

-- 4. 验证修复结果
SELECT COUNT(*) AS remaining_count
FROM alerts
WHERE source = 'lcmdb'
  AND raw_data->'markdown'->>'text' IS NOT NULL
  AND content != REPLACE(raw_data->'markdown'->>'text', '\n', CHR(10));
