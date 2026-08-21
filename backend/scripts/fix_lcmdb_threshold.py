"""
修复 lcmdb 告警中 content 字段的阈值截断问题

问题根因：HTML 标签去除正则 <[^>]+> 误匹配了如 < 80 这样的比较表达式，
导致阈值行被截断，如 "阈值:[包成功率 < 80]" 变成 "阈值:[包成功率 警告"

修复方案：从 raw_data.text 重新生成正确的 content（保留 HTML 标签用于前端渲染）

使用方法:
    cd backend
    python -m scripts.fix_lcmdb_threshold          # 预览
    python -m scripts.fix_lcmdb_threshold --apply   # 执行修复
"""
import asyncio
import re
import argparse
from sqlalchemy import select, update, func
from apps.core.database import AsyncSessionLocal
from apps.alert.models import Alert


def regenerate_content(raw_text: str) -> str:
    """从原始文本重新生成 content（保留 HTML 标签用于前端渲染）"""
    # 处理转义换行符
    text = raw_text.replace("\\n", "\n")
    # 保留 HTML 标签（如 <font color='yellow'>警告</font>）
    return text


async def count_affected_records(session):
    """统计受影响的记录数量（content 与 raw_data.text 不一致）"""
    result = await session.execute(
        select(func.count(Alert.id)).where(
            Alert.source == 'lcmdb',
            Alert.raw_data.isnot(None)
        )
    )
    return result.scalar()


async def find_incorrect_records(session, limit=10):
    """查找 content 与 raw_data.text 不一致的记录"""
    result = await session.execute(
        select(Alert.id, Alert.content, Alert.raw_data).where(
            Alert.source == 'lcmdb',
            Alert.raw_data.isnot(None)
        ).limit(limit)
    )
    rows = result.all()

    incorrect = []
    for row in rows:
        raw_data = row.raw_data or {}
        markdown = raw_data.get("markdown", {})
        raw_text = markdown.get("text", "")

        if not raw_text:
            continue

        correct_content = regenerate_content(raw_text)

        # 比较（忽略首尾空白）
        if row.content and row.content.strip() != correct_content.strip():
            incorrect.append({
                'id': row.id,
                'current': row.content[:100] if row.content else None,
                'correct': correct_content[:100],
                'raw_text': raw_text[:100]
            })

    return incorrect


async def preview_fix(session, limit=5):
    """预览修复效果"""
    incorrect = await find_incorrect_records(session, limit)

    print(f"\n预览修复效果 (最多 {limit} 条):")
    print("-" * 80)
    for item in incorrect:
        print(f"\nID: {item['id']}")
        print(f"当前 content: {item['current']}")
        print(f"修复后: {item['correct']}")
    print("-" * 80)

    return len(incorrect)


async def apply_fix(session, dry_run=True):
    """执行修复"""
    if dry_run:
        print("\n[Dry Run] 预览模式，不会实际修改数据")
        count = await preview_fix(session)
        return count

    # 获取所有需要修复的记录
    result = await session.execute(
        select(Alert.id, Alert.raw_data).where(
            Alert.source == 'lcmdb',
            Alert.raw_data.isnot(None)
        )
    )
    rows = result.all()

    fixed_count = 0
    for row in rows:
        raw_data = row.raw_data or {}
        markdown = raw_data.get("markdown", {})
        raw_text = markdown.get("text", "")

        if not raw_text:
            continue

        correct_content = regenerate_content(raw_text)

        # 获取当前 content
        alert_result = await session.execute(
            select(Alert.content).where(Alert.id == row.id)
        )
        current_content = alert_result.scalar_one()

        if current_content and current_content.strip() != correct_content.strip():
            await session.execute(
                update(Alert)
                .where(Alert.id == row.id)
                .values(content=correct_content)
            )
            fixed_count += 1
            print(f"Fixed ID: {row.id}")

    await session.commit()
    return fixed_count


async def main():
    parser = argparse.ArgumentParser(description='修复 lcmdb 告警中的阈值截断问题')
    parser.add_argument('--apply', action='store_true', help='实际执行修复（默认仅预览）')
    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        try:
            total = await count_affected_records(session)
            print(f"共发现 {total} 条 lcmdb 告警")

            if total > 0:
                fixed = await apply_fix(session, dry_run=not args.apply)
                if not args.apply:
                    print(f"\n预计需要修复: {fixed} 条记录")
                    print("使用 --apply 参数执行实际修复")
                else:
                    print(f"\n成功修复: {fixed} 条记录")
            else:
                print("无需修复")
        finally:
            await session.close()


if __name__ == '__main__':
    asyncio.run(main())
