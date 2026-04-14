-- 观澜 · PostgreSQL 数据库初始化脚本
-- 创建 InsightAgent 所需的 15 张表（7 内容表 + 7 评论表 + daily_news）
-- 使用方法：
--   createdb yuqing
--   psql -U postgres -d yuqing -f scripts/init_postgres.sql

-- ===================== 内容表 =====================

DROP TABLE IF EXISTS weibo_note CASCADE;
CREATE TABLE weibo_note (
    id SERIAL PRIMARY KEY,
    content TEXT,
    source_keyword VARCHAR(128),
    create_date_time TIMESTAMP,
    nickname VARCHAR(128),
    note_url VARCHAR(1024),
    liked_count INTEGER,
    comments_count INTEGER,
    shared_count INTEGER
);
CREATE INDEX idx_weibo_note_kw ON weibo_note(source_keyword);
CREATE INDEX idx_weibo_note_time ON weibo_note(create_date_time);

DROP TABLE IF EXISTS xhs_note CASCADE;
CREATE TABLE xhs_note (
    id SERIAL PRIMARY KEY,
    title VARCHAR(512),
    "desc" TEXT,
    tag_list TEXT,
    source_keyword VARCHAR(128),
    "time" BIGINT,
    nickname VARCHAR(128),
    note_url VARCHAR(1024),
    liked_count INTEGER,
    comment_count INTEGER,
    share_count INTEGER,
    collected_count INTEGER
);
CREATE INDEX idx_xhs_note_kw ON xhs_note(source_keyword);

DROP TABLE IF EXISTS zhihu_content CASCADE;
CREATE TABLE zhihu_content (
    id SERIAL PRIMARY KEY,
    title VARCHAR(512),
    "desc" TEXT,
    content_text TEXT,
    source_keyword VARCHAR(128),
    created_time VARCHAR(32),
    user_nickname VARCHAR(128),
    content_url VARCHAR(1024),
    voteup_count INTEGER,
    comment_count INTEGER
);
CREATE INDEX idx_zhihu_content_kw ON zhihu_content(source_keyword);

DROP TABLE IF EXISTS bilibili_video CASCADE;
CREATE TABLE bilibili_video (
    id SERIAL PRIMARY KEY,
    title VARCHAR(512),
    "desc" TEXT,
    source_keyword VARCHAR(128),
    create_time BIGINT,
    nickname VARCHAR(128),
    video_url VARCHAR(1024),
    liked_count INTEGER,
    video_comment INTEGER,
    video_share_count INTEGER,
    video_play_count BIGINT,
    video_favorite_count INTEGER,
    video_coin_count INTEGER,
    video_danmaku INTEGER
);
CREATE INDEX idx_bili_video_kw ON bilibili_video(source_keyword);

DROP TABLE IF EXISTS douyin_aweme CASCADE;
CREATE TABLE douyin_aweme (
    id SERIAL PRIMARY KEY,
    title VARCHAR(512),
    "desc" TEXT,
    source_keyword VARCHAR(128),
    create_time BIGINT,
    nickname VARCHAR(128),
    aweme_url VARCHAR(1024),
    liked_count INTEGER,
    comment_count INTEGER,
    share_count INTEGER,
    collected_count INTEGER
);
CREATE INDEX idx_douyin_aweme_kw ON douyin_aweme(source_keyword);

DROP TABLE IF EXISTS kuaishou_video CASCADE;
CREATE TABLE kuaishou_video (
    id SERIAL PRIMARY KEY,
    title VARCHAR(512),
    "desc" TEXT,
    source_keyword VARCHAR(128),
    create_time BIGINT,
    nickname VARCHAR(128),
    video_url VARCHAR(1024),
    liked_count INTEGER,
    viewd_count INTEGER
);
CREATE INDEX idx_kuaishou_video_kw ON kuaishou_video(source_keyword);

DROP TABLE IF EXISTS tieba_note CASCADE;
CREATE TABLE tieba_note (
    id SERIAL PRIMARY KEY,
    title VARCHAR(512),
    "desc" TEXT,
    source_keyword VARCHAR(128),
    publish_time VARCHAR(32),
    nickname VARCHAR(128),
    url VARCHAR(1024)
);
CREATE INDEX idx_tieba_note_kw ON tieba_note(source_keyword);

-- ===================== 评论表 =====================

DROP TABLE IF EXISTS weibo_note_comment CASCADE;
CREATE TABLE weibo_note_comment (
    id SERIAL PRIMARY KEY,
    content TEXT,
    user_nickname VARCHAR(128),
    create_date_time TIMESTAMP,
    comment_like_count INTEGER
);

DROP TABLE IF EXISTS xhs_note_comment CASCADE;
CREATE TABLE xhs_note_comment (
    id SERIAL PRIMARY KEY,
    content TEXT,
    user_nickname VARCHAR(128),
    create_time BIGINT,
    like_count INTEGER
);

DROP TABLE IF EXISTS zhihu_comment CASCADE;
CREATE TABLE zhihu_comment (
    id SERIAL PRIMARY KEY,
    content TEXT,
    user_nickname VARCHAR(128),
    create_time BIGINT,
    like_count INTEGER
);

DROP TABLE IF EXISTS bilibili_video_comment CASCADE;
CREATE TABLE bilibili_video_comment (
    id SERIAL PRIMARY KEY,
    content TEXT,
    user_nickname VARCHAR(128),
    create_time BIGINT,
    like_count INTEGER
);

DROP TABLE IF EXISTS douyin_aweme_comment CASCADE;
CREATE TABLE douyin_aweme_comment (
    id SERIAL PRIMARY KEY,
    content TEXT,
    user_nickname VARCHAR(128),
    create_time BIGINT,
    like_count INTEGER
);

DROP TABLE IF EXISTS kuaishou_video_comment CASCADE;
CREATE TABLE kuaishou_video_comment (
    id SERIAL PRIMARY KEY,
    content TEXT,
    user_nickname VARCHAR(128),
    create_time BIGINT,
    like_count INTEGER
);

DROP TABLE IF EXISTS tieba_comment CASCADE;
CREATE TABLE tieba_comment (
    id SERIAL PRIMARY KEY,
    content TEXT,
    nickname VARCHAR(128),
    publish_time VARCHAR(32),
    like_count INTEGER
);

-- ===================== 热榜新闻表（MindSpider BroadTopicExtraction）=====================

DROP TABLE IF EXISTS daily_news CASCADE;
CREATE TABLE daily_news (
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
);
CREATE INDEX idx_daily_news_date ON daily_news(crawl_date);
CREATE INDEX idx_daily_news_source ON daily_news(source_platform);

-- ===================== 建表完成 =====================
SELECT 'Database initialized: 14 MediaCrawler tables + daily_news' AS status;
