#!/usr/bin/env python3
"""
刷新每日热榜新闻数据。

用法：
    python scripts/refresh_news.py                # 采集并写入数据库
    python scripts/refresh_news.py --dry-run      # 只采集不写入，看数据
    python scripts/refresh_news.py --show weibo   # 查看某个平台的最新数据

建议配合 cron/launchd 定时执行，例如每小时刷新一次：
    0 * * * * cd /path/to/project && python scripts/refresh_news.py >> logs/news.log 2>&1
"""

import asyncio
import sys
import argparse
from pathlib import Path

# 确保能导入项目模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def run_dry():
    """只拉取不入库"""
    from agno_tools.news_collector import collect_all_news
    items = await collect_all_news()
    print(f"\n✅ 采集成功，共 {len(items)} 条")
    print("\n前 10 条预览：")
    for item in items[:10]:
        print(f"  [{item['source_name']:12s}] #{item['rank']:3d} {item['title'][:60]}")


async def run_refresh():
    """正常刷新流程"""
    from agno_tools.news_collector import refresh_news
    await refresh_news()


async def run_show(source: str, limit: int):
    """查看某个平台最新数据"""
    from agno_tools.news_collector import get_latest_news_by_source, SOURCES
    if source not in SOURCES:
        print(f"❌ 不支持的源：{source}")
        print(f"支持的源：{', '.join(SOURCES.keys())}")
        sys.exit(1)

    items = await get_latest_news_by_source(source, limit=limit)
    if not items:
        print(f"⚠️  {SOURCES[source]} 数据库中无数据，先运行一次刷新")
        return

    print(f"\n=== {SOURCES[source]}（前 {len(items)} 条）===")
    for item in items:
        print(f"  #{item['rank_position']:3d} [{item['crawl_date']}] {item['title']}")


def main():
    parser = argparse.ArgumentParser(description="观澜 · 每日热榜新闻刷新")
    parser.add_argument("--dry-run", action="store_true", help="只采集不写库")
    parser.add_argument("--show", type=str, metavar="SOURCE", help="查看某个源的最新数据")
    parser.add_argument("--limit", type=int, default=20, help="查看时的数据条数（默认 20）")
    args = parser.parse_args()

    if args.dry_run:
        asyncio.run(run_dry())
    elif args.show:
        asyncio.run(run_show(args.show, args.limit))
    else:
        asyncio.run(run_refresh())


if __name__ == "__main__":
    main()
