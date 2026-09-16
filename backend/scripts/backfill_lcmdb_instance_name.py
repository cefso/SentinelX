"""
为历史 lcmdb 告警回填 instance_name（从标题「xx 的 [..]」提取）。

使用方法:
    cd backend
    python -m scripts.backfill_lcmdb_instance_name            # dry-run 预览
    python -m scripts.backfill_lcmdb_instance_name --apply    # 实际写入
"""
import argparse
import asyncio

from sqlalchemy import select, update

from apps.alert.models import Alert
from apps.alert.services.alert_utils import extract_instance_from_title
from apps.core.database import get_async_session


async def count_missing(session) -> int:
    from sqlalchemy import func

    result = await session.execute(
        select(func.count()).select_from(Alert).where(
            Alert.source == "lcmdb",
            (Alert.instance_name.is_(None)) | (Alert.instance_name == ""),
        )
    )
    return int(result.scalar() or 0)


async def preview(session, limit: int = 8) -> list[tuple[int, str, str]]:
    result = await session.execute(
        select(Alert.id, Alert.title, Alert.instance_name)
        .where(
            Alert.source == "lcmdb",
            (Alert.instance_name.is_(None)) | (Alert.instance_name == ""),
        )
        .order_by(Alert.fired_at.desc())
        .limit(limit)
    )
    rows = []
    for row in result.all():
        extracted = extract_instance_from_title(row.title or "") or "(无法提取)"
        rows.append((row.id, (row.title or "")[:80], extracted))
    return rows


async def apply_backfill(session) -> int:
    result = await session.execute(
        select(Alert.id, Alert.title).where(
            Alert.source == "lcmdb",
            (Alert.instance_name.is_(None)) | (Alert.instance_name == ""),
        )
    )
    updated = 0
    for alert_id, title in result.all():
        name = extract_instance_from_title(title or "")
        if not name:
            continue
        await session.execute(
            update(Alert).where(Alert.id == alert_id).values(instance_name=name)
        )
        updated += 1
    await session.commit()
    return updated


async def main() -> None:
    parser = argparse.ArgumentParser(description="回填 lcmdb 告警 instance_name")
    parser.add_argument("--apply", action="store_true", help="实际写入（默认 dry-run）")
    args = parser.parse_args()

    async for session in get_async_session():
        missing = await count_missing(session)
        print(f"待回填 lcmdb 告警数: {missing}")
        print("\n预览:")
        for alert_id, title, extracted in await preview(session):
            print(f"  #{alert_id}  {title}  →  {extracted}")

        if not args.apply:
            print("\n[Dry Run] 未写入。加 --apply 执行回填。")
            return

        updated = await apply_backfill(session)
        print(f"\n已回填 instance_name: {updated} 条")


if __name__ == "__main__":
    asyncio.run(main())
