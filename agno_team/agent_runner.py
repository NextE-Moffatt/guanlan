# agno_team/agent_runner.py
# 单个 Agent 的多步流程编排（async 版本）
# 提取自 run_single_agent.py，加入 ForumState 集成
#
# 关键变化：
# 1. 所有 LLM/工具调用通过 asyncio.to_thread 包装，避免阻塞 event loop
# 2. 每个段落的 SummaryNode 步骤之前会读取 ForumState 的最新 HOST 发言
# 3. 段落产出后会写入 ForumState（触发 Host 阈值检查）

from __future__ import annotations
import asyncio
import json
import re
from typing import List, Dict, Any, Optional

from openai import OpenAI

from .forum_state import ForumState, format_host_speech_for_prompt


# ===== LLM 客户端缓存 =====

_clients_cache: Dict[str, tuple] = {}


def _get_client(config_prefix: str):
    """获取或创建 OpenAI client + model_name（按 engine 缓存）"""
    if config_prefix in _clients_cache:
        return _clients_cache[config_prefix]

    from config import settings
    api_key = getattr(settings, f"{config_prefix}_API_KEY")
    base_url = getattr(settings, f"{config_prefix}_BASE_URL")
    model_name = getattr(settings, f"{config_prefix}_MODEL_NAME")

    if not api_key:
        raise ValueError(f"{config_prefix}_API_KEY 未配置")

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=600)
    _clients_cache[config_prefix] = (client, model_name)
    return client, model_name


def _call_llm_sync(client, model_name: str, system_prompt: str, user_content: str) -> str:
    """同步 LLM 调用（内部使用，外部用 _call_llm 异步包装）"""
    stream = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
        stream=True,
    )
    chunks = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            chunks.append(delta)
    return "".join(chunks)


async def _call_llm(client, model_name: str, system_prompt: str, user_content: str) -> str:
    """异步 LLM 调用，自动卸到线程池"""
    return await asyncio.to_thread(_call_llm_sync, client, model_name, system_prompt, user_content)


def _parse_json(text: str) -> Optional[Any]:
    """容错解析 LLM 返回的 JSON"""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*?\}", text) or re.search(r"\[[\s\S]*?\]", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None


# ===== 工具调用调度 =====

async def _call_tool_async(agent_type: str, decision: Dict[str, Any], default_topic: str) -> str:
    """根据 decision 字典调用对应的工具（异步包装同步工具）"""
    tool_name = decision.get("search_tool", "")
    search_query = decision.get("search_query", default_topic)

    if agent_type == "query":
        from agno_tools import call_news_tool
        tool_kwargs = {"query": search_query}
        if tool_name == "search_news_by_date":
            tool_kwargs["start_date"] = decision.get("start_date", "")
            tool_kwargs["end_date"] = decision.get("end_date", "")
        if not tool_name:
            tool_name = "basic_search_news"
        return await asyncio.to_thread(call_news_tool, tool_name, **tool_kwargs)

    elif agent_type == "media":
        from agno_tools import call_media_tool
        tool_kwargs = {"query": search_query}
        if not tool_name:
            tool_name = "comprehensive_search"
        return await asyncio.to_thread(call_media_tool, tool_name, **tool_kwargs)

    elif agent_type == "insight":
        # 国内本地数据库工具
        domestic_tools = {
            "search_hot_content", "search_topic_globally", "search_topic_by_date",
            "get_comments_for_topic", "search_topic_on_platform", "analyze_sentiment",
        }
        # 海外工具
        overseas_tools = {
            "search_hackernews", "search_hackernews_recent", "search_hackernews_comments",
            "search_github_repos", "search_github_issues", "search_github_code",
            "search_youtube_videos", "get_youtube_comments", "search_youtube_with_comments",
            "search_reddit", "get_subreddit_hot", "get_reddit_post_comments",
        }

        if tool_name in overseas_tools:
            from agno_tools import call_overseas_tool
            # 海外工具的参数命名是 query 而不是 topic
            tool_kwargs = {"query": search_query}
            if tool_name == "search_reddit":
                if decision.get("subreddit"):
                    tool_kwargs["subreddit"] = decision["subreddit"]
                tool_kwargs["sort"] = decision.get("sort", "relevance")
            elif tool_name == "get_subreddit_hot":
                tool_kwargs = {
                    "subreddit": decision.get("subreddit", "programming"),
                    "time_filter": decision.get("time_filter", "week"),
                }
            elif tool_name == "get_youtube_comments":
                tool_kwargs = {"video_id": decision.get("video_id", "")}
            elif tool_name == "get_reddit_post_comments":
                tool_kwargs = {
                    "post_id": decision.get("post_id", ""),
                    "subreddit": decision.get("subreddit", ""),
                }
            return await asyncio.to_thread(call_overseas_tool, tool_name, **tool_kwargs)

        # 国内工具（默认路径）
        from agno_tools import call_insight_tool
        tool_kwargs = {"topic": search_query}
        if tool_name == "search_topic_by_date":
            tool_kwargs["start_date"] = decision.get("start_date", "")
            tool_kwargs["end_date"] = decision.get("end_date", "")
        elif tool_name == "search_topic_on_platform":
            tool_kwargs["platform"] = decision.get("platform", "weibo")
            if decision.get("start_date"):
                tool_kwargs["start_date"] = decision.get("start_date")
                tool_kwargs["end_date"] = decision.get("end_date", "")
        elif tool_name == "search_hot_content":
            tool_kwargs = {"time_period": decision.get("time_period", "week")}
        elif tool_name == "analyze_sentiment":
            tool_kwargs = {"texts": decision.get("texts") or [search_query]}
        if not tool_name or tool_name not in domestic_tools:
            tool_name = "search_topic_globally"
        return await asyncio.to_thread(call_insight_tool, tool_name, **tool_kwargs)

    return f"未知 agent_type: {agent_type}"


# ===== 单 Agent 完整流程（异步版）=====

AGENT_CONFIG = {
    "insight": ("InsightAgent", "INSIGHT_ENGINE", "INSIGHT"),
    "media":   ("MediaAgent",   "MEDIA_ENGINE",   "MEDIA"),
    "query":   ("QueryAgent",   "QUERY_ENGINE",   "QUERY"),
}


async def run_agent_pipeline(
    agent_type: str,
    query: str,
    forum_state: Optional[ForumState] = None,
) -> Dict[str, Any]:
    """
    异步运行单个 Agent 的完整三阶段流程：
    1. 规划报告结构
    2. 逐段：搜索决策 → 工具调用 → 撰写初稿 → 反思 → 补充搜索 → 深化
    3. 最终格式化报告

    在每个段落的 SummaryNode 之前会读取 forum_state 的最新 HOST 发言，
    塞进 prompt 前缀作为引导；段落产出后写入 forum_state。

    Returns:
        dict: {
            "agent_type": str,
            "agent_name": str,
            "query": str,
            "paragraphs": List[{"title": str, "paragraph_latest_state": str}],
            "final_report": str,
        }
    """
    if agent_type not in AGENT_CONFIG:
        raise ValueError(f"未知 agent_type: {agent_type}")

    agent_name, config_prefix, forum_role = AGENT_CONFIG[agent_type]
    client, model_name = _get_client(config_prefix)

    # 检测可用的海外工具（仅 insight 需要）
    overseas_extra = ""
    if agent_type == "insight":
        from config import settings
        from agno_agents.insight_agent import _detect_available_overseas, _build_overseas_section
        available = _detect_available_overseas(settings)
        overseas_extra = _build_overseas_section(available)

    # 动态导入对应 agent 的 prompt
    if agent_type == "insight":
        from agno_agents.insight_agent import (
            SYSTEM_PROMPT_REPORT_STRUCTURE,
            SYSTEM_PROMPT_FIRST_SEARCH,
            SYSTEM_PROMPT_FIRST_SUMMARY,
            SYSTEM_PROMPT_REFLECTION,
            SYSTEM_PROMPT_REFLECTION_SUMMARY,
            SYSTEM_PROMPT_REPORT_FORMATTING,
        )
    elif agent_type == "media":
        from agno_agents.media_agent import (
            SYSTEM_PROMPT_REPORT_STRUCTURE,
            SYSTEM_PROMPT_FIRST_SEARCH,
            SYSTEM_PROMPT_FIRST_SUMMARY,
            SYSTEM_PROMPT_REFLECTION,
            SYSTEM_PROMPT_REFLECTION_SUMMARY,
            SYSTEM_PROMPT_REPORT_FORMATTING,
        )
    else:
        from agno_agents.query_agent import (
            SYSTEM_PROMPT_REPORT_STRUCTURE,
            SYSTEM_PROMPT_FIRST_SEARCH,
            SYSTEM_PROMPT_FIRST_SUMMARY,
            SYSTEM_PROMPT_REFLECTION,
            SYSTEM_PROMPT_REFLECTION_SUMMARY,
            SYSTEM_PROMPT_REPORT_FORMATTING,
        )

    print(f"\n🚀 [{agent_name}] 启动，主题: {query}")

    # ===== 阶段一：规划报告结构 =====
    structure_raw = await _call_llm(client, model_name, SYSTEM_PROMPT_REPORT_STRUCTURE, query)
    paragraphs_outline = _parse_json(structure_raw)
    if not isinstance(paragraphs_outline, list):
        paragraphs_outline = []

    print(f"📋 [{agent_name}] 规划了 {len(paragraphs_outline)} 个段落")

    # ===== 阶段二：逐段搜索 + 总结 + 反思 =====
    paragraph_results: List[Dict[str, str]] = []

    for idx, para in enumerate(paragraphs_outline, 1):
        if not isinstance(para, dict):
            continue
        title = para.get("title", "")
        content = para.get("content", "")
        para_input = json.dumps({"title": title, "content": content}, ensure_ascii=False)

        print(f"🔍 [{agent_name}] 段落 {idx}/{len(paragraphs_outline)}: {title}")

        # 2a. 首次搜索决策（insight 类型在 system prompt 末尾追加海外平台说明）
        search_system = SYSTEM_PROMPT_FIRST_SEARCH + (overseas_extra if overseas_extra else "")
        search_decision_raw = await _call_llm(client, model_name, search_system, para_input)
        decision = _parse_json(search_decision_raw)

        # 2b. 调用真实工具
        search_results = f"（无搜索结果：{title}）"
        if isinstance(decision, dict):
            try:
                search_results = await _call_tool_async(agent_type, decision, title)
            except Exception as e:
                search_results = f"工具调用失败: {e}"

        # 2c. 读取 HOST 引导发言并撰写初稿
        host_hint = forum_state.get_latest_host_speech() if forum_state else None
        host_prefix = format_host_speech_for_prompt(host_hint) if host_hint else ""

        summary_input = host_prefix + json.dumps({
            "title": title,
            "content": content,
            "search_query": query,
            "search_results": [search_results],
        }, ensure_ascii=False)

        summary_raw = await _call_llm(client, model_name, SYSTEM_PROMPT_FIRST_SUMMARY, summary_input)
        summary_data = _parse_json(summary_raw)
        paragraph_state = (
            summary_data.get("paragraph_latest_state", summary_raw)
            if isinstance(summary_data, dict)
            else summary_raw
        )

        # ⭐ 写入 forum_state（可能触发 Host）
        if forum_state is not None:
            await forum_state.write(forum_role, paragraph_state)

        # 2d. 反思：基于当前段落生成补充搜索
        reflection_input = json.dumps({
            "title": title,
            "content": content,
            "paragraph_latest_state": paragraph_state,
        }, ensure_ascii=False)

        reflection_system = SYSTEM_PROMPT_REFLECTION + (overseas_extra if overseas_extra else "")
        reflection_raw = await _call_llm(client, model_name, reflection_system, reflection_input)
        ref_decision = _parse_json(reflection_raw)

        ref_search_results = f"（无补充搜索结果：{title}）"
        if isinstance(ref_decision, dict):
            try:
                ref_search_results = await _call_tool_async(agent_type, ref_decision, title)
            except Exception as e:
                ref_search_results = f"补充搜索失败: {e}"

        # 2e. 反思总结：再次读取 HOST 引导，深化段落
        host_hint2 = forum_state.get_latest_host_speech() if forum_state else None
        host_prefix2 = format_host_speech_for_prompt(host_hint2) if host_hint2 else ""

        ref_summary_input = host_prefix2 + json.dumps({
            "title": title,
            "content": content,
            "search_query": query,
            "search_results": [ref_search_results],
            "paragraph_latest_state": paragraph_state,
        }, ensure_ascii=False)

        ref_summary_raw = await _call_llm(client, model_name, SYSTEM_PROMPT_REFLECTION_SUMMARY, ref_summary_input)
        ref_summary_data = _parse_json(ref_summary_raw)
        final_state = (
            ref_summary_data.get("updated_paragraph_latest_state", paragraph_state)
            if isinstance(ref_summary_data, dict)
            else paragraph_state
        )

        # ⭐ 深化后的段落再次写入 forum_state
        if forum_state is not None:
            await forum_state.write(forum_role, final_state)

        paragraph_results.append({
            "title": title,
            "paragraph_latest_state": final_state,
        })

    # ===== 阶段三：最终报告格式化 =====
    print(f"📝 [{agent_name}] 生成最终报告...")
    formatting_input = json.dumps(paragraph_results, ensure_ascii=False)
    final_report = await _call_llm(client, model_name, SYSTEM_PROMPT_REPORT_FORMATTING, formatting_input)

    print(f"✅ [{agent_name}] 完成（{len(final_report)} 字）")

    return {
        "agent_type": agent_type,
        "agent_name": agent_name,
        "query": query,
        "paragraphs": paragraph_results,
        "final_report": final_report,
    }
