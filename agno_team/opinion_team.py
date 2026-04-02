# agno_team/opinion_team.py
# TODO(C组): 用 agno Team 编排所有 Agent
# 替代原 app.py 中的多引擎调度逻辑

from agno.team import Team
from agno.models.openai import OpenAIChat


def create_opinion_team(config=None):
    """
    创建舆情分析 Team，编排所有 Agent 的协作流程。
    替代原 app.py 的引擎调度逻辑。

    工作流程：
    1. 协调者收到分析主题
    2. 并行触发 InsightAgent、MediaAgent、QueryAgent
    3. 三个分析完成后，交给 ReportAgent 生成综合报告
    4. 返回最终报告路径

    Args:
        config: Settings 对象，为 None 时从全局 settings 读取
    """
    if config is None:
        from config import settings
        config = settings

    # TODO(C组): B组完成后取消注释并引入真实 Agent
    # from agno_agents import create_insight_agent, create_media_agent, create_query_agent
    # from agno_agents.report_agent import create_report_agent
    # insight_agent = create_insight_agent(config)
    # media_agent = create_media_agent(config)
    # query_agent = create_query_agent(config)
    # report_agent = create_report_agent(config)

    team = Team(
        name="微舆舆情分析团队",
        mode="coordinate",
        model=OpenAIChat(
            id=config.INSIGHT_ENGINE_MODEL_NAME,
            api_key=config.INSIGHT_ENGINE_API_KEY,
            base_url=config.INSIGHT_ENGINE_BASE_URL,
        ),
        members=[],  # TODO(C组): 填入上方四个 agent
        instructions="""
你是舆情分析团队的协调者。收到分析主题后：
1. 同时向 InsightAgent、MediaAgent、QueryAgent 发布分析任务
2. 等待三个 Agent 完成各自的分析
3. 将三份分析报告汇总后，交给 ReportAgent 生成综合 HTML 报告
4. 返回最终报告的文件路径给用户
""",
        markdown=True,
        stream=True,
        show_tool_calls=True,
    )
    return team


def run_opinion_analysis(topic: str, config=None) -> str:
    """
    执行完整舆情分析流程。
    替代原 app.py 的任务调度入口。

    Args:
        topic: 分析主题，如 "某品牌产品质量危机"
    Returns:
        综合报告 HTML 文件路径，或最终报告内容
    """
    team = create_opinion_team(config)
    response = team.run(f"请对以下主题进行全面的舆情分析：{topic}")
    return response.content
