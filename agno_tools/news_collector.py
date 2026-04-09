# agno_tools/news_collector.py
# 阶段 1 接入：从 newsnow 聚合 API 拉取 12 个平台的热榜数据
# 迁移自 BettaFish/MindSpider/BroadTopicExtraction/get_today_news.py
#
# 使用方式：
#   # 命令行手动刷新
#   python -m agno_tools.news_collector
#
#   # 或者在代码中：
#   from agno_tools.news_collector import refresh_news
#   import asyncio
#   asyncio.run(refresh_news())

from __future__ import annotations
import asyncio
import json
import time
from datetime import datetime, date
from typing import List, Dict, Any

import httpx
from sqlalchemy import text


BASE_URL = "https://newsnow.busiyi.world"

# 12 个支持的新闻源（与 BettaFish MindSpider 一致）
SOURCES = {
    "weibo": "微博热搜",
    "zhihu": "知乎热榜",
    "bilibili-hot-search": "B站热搜",
    "toutiao": "今日头条",
    "douyin": "抖音热榜",
    "github-trending-today": "GitHub趋势",
    "coolapk": "酷安热榜",
    "tieba": "百度贴吧",
    "wallstreetcn": "华尔街见闻",
    "thepaper": "澎湃新闻",
    "cls-hot": "财联社",
    "xueqiu": "雪球热榜",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": BASE_URL + "/",
    "Connection": "keep-alive",
}


async def fetch_source(client: httpx.AsyncClient, source: str) -> List[Dict[str, Any]]:
    """从单个源拉取热榜数据，失败时返回空列表"""
    url = f"{BASE_URL}/api/s?id={source}&latest"
    try:
        r = await client.get(url, headers=_HEADERS, timeout=30.0)
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])

        result = []
        for idx, item in enumerate(items):
            result.append({
                "source": source,
                "source_name": SOURCES[source],
                "origin_id": str(item.get("id", "")),
                "title": item.get("title", "").strip(),
                "url": item.get("url") or item.get("mobileUrl", ""),
                "extra": item.get("extra", {}),
                "rank": idx + 1,
            })
        print(f"  ✓ {SOURCES[source]:12s} {len(result)} 条")
        return result
    except httpx.HTTPStatusError as e:
        print(f"  ✗ {SOURCES[source]:12s} HTTP {e.response.status_code}")
        return []
    except Exception as e:
        print(f"  ✗ {SOURCES[source]:12s} {type(e).__name__}: {e}")
        return []


async def collect_all_news() -> List[Dict[str, Any]]:
    """并发从所有源拉取热榜"""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [fetch_source(client, src) for src in SOURCES.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    # 展平
    flat = []
    for items in results:
        flat.extend(items)
    return flat


async def save_to_db(news_items: List[Dict[str, Any]]) -> int:
    """写入 daily_news 表。先清理当天的旧数据再插入新数据。"""
    if not news_items:
        return 0

    # 懒加载数据库引擎
    from .db_query_tools import _get_engine
    engine = _get_engine()

    today = date.today().isoformat()
    now_ts = int(time.time() * 1000)

    async with engine.begin() as conn:
        # 先保证表存在（适配 SQLite / PostgreSQL / MySQL 三种方言）
        await conn.execute(text(_get_create_sql()))

        # 删除今天的旧数据（避免重复）
        await conn.execute(
            text("DELETE FROM daily_news WHERE crawl_date = :today"),
            {"today": today},
        )

        # 批量插入
        for idx, item in enumerate(news_items):
            news_id = f"{item['source']}_{idx}_{now_ts}"
            await conn.execute(
                text("""
                    INSERT INTO daily_news
                        (news_id, source_platform, title, url, description, crawl_date, rank_position, add_ts, last_modify_ts)
                    VALUES
                        (:news_id, :src, :title, :url, :desc, :date, :rank, :ts, :ts)
                """),
                {
                    "news_id": news_id,
                    "src": item["source"],
                    "title": item["title"],
                    "url": item["url"],
                    "desc": json.dumps(item.get("extra", {}), ensure_ascii=False),
                    "date": today,
                    "rank": item["rank"],
                    "ts": now_ts,
                },
            )

    return len(news_items)


def _get_create_sql() -> str:
    """根据当前数据库方言生成 daily_news 建表语句"""
    from config import settings
    dialect = (settings.DB_DIALECT or "sqlite").lower()

    if dialect == "sqlite":
        return """
            CREATE TABLE IF NOT EXISTS daily_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id TEXT NOT NULL,
                source_platform TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT,
                description TEXT,
                crawl_date TEXT NOT NULL,
                rank_position INTEGER,
                add_ts INTEGER NOT NULL,
                last_modify_ts INTEGER NOT NULL
            )
        """
    elif dialect in ("postgresql", "postgres"):
        return """
            CREATE TABLE IF NOT EXISTS daily_news (
                id SERIAL PRIMARY KEY,
                news_id VARCHAR(128) NOT NULL,
                source_platform VARCHAR(32) NOT NULL,
                title VARCHAR(500) NOT NULL,
                url VARCHAR(1024),
                description TEXT,
                crawl_date DATE NOT NULL,
                rank_position INTEGER,
                add_ts BIGINT NOT NULL,
                last_modify_ts BIGINT NOT NULL
            )
        """
    else:  # MySQL
        return """
            CREATE TABLE IF NOT EXISTS daily_news (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                news_id VARCHAR(128) NOT NULL,
                source_platform VARCHAR(32) NOT NULL,
                title VARCHAR(500) NOT NULL,
                url VARCHAR(1024),
                description TEXT,
                crawl_date DATE NOT NULL,
                rank_position INT,
                add_ts BIGINT NOT NULL,
                last_modify_ts BIGINT NOT NULL,
                INDEX idx_date (crawl_date),
                INDEX idx_source (source_platform)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """


async def refresh_news() -> Dict[str, int]:
    """完整刷新流程：采集 → 入库"""
    print(f"\n📰 开始采集 {len(SOURCES)} 个平台的热榜数据...")
    print("=" * 50)

    items = await collect_all_news()
    print("=" * 50)
    print(f"✅ 共采集 {len(items)} 条热榜数据")

    if items:
        print("\n💾 写入数据库...")
        count = await save_to_db(items)
        print(f"✅ 已写入 {count} 条到 daily_news 表")

        # 统计各源数量
        from collections import Counter
        counter = Counter(i["source_name"] for i in items)
        print("\n📊 按平台统计：")
        for name, n in sorted(counter.items(), key=lambda x: -x[1]):
            print(f"   {name:12s} {n:4d} 条")

    return {"total": len(items), "sources": len(SOURCES)}


# ===== 查询辅助函数（供 InsightAgent 使用或单独调用）=====

async def get_latest_news_by_source(source: str, limit: int = 20) -> List[Dict[str, Any]]:
    """查询某个平台的最新热榜（从 daily_news 表）"""
    from .db_query_tools import _get_engine, _wrap_field
    engine = _get_engine()
    query = f"""
        SELECT title, url, rank_position, crawl_date
        FROM daily_news
        WHERE source_platform = :src
        ORDER BY crawl_date DESC, rank_position ASC
        LIMIT :limit
    """
    async with engine.connect() as conn:
        result = await conn.execute(text(query), {"src": source, "limit": limit})
        return [dict(row) for row in result.mappings().all()]


async def search_news_title(keyword: str, limit: int = 30) -> List[Dict[str, Any]]:
    """按标题关键词搜索最近的热榜新闻"""
    from .db_query_tools import _get_engine
    engine = _get_engine()
    query = f"""
        SELECT source_platform, title, url, rank_position, crawl_date
        FROM daily_news
        WHERE title LIKE :kw
        ORDER BY crawl_date DESC, rank_position ASC
        LIMIT :limit
    """
    async with engine.connect() as conn:
        result = await conn.execute(text(query), {"kw": f"%{keyword}%", "limit": limit})
        return [dict(row) for row in result.mappings().all()]


# ===== 命令行入口 =====

if __name__ == "__main__":
    import sys
    from pathlib import Path
    # 确保能导入 config
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    asyncio.run(refresh_news())
