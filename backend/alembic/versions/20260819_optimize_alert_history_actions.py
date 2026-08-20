"""optimize alert history actions

Revision ID: 20260819_optimize_history
Revises: 20260724_webhook_logs
Create Date: 2026-08-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260819_optimize_history"
down_revision = "20260724_webhook_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    将旧的 action 类型迁移到新的 8 种核心类型：
    
    旧类型 → 新类型映射：
    - deduplicated → filtered
    - aggregated → filtered
    - dispose_acknowledge → acknowledged
    - dispose_resolve → resolved
    - dispose_silence → silenced
    - dispose_note → updated
    - acknowledge_callback → acknowledged
    - resolve_callback → resolved
    - silence_callback → silenced
    - escalate_level_* → escalated
    - auto_assign → updated
    - update → updated
    """
    
    # 1. deduplicated → filtered
    op.execute(
        "UPDATE alert_history SET action = 'filtered' WHERE action = 'deduplicated'"
    )
    
    # 2. aggregated → filtered
    op.execute(
        "UPDATE alert_history SET action = 'filtered' WHERE action = 'aggregated'"
    )
    
    # 3. dispose_acknowledge → acknowledged
    op.execute(
        "UPDATE alert_history SET action = 'acknowledged' WHERE action = 'dispose_acknowledge'"
    )
    
    # 4. dispose_resolve → resolved
    op.execute(
        "UPDATE alert_history SET action = 'resolved' WHERE action = 'dispose_resolve'"
    )
    
    # 5. dispose_silence → silenced
    op.execute(
        "UPDATE alert_history SET action = 'silenced' WHERE action = 'dispose_silence'"
    )
    
    # 6. dispose_note → updated
    op.execute(
        "UPDATE alert_history SET action = 'updated' WHERE action = 'dispose_note'"
    )
    
    # 7. acknowledge_callback → acknowledged
    op.execute(
        "UPDATE alert_history SET action = 'acknowledged' WHERE action = 'acknowledge_callback'"
    )
    
    # 8. resolve_callback → resolved
    op.execute(
        "UPDATE alert_history SET action = 'resolved' WHERE action = 'resolve_callback'"
    )
    
    # 9. silence_callback → silenced
    op.execute(
        "UPDATE alert_history SET action = 'silenced' WHERE action = 'silence_callback'"
    )
    
    # 10. escalate_level_* → escalated (使用 LIKE 匹配前缀)
    op.execute(
        "UPDATE alert_history SET action = 'escalated' WHERE action LIKE 'escalate_level_%'"
    )
    
    # 11. auto_assign → updated
    op.execute(
        "UPDATE alert_history SET action = 'updated' WHERE action = 'auto_assign'"
    )
    
    # 12. update → updated
    op.execute(
        "UPDATE alert_history SET action = 'updated' WHERE action = 'update'"
    )


def downgrade() -> None:
    """
    回滚操作（不建议回滚，因为无法精确还原旧的 action 类型）
    """
    # 由于新的 action 类型是旧类型的合并，无法精确回滚
    # 如果需要回滚，需要从 new_value 中提取原始 action 类型
    pass
