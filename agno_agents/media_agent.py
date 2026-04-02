# agno_agents/media_agent.py
# TODO(B组): 迁移自 MediaEngine/agent.py
# 负责媒体报道内容的分析（新闻、自媒体等）

from agno.agent import Agent
from agno.models.openai import OpenAIChat

# TODO(B组): A组完成后取消注释
# from agno_tools import search_news, analyze_sentiment

MEDIA_SYSTEM_PROMPT = """
# TODO(B组): 从 MediaEngine/prompts/ 迁移完整 prompt
"""


def create_media_agent(config=None):
    """
    创建 MediaAgent 实例。

    Args:
        config: Settings 对象，为 None 时从全局 settings 读取
    """
    if config is None:
        from config import settings
        config = settings

    return Agent(
        name="MediaAgent",
        model=OpenAIChat(
            id=config.MEDIA_ENGINE_MODEL_NAME,
            api_key=config.MEDIA_ENGINE_API_KEY,
            base_url=config.MEDIA_ENGINE_BASE_URL,
        ),
        tools=[],  # TODO(B组): A组完成后替换为真实工具
        instructions=MEDIA_SYSTEM_PROMPT,
        markdown=True,
        stream=True,
        show_tool_calls=True,
    )


def run_media_analysis(query: str, config=None) -> str:
    """
    执行媒体内容分析。
    替代原 MediaEngine agent.run(query)

    Args:
        query: 分析主题
    Returns:
        Markdown 格式媒体分析报告
    """
    agent = create_media_agent(config)
    response = agent.run(query)
    return response.content
