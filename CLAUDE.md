# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

agno-mirofish is a multi-agent sentiment/opinion analysis system migrated from [BettaFish](https://github.com/666ghj/BettaFish) to the [Agno](https://github.com/agno-agi/agno) framework. Three teams develop in parallel with defined contracts. I have downloaded the original code in /Users/xujing/Desktop/xinxisuo/agno_mirofish/BettaFish.

## Architecture

Three-layer architecture with strict interface contracts (see `interfaces.md`):

```
agno_tools/  (A group)  →  agno_agents/  (B group)  →  agno_team/ + main.py  (C group)
   Data & Tools               Core Agents                Orchestration & API
```

**Agents** (all share the same 3-stage workflow: Plan → Search+Summarize+Reflect → Format):
- **InsightAgent**: Social media sentiment analysis via local DB tools (Weibo/Bilibili/Zhihu/Tieba). Uses Moonshot Kimi-K2.
- **MediaAgent**: Multi-modal web content analysis (text + images + structured data). Uses Gemini-2.5-Pro.
- **QueryAgent**: News fact-checking and multi-source verification. Uses DeepSeek Chat.

All three agents return `AnalysisResult` (defined in `agno_agents/models.py`), which contains structured `paragraphs` for ForumEngine consumption and a `final_report` Markdown string for ReportEngine.

**Key shared models** (`agno_agents/models.py`): `SearchDecision`, `ReportStructure`, `ParagraphResult`, `AnalysisResult` — used by agents, forum, and report layers.

**Config** (`config.py`): Pydantic-settings with `.env` auto-load. Each engine has separate `*_API_KEY`, `*_BASE_URL`, `*_MODEL_NAME` settings.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask app
python main.py

# Run integration tests (validates all three layers)
python -m pytest test_integration.py -v

# Run a single test class
python -m pytest test_integration.py::TestAgentLayer -v
```

## Development Notes

- Tools in `agno_tools/` are currently stubs (TODO markers). Each agent file has commented-out imports that should be uncommented when A group delivers real implementations.
- Each agent's `instructions` prompt embeds the **original BettaFish JSON Schemas** verbatim (INPUT/OUTPUT JSON SCHEMA blocks). Do not remove these — they drive the multi-stage workflow and are consumed by ForumEngine's log parser.
- Agents use `response_model=AnalysisResult` for type-safe structured output via Agno's pydantic integration.
- The `agno_team/opinion_team.py` orchestrates all three agents in parallel and feeds results to a ReportAgent. The `forum_agent.py` provides real-time commentary during analysis.
- `main.py` uses Flask + Socket.IO for real-time frontend communication.

## Git Conventions

- Do NOT add `Co-Authored-By` lines in commits.
- Remote `origin` = GitHub (`NextE-Moffatt/agno-mirofish`)
