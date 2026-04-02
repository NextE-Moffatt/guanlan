# agno_agents/query_agent.py
# TODO(B组): 迁移自 QueryEngine/agent.py
# 负责舆情数据的快速查询和检索

from agno.agent import Agent
from agno.models.openai import OpenAIChat

# TODO(B组): A组完成后取消注释
# from agno_tools import search_weibo, search_forum, search_news

QUERY_SYSTEM_PROMPT = """
# TODO(B组): 从 QueryEngine/prompts/ 迁移完整 prompt
"""


def create_query_agent(config=None):
    """
    创建 QueryAgent 实例。

    Args:
        config: Settings 对象，为 None 时从全局 settings 读取
    """
    if config is None:
        from config import settings
        config = settings

    return Agent(
        name="QueryAgent",
        model=OpenAIChat(
            id=config.QUERY_ENGINE_MODEL_NAME,
            api_key=config.QUERY_ENGINE_API_KEY,
            base_url=config.QUERY_ENGINE_BASE_URL,
        ),
        tools=[],  # TODO(B组): A组完成后替换为真实工具
        instructions=QUERY_SYSTEM_PROMPT,
        markdown=True,
        stream=True,
        show_tool_calls=True,
    )


def run_query(query: str, config=None) -> str:
    """
    执行数据查询。
    替代原 QueryEngine agent.run(query)

    Args:
        query: 查询问题
    Returns:
        Markdown 格式查询结果
    """
    agent = create_query_agent(config)
    response = agent.run(query)
    return response.content
