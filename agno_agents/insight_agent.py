# agno_agents/insight_agent.py
# TODO(B组): 迁移自 InsightEngine/agent.py (DeepSearchAgent)
# 重点：保留反思循环逻辑，将 nodes/ 的多步流程整合进 instructions

from agno.agent import Agent
from agno.models.openai import OpenAIChat

# TODO(B组): A组完成后取消注释
# from agno_tools import search_weibo, search_forum, search_news, analyze_sentiment, optimize_keywords

INSIGHT_SYSTEM_PROMPT = """
# TODO(B组): 从 InsightEngine/prompts/ 迁移完整 prompt
# 需要整合以下原始 prompt：
# - SYSTEM_PROMPT_FIRST_SEARCH（首次搜索指令）
# - SYSTEM_PROMPT_REFLECTION（反思判断指令）
# - SYSTEM_PROMPT_REPORT_STRUCTURE（报告结构规划）
# - SYSTEM_PROMPT_FORMATTING（最终格式化）
# 整合为一段连贯的工作流指令
"""


def create_insight_agent(config=None):
    """
    创建 InsightAgent 实例。
    替代原 DeepSearchAgent.__init__()

    Args:
        config: Settings 对象，为 None 时从全局 settings 读取
    """
    if config is None:
        from config import settings
        config = settings

    return Agent(
        name="InsightAgent",
        model=OpenAIChat(
            id=config.INSIGHT_ENGINE_MODEL_NAME,
            api_key=config.INSIGHT_ENGINE_API_KEY,
            base_url=config.INSIGHT_ENGINE_BASE_URL,
        ),
        # TODO(B组): A组完成后替换为真实工具
        tools=[],
        instructions=INSIGHT_SYSTEM_PROMPT,
        markdown=True,
        stream=True,
        show_tool_calls=True,
    )


def run_insight_analysis(query: str, config=None) -> str:
    """
    执行深度洞察分析。
    替代原 DeepSearchAgent.run(query)

    Args:
        query: 用户分析主题，如 "某热点事件舆情分析"
    Returns:
        完整的 Markdown 格式分析报告
    """
    agent = create_insight_agent(config)
    response = agent.run(query)
    return response.content
