"""
为历史告警回填 instance_key / alert_type（实例告警反规范化列）。

部署后务必执行本脚本，否则历史行 instance_key 为 NULL，
实例告警页会把它们聚合成一个「未识别实例」卡片。

使用方法:
    cd backend
    python -m scripts.backfill_alert_instance_fields            # dry-run 预览
    python -m scripts.backfill_alert_instance_fields --apply    # 实际写入
"""
from __future__ import annotations

import argparse
import asyncio
from typing import List, Sequence, Tuple

from sqlalchemy import or_, select, update

from apps.alert.models import Alert
from apps.alert.services.by_instance import apply_instance_denorm
from apps.core.database import get_db_context

BATCH_SIZE = 500


def _needs_backfill() -> list:
    return [
        or_(Alert.instance_key.is_(None), Alert.alert_type.is_(None)),
    ]


async def count_missing(session) -> int:
    from sqlalchemy import func

    result = await session.execute(
        select(func.count()).select_from(Alert).where(*_needs_backfill())
    )
    return int(result.scalar() or 0)


async def preview(session, limit: int = 8) -> List[Tuple[int, str, str, str]]:
    result = await session.execute(
        select(
            Alert.id,
            Alert.title,
            Alert.instance_name,
            Alert.alert_key,
            Alert.metric_name,
            Alert.labels,
            Alert.instance_id,
        )
        .where(*_needs_backfill())
        .order_by(Alert.id.asc())
        .limit(limit)
    )
    rows = []
    for row in result.all():
        alert = Alert(
            id=row.id,
            title=row.title,
            instance_name=row.instance_name,
            alert_key=row.alert_key,
            metric_name=row.metric_name,
            labels=row.labels or {},
            instance_id=row.instance_id,
        )
        apply_instance_denorm(alert)
        rows.append(
            (row.id, (row.title or "")[:80], alert.instance_key or "?", alert.alert_type or "?")
        )
    return rows


async def apply_backfill(session) -> int:
    updated = 0
    last_id = 0
    while True:
        result = await session.execute(
            select(Alert)
            .where(*_needs_backfill(), Alert.id > last_id)
            .order_by(Alert.id.asc())
            .limit(BATCH_SIZE)
        )
        alerts: Sequence[Alert] = result.scalars().all()
        if not alerts:
            break
        for alert in alerts:
            apply_instance_denorm(alert)
            await session.execute(
                update(Alert)
                .where(Alert.id == alert.id)
                .values(instance_key=alert.instance_key, alert_type=alert.alert_type)
            )
            last_id = alert.id
            updated += 1
        await session.commit()
    return updated


async def main() -> None:
    parser = argparse.ArgumentParser(description="回填告警 instance_key / alert_type")
    parser.add_argument("--apply", action="store_true", help="实际写入（默认 dry-run）")
    args = parser.parse_args()

    async with get_db_context() as session:
        missing = await count_missing(session)
        print(f"待回填告警数: {missing}")
        print("\n预览:")
        for alert_id, title, key, atype in await preview(session):
            print(f"  #{alert_id}  {title}  →  key={key} type={atype}")

        if not args.apply:
            print("\nDry-run 结束。加 --apply 实际写入。")
            return

        updated = await apply_backfill(session)
        print(f"\n已回填 {updated} 条。")


if __name__ == "__main__":
    asyncio.run(main())
