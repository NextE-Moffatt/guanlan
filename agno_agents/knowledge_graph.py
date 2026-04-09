# agno_agents/knowledge_graph.py
# 知识图谱提取：从完整的综合报告中抽取实体与关系
#
# 输出的 JSON 结构会被存到 reports/web/{task_id}/graph.json，
# 前端用 vis.js 渲染成可交互的关系网络图。

from __future__ import annotations
import json
import re
from typing import Dict, Any, List, Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat


# ============== Prompt ==============

GRAPH_EXTRACT_PROMPT = """你是一位专业的知识图谱工程师。请从以下舆情分析报告中提取**核心实体**和它们之间的**关系**，生成一份可视化的知识图谱。

**报告主题**：{query}

**报告内容**（节选）：
{report_content}

---

## 提取要求

### 1. 实体（entities）

从报告中识别最重要的 **15-30 个**核心实体（不要太多，宁缺毋滥）。每个实体需要提供：

- `id`: 英文或拼音的唯一标识（如 "anthropic" / "claude_code" / "open_ai"，全小写，下划线分隔）
- `name`: 实体的中文显示名（或原文名，如 "Anthropic" / "Claude Code"）
- `type`: **严格**从以下枚举选择一个：
  - `person` — 人物（创始人、CEO、关键人物）
  - `organization` — 公司、机构、团队
  - `product` — 产品、工具、模型、软件
  - `event` — 事件（发布、争议、危机、合作等）
  - `location` — 地点、国家、城市
  - `topic` — 话题、概念、趋势
- `description`: 一句话描述（30 字以内）
- `weight`: 重要度 1-10（在报告中被提及次数越多、讨论越深入的越重要）
- `sentiment`: 舆情态度，枚举 `positive` / `negative` / `neutral` / `mixed`

### 2. 关系（relations）

识别实体之间的关系，每个关系需要：

- `source`: 源实体 id（必须在 entities 里出现过）
- `target`: 目标实体 id（必须在 entities 里出现过）
- `type`: 关系类型（中文短语，2-6 字），例如：发布、开发、收购、合作、竞争、批评、支持、参与、发生于、导致、包含、基于、反对
- `evidence`: 一句话证据（从报告中提取，不超过 80 字）
- `strength`: 关系强度 1-5（基于证据充分程度和重要性）

关系数量控制在 **20-40 个**。优先选择：
- 对理解主题最关键的关系
- 报告中有明确证据支持的关系
- 能构成清晰网络的关系（避免孤立节点）

### 3. 质量要求

- **实体去重**：同一个概念只出现一次（比如 "Anthropic 公司"/"Anthropic"/"Anthropic 团队" 合并为一个）
- **关系双向**：如果 A 发布 B，通常不再加 B 被 A 发布（避免重复）
- **避免空泛**：不要提取"AI"、"技术"、"社区"这种过于宽泛的实体
- **聚焦核心**：围绕报告主题组织图谱，边缘话题可以省略

---

## 输出格式（严格 JSON，不要任何 markdown 代码块包裹）

```
{{
  "entities": [
    {{
      "id": "anthropic",
      "name": "Anthropic",
      "type": "organization",
      "description": "Claude 模型背后的 AI 安全研究公司",
      "weight": 10,
      "sentiment": "neutral"
    }}
  ],
  "relations": [
    {{
      "source": "anthropic",
      "target": "claude_code",
      "type": "发布",
      "evidence": "Anthropic 于 2025 年 2 月正式发布 Claude Code 作为命令行 AI 编程助手",
      "strength": 5
    }}
  ]
}}
```

只返回 JSON，不要任何解释、不要 markdown 代码块。"""


# ============== 提取器 ==============

class KnowledgeGraphExtractor:
    """知识图谱提取器"""

    def __init__(self, config=None):
        if config is None:
            from config import settings
            config = settings

        # 复用 REPORT_ENGINE 的配置（图谱提取也是生成任务）
        if config.REPORT_ENGINE_API_KEY:
            api_key = config.REPORT_ENGINE_API_KEY
            base_url = config.REPORT_ENGINE_BASE_URL
            model_name = config.REPORT_ENGINE_MODEL_NAME
        elif config.FORUM_HOST_API_KEY:
            api_key = config.FORUM_HOST_API_KEY
            base_url = config.FORUM_HOST_BASE_URL
            model_name = config.FORUM_HOST_MODEL_NAME
        elif config.QUERY_ENGINE_API_KEY:
            api_key = config.QUERY_ENGINE_API_KEY
            base_url = config.QUERY_ENGINE_BASE_URL
            model_name = config.QUERY_ENGINE_MODEL_NAME
        else:
            raise ValueError("知识图谱提取需要至少一个可用的 LLM API key")

        self.agent = Agent(
            name="KnowledgeGraphExtractor",
            model=OpenAIChat(
                id=model_name,
                api_key=api_key,
                base_url=base_url,
                role_map={
                    "system": "system",
                    "user": "user",
                    "assistant": "assistant",
                    "tool": "tool",
                    "model": "assistant",
                },
            ),
            instructions="你是一位专业的知识图谱工程师，严格输出 JSON 格式。",
            system_message_role="system",
            markdown=False,
        )

    async def extract(self, query: str, report_content: str) -> Dict[str, Any]:
        """
        从报告内容中提取知识图谱。

        Args:
            query: 原始分析主题
            report_content: 完整的报告 Markdown 文本

        Returns:
            dict: {
                "entities": [...],
                "relations": [...],
                "stats": {...}
            }
        """
        # 截断报告：太长会导致 LLM token 爆炸
        # 取前 12000 字 + 后 3000 字（开头有执行摘要，结尾有跨源验证）
        if len(report_content) > 15000:
            head = report_content[:12000]
            tail = report_content[-3000:]
            report_excerpt = head + "\n\n...(中间部分省略)...\n\n" + tail
        else:
            report_excerpt = report_content

        prompt = GRAPH_EXTRACT_PROMPT.format(
            query=query,
            report_content=report_excerpt,
        )

        print("\n🕸️  [Graph] 提取知识图谱中...")
        try:
            response = await self.agent.arun(prompt)
            raw = response.content if response else ""
        except Exception as e:
            print(f"⚠️  [Graph] 提取失败: {e}")
            return _empty_graph()

        graph = _parse_graph_json(raw)
        if not graph or not graph.get("entities"):
            print("⚠️  [Graph] 解析失败，返回空图谱")
            return _empty_graph()

        # 后处理：清洗和验证
        graph = _sanitize_graph(graph)
        graph["stats"] = {
            "entity_count": len(graph["entities"]),
            "relation_count": len(graph["relations"]),
            "entity_types": _count_types(graph["entities"]),
        }

        print(f"✅ [Graph] 提取到 {len(graph['entities'])} 个实体，{len(graph['relations'])} 条关系")
        return graph


# ============== 辅助函数 ==============

def _empty_graph() -> Dict[str, Any]:
    return {
        "entities": [],
        "relations": [],
        "stats": {"entity_count": 0, "relation_count": 0, "entity_types": {}},
    }


def _parse_graph_json(text: str) -> Optional[Dict[str, Any]]:
    """容错解析 LLM 输出的 JSON"""
    text = (text or "").strip()
    # 剥 markdown 代码块
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取 {...} 部分
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


def _sanitize_graph(graph: Dict[str, Any]) -> Dict[str, Any]:
    """清洗图谱数据：验证字段、去重、过滤孤立关系"""
    valid_entity_types = {"person", "organization", "product", "event", "location", "topic"}
    valid_sentiments = {"positive", "negative", "neutral", "mixed"}

    # 1. 清洗实体
    seen_ids = set()
    clean_entities = []
    for e in graph.get("entities", []):
        if not isinstance(e, dict):
            continue
        eid = str(e.get("id", "")).strip().lower()
        if not eid or eid in seen_ids:
            continue
        seen_ids.add(eid)

        etype = e.get("type", "topic")
        if etype not in valid_entity_types:
            etype = "topic"

        sentiment = e.get("sentiment", "neutral")
        if sentiment not in valid_sentiments:
            sentiment = "neutral"

        try:
            weight = int(e.get("weight", 5))
        except (TypeError, ValueError):
            weight = 5
        weight = max(1, min(10, weight))

        clean_entities.append({
            "id": eid,
            "name": str(e.get("name", eid))[:40],
            "type": etype,
            "description": str(e.get("description", ""))[:120],
            "weight": weight,
            "sentiment": sentiment,
        })

    # 2. 清洗关系：source 和 target 必须都在实体列表里
    entity_ids = {e["id"] for e in clean_entities}
    clean_relations = []
    seen_relation_keys = set()
    for r in graph.get("relations", []):
        if not isinstance(r, dict):
            continue
        src = str(r.get("source", "")).strip().lower()
        tgt = str(r.get("target", "")).strip().lower()
        if not src or not tgt or src not in entity_ids or tgt not in entity_ids:
            continue
        if src == tgt:
            continue

        # 去重（同一对实体的同一种关系只保留一条）
        rtype = str(r.get("type", "相关"))[:20]
        key = (src, tgt, rtype)
        if key in seen_relation_keys:
            continue
        seen_relation_keys.add(key)

        try:
            strength = int(r.get("strength", 3))
        except (TypeError, ValueError):
            strength = 3
        strength = max(1, min(5, strength))

        clean_relations.append({
            "source": src,
            "target": tgt,
            "type": rtype,
            "evidence": str(r.get("evidence", ""))[:160],
            "strength": strength,
        })

    return {
        "entities": clean_entities,
        "relations": clean_relations,
    }


def _count_types(entities: List[Dict[str, Any]]) -> Dict[str, int]:
    """统计各类型实体数量"""
    counter: Dict[str, int] = {}
    for e in entities:
        t = e.get("type", "topic")
        counter[t] = counter.get(t, 0) + 1
    return counter
