# agno_tools/sentiment_tools.py
# TODO(A组): 迁移自 InsightEngine/tools/sentiment_analyzer.py + SentimentAnalysisModel/
# 模型使用懒加载，首次调用时初始化，避免 import 时就加载大模型

from agno.tools import tool
from typing import List, Dict, Any

_analyzer = None


def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        # TODO(A组): 替换为实际的模型加载逻辑
        # from InsightEngine.tools.sentiment_analyzer import multilingual_sentiment_analyzer
        # _analyzer = multilingual_sentiment_analyzer
        raise NotImplementedError("TODO(A组): 初始化情感分析模型")
    return _analyzer


@tool(description="对文本列表进行多语言情感分析，支持22种语言，返回正/负/中性及置信度")
def analyze_sentiment(texts: List[str]) -> List[Dict[str, Any]]:
    """
    Args:
        texts: 待分析文本列表
    Returns:
        每条文本的分析结果列表，每项包含:
        - sentiment: "positive" | "negative" | "neutral"
        - confidence: float (0~1)
        - language: 检测到的语言代码
    """
    analyzer = _get_analyzer()
    return analyzer.batch_analyze(texts)
