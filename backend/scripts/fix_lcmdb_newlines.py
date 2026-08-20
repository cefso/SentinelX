"""
修复 lcmdb 告警中 content 字段的转义换行符
将字面量 \n 替换为实际换行符

使用方法:
    cd backend
    python -m scripts.fix_lcmdb_newlines
"""
import asyncio
from sqlalchemy import update, select, func
from apps.core.database import get_async_session
from apps.alert.models import Alert


async def count_affected_records(session):
    """统计受影响的记录数量"""
    result = await session.execute(
        select(func.count(Alert.id)).where(
            Alert.source == 'lcmdb',
            Alert.content.like('%\\n%')
        )
    )
    return result.scalar()


async def preview_fix(session, limit=5):
    """预览修复效果"""
    result = await session.execute(
        select(Alert.id, Alert.alert_key, Alert.content).where(
            Alert.source == 'lcmdb',
            Alert.content.like('%\\n%')
        ).limit(limit)
    )
    rows = result.all()

    print("\n预览修复效果:")
    print("-" * 80)
    for row in rows:
        print(f"\nID: {row.id}")
        print(f"Alert Key: {row.alert_key}")
        print(f"修复前: {row.content[:100]}...")
        fixed = row.content.replace('\\n', '\n')
        print(f"修复后: {fixed[:100]}...")
    print("-" * 80)


async def apply_fix(session, dry_run=True):
    """执行修复"""
    if dry_run:
        print("\n[Dry Run] 预览模式，不会实际修改数据")
        await preview_fix(session)
        return

    # 获取修复前数量
    before_count = await count_affected_records(session)
    print(f"\n修复前受影响记录数: {before_count}")

    # 执行修复
    result = await session.execute(
        update(Alert)
        .where(
            Alert.source == 'lcmdb',
            Alert.content.like('%\\n%')
        )
        .values(content=func.replace(Alert.content, '\\n', '\n'))
    )
    await session.commit()

    # 获取修复后数量
    after_count = await count_affected_records(session)
    print(f"修复后受影响记录数: {after_count}")
    print(f"成功修复: {before_count - after_count} 条记录")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='修复 lcmdb 告警中的转义换行符')
    parser.add_argument('--apply', action='store_true', help='实际执行修复（默认仅预览）')
    args = parser.parse_args()

    async for session in get_async_session():
        try:
            total = await count_affected_records(session)
            print(f"共发现 {total} 条需要修复的记录")

            if total > 0:
                await apply_fix(session, dry_run=not args.apply)
            else:
                print("无需修复")
        finally:
            await session.close()


if __name__ == '__main__':
    asyncio.run(main())
