# agno_agents/report_agent.py
# TODO(C组): 迁移自 ReportEngine/agent.py
# 接收三个引擎的分析报告，生成综合 HTML 报告

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools import tool
from typing import List


@tool(description="列出所有可用的报告模板名称")
def list_report_templates() -> List[str]:
    """返回 ReportEngine/report_template/ 下的所有可用模板"""
    # TODO(C组): 迁移自 ReportEngine/report_template/
    raise NotImplementedError("TODO(C组)")


@tool(description="将报告 Markdown 内容渲染为 HTML 文件，返回输出文件路径")
def render_report_to_html(
    report_markdown: str,
    template_name: str,
    output_filename: str
) -> str:
    """
    Args:
        report_markdown: 完整的 Markdown 格式报告内容
        template_name: 模板名称（来自 list_report_templates 的返回值）
        output_filename: 输出文件名（不含路径，如 "report_20240101.html"）
    Returns:
        生成的 HTML 文件绝对路径
    """
    # TODO(C组): 复用 ReportEngine/renderers/HTMLRenderer
    raise NotImplementedError("TODO(C组)")


REPORT_SYSTEM_PROMPT = """
# TODO(C组): 从 ReportEngine/nodes/ 各节点的 prompt 整合完整指令
# 需要整合：模板选择、布局规划、字数预算、章节生成的指令
"""


def create_report_agent(config=None):
    """
    创建 ReportAgent 实例。

    Args:
        config: Settings 对象，为 None 时从全局 settings 读取
    """
    if config is None:
        from config import settings
        config = settings

    return Agent(
        name="ReportAgent",
        model=OpenAIChat(
            id=config.REPORT_ENGINE_MODEL_NAME,
            api_key=config.REPORT_ENGINE_API_KEY,
            base_url=config.REPORT_ENGINE_BASE_URL,
        ),
        tools=[list_report_templates, render_report_to_html],
        instructions=REPORT_SYSTEM_PROMPT,
        markdown=True,
        stream=True,
        show_tool_calls=True,
    )


def run_report_generation(
    insight_report: str,
    media_report: str,
    query_report: str,
    config=None
) -> str:
    """
    生成综合分析报告。
    替代原 ReportEngine ReportAgent.run()

    Args:
        insight_report: InsightEngine 输出的 Markdown 报告
        media_report: MediaEngine 输出的 Markdown 报告
        query_report: QueryEngine 输出的 Markdown 报告
    Returns:
        生成的 HTML 报告文件路径
    """
    agent = create_report_agent(config)
    combined_input = f"""
## InsightEngine 深度分析报告
{insight_report}

## MediaEngine 媒体分析报告
{media_report}

## QueryEngine 数据查询结果
{query_report}
"""
    response = agent.run(combined_input)
    return response.content
