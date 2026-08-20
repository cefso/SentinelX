-- ============================================================
-- 告警操作记录类型迁移脚本
-- 将旧的12种 action 类型迁移到新的8种核心类型
-- ============================================================
-- 执行前请先备份数据库！
-- pg_dump -U postgres sentinelx > backup_$(date +%Y%m%d).sql
-- ============================================================

BEGIN;

-- 1. deduplicated → filtered
UPDATE alert_history SET action = 'filtered' WHERE action = 'deduplicated';

-- 2. aggregated → filtered
UPDATE alert_history SET action = 'filtered' WHERE action = 'aggregated';

-- 3. dispose_acknowledge → acknowledged
UPDATE alert_history SET action = 'acknowledged' WHERE action = 'dispose_acknowledge';

-- 4. dispose_resolve → resolved
UPDATE alert_history SET action = 'resolved' WHERE action = 'dispose_resolve';

-- 5. dispose_silence → silenced
UPDATE alert_history SET action = 'silenced' WHERE action = 'dispose_silence';

-- 6. dispose_note → updated
UPDATE alert_history SET action = 'updated' WHERE action = 'dispose_note';

-- 7. acknowledge_callback → acknowledged
UPDATE alert_history SET action = 'acknowledged' WHERE action = 'acknowledge_callback';

-- 8. resolve_callback → resolved
UPDATE alert_history SET action = 'resolved' WHERE action = 'resolve_callback';

-- 9. silence_callback → silenced
UPDATE alert_history SET action = 'silenced' WHERE action = 'silence_callback';

-- 10. escalate_level_* → escalated
UPDATE alert_history SET action = 'escalated' WHERE action LIKE 'escalate_level_%';

-- 11. auto_assign → updated
UPDATE alert_history SET action = 'updated' WHERE action = 'auto_assign';

-- 12. update → updated
UPDATE alert_history SET action = 'updated' WHERE action = 'update';

COMMIT;

-- ============================================================
-- 验证迁移结果
-- ============================================================
SELECT action, COUNT(*) as count 
FROM alert_history 
GROUP BY action 
ORDER BY count DESC;
