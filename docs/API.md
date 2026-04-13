# 前端接口文档

> 基础地址：`http://{host}:{port}`（默认 `http://localhost:9460`）
>
> 通信方式：HTTP REST + Socket.IO 实时推送

---

## 一、REST API

### 1.1 查询当前任务状态

```
GET /api/status
```

**响应**：

```json
{
  "running": true,
  "task_id": "20260410_143025",
  "query": "Claude Code 舆情分析",
  "stage": "analyzing",
  "agent_progress": {
    "insight": { "current": 3, "total": 0, "status": "running" },
    "media":   { "current": 1, "total": 0, "status": "running" },
    "query":   { "current": 2, "total": 0, "status": "running" }
  },
  "entries_count": 6,
  "start_time": "2026-04-10T14:30:25.784581",
  "error": null
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|---|---|---|
| `running` | bool | 是否有任务在运行 |
| `task_id` | string \| null | 当前任务 ID（格式 `YYYYMMDD_HHMMSS`） |
| `query` | string \| null | 分析主题 |
| `stage` | string | `idle` / `analyzing` / `reporting` / `completed` / `failed` / `cancelled` |
| `agent_progress` | object | 三个智能体的进度 |
| `agent_progress.*.current` | int | 当前已产出的段落数 |
| `agent_progress.*.status` | string | `pending` / `running` / `done` |
| `entries_count` | int | 论坛发言总条数 |
| `start_time` | string \| null | ISO 8601 格式开始时间 |
| `error` | string \| null | 错误信息（仅在 `stage=failed` 时有值） |

---

### 1.2 启动分析任务

```
POST /api/start
Content-Type: application/json
```

**请求体**：

```json
{
  "query": "Claude Code 在中文程序员社区的舆情分析",
  "threshold": 5
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `query` | string | ✅ | 分析主题（不能为空） |
| `threshold` | int | ❌ | 主持人触发阈值（默认 5，即累计 5 条智能体段落触发一次主持人发言） |

**成功响应**（200）：

```json
{
  "ok": true,
  "task_id": "20260410_143025",
  "query": "Claude Code 在中文程序员社区的舆情分析"
}
```

**失败响应**：

| HTTP | 场景 | 响应 |
|---|---|---|
| 400 | query 为空 | `{"ok": false, "error": "请输入分析主题"}` |
| 409 | 已有任务在运行 | `{"ok": false, "error": "已有任务在运行，请等待完成"}` |

---

### 1.3 取消当前任务

```
POST /api/cancel
```

**成功响应**（200）：

```json
{
  "ok": true,
  "task_id": "20260410_143025",
  "message": "已请求取消，任务将在下一个检查点停止"
}
```

**说明**：取消不是立即生效的，任务会在当前段落 LLM 调用完成后（通常 30-60 秒内）停止。取消后 `stage` 变为 `cancelled`。

**失败响应**：

| HTTP | 场景 | 响应 |
|---|---|---|
| 400 | 没有运行中的任务 | `{"ok": false, "error": "当前没有运行中的任务"}` |
| 400 | forum_state 未创建 | `{"ok": false, "error": "无法取消（任务可能尚未真正启动）"}` |

---

### 1.4 获取论坛发言列表

```
GET /api/entries
```

**响应**：

```json
{
  "entries": [
    {
      "timestamp": 1712733025.123,
      "time_str": "14:30:25",
      "role": "INSIGHT",
      "content": "通过分析微博数据，发现 Claude Code 正面情感占比 62%..."
    },
    {
      "timestamp": 1712733085.456,
      "time_str": "14:31:25",
      "role": "HOST",
      "content": "**一、事件梳理**\n各Agent的发言显示..."
    }
  ]
}
```

**`role` 枚举值**：

| role | 说明 | UI 建议 |
|---|---|---|
| `INSIGHT` | 舆情探察智能体的段落产出 | 蓝色标签 |
| `MEDIA` | 多模态分析智能体的段落产出 | 粉色标签 |
| `QUERY` | 新闻调查智能体的段落产出 | 绿色标签 |
| `HOST` | 主持人引导发言 | 橙色/金色标签，单独区域展示 |
| `SYSTEM` | 系统消息 | 灰色 |

---

### 1.5 获取最新报告信息

```
GET /api/report/latest
```

**成功响应**（200）：

```json
{
  "ok": true,
  "task_id": "20260410_143025",
  "has_html": true,
  "has_md": true,
  "html_url": "/api/report/file/20260410_143025/final_report.html",
  "md_url": "/api/report/file/20260410_143025/final_report.md"
}
```

**失败响应**（404）：`{"ok": false, "error": "暂无报告"}`

---

### 1.6 下载/查看报告文件

```
GET /api/report/file/{task_id}/{filename}
```

**路径参数**：

| 参数 | 说明 |
|---|---|
| `task_id` | 任务 ID（如 `20260410_143025`） |
| `filename` | 文件名，可选值见下表 |

**可用文件名**：

| filename | 类型 | 说明 |
|---|---|---|
| `final_report.html` | text/html | 综合 HTML 报告（含 Chart.js 可视化） |
| `final_report.md` | text/markdown | 综合 Markdown 报告 |
| `insight_report.md` | text/markdown | 舆情探察独立报告 |
| `media_report.md` | text/markdown | 多模态分析独立报告 |
| `query_report.md` | text/markdown | 新闻调查独立报告 |
| `forum_log.txt` | text/plain | 完整论坛日志 |
| `graph.json` | application/json | 知识图谱数据 |
| `meta.json` | application/json | 任务元数据 |

**错误**：400（路径穿越）/ 404（任务或文件不存在）

---

### 1.7 获取历史任务列表

```
GET /api/history
```

**响应**：

```json
{
  "items": [
    {
      "task_id": "20260410_143025",
      "query": "Claude Code 在中文程序员社区的舆情分析",
      "title": "Claude Code中文舆情全景图：技术理想与工程现实的张力解构",
      "status": "completed",
      "created_at": "2026-04-10T14:30:25",
      "display_time": "2026-04-10 14:30",
      "has_html": true,
      "has_md": true,
      "has_graph": true,
      "chapter_count": 6,
      "html_url": "/api/report/file/20260410_143025/final_report.html",
      "md_url": "/api/report/file/20260410_143025/final_report.md",
      "graph_url": "/api/graph/20260410_143025"
    }
  ],
  "total": 1
}
```

**`status` 枚举**：

| status | 说明 |
|---|---|
| `completed` | 综合报告 HTML 已生成 |
| `partial` | 有部分 agent 报告但综合报告未完成 |
| `incomplete` | 任务目录存在但没有任何报告文件 |

**排序**：按 `created_at` 倒序（最新在前）。

---

### 1.8 获取历史任务详情

```
GET /api/history/{task_id}
```

**成功响应**（200）：

```json
{
  "ok": true,
  "task_id": "20260410_143025",
  "forum_log": "[14:30:25] [INSIGHT] 通过分析微博数据...\n[14:31:25] [HOST] ...",
  "host_speeches": "## Host 发言 #1\n\n...",
  "html_url": "/api/report/file/20260410_143025/final_report.html",
  "md_url": "/api/report/file/20260410_143025/final_report.md",
  "graph_url": "/api/graph/20260410_143025"
}
```

**说明**：`forum_log` 和 `host_speeches` 限制最大返回 50000 / 30000 字符。

---

### 1.9 获取知识图谱

```
GET /api/graph/{task_id}
```

**成功响应**（200）：

```json
{
  "ok": true,
  "graph": {
    "entities": [
      {
        "id": "anthropic",
        "name": "Anthropic",
        "type": "organization",
        "description": "Claude 模型背后的 AI 安全研究公司",
        "weight": 10,
        "sentiment": "neutral"
      },
      {
        "id": "claude_code",
        "name": "Claude Code",
        "type": "product",
        "description": "Anthropic 发布的命令行 AI 编程助手",
        "weight": 10,
        "sentiment": "mixed"
      }
    ],
    "relations": [
      {
        "source": "anthropic",
        "target": "claude_code",
        "type": "发布",
        "evidence": "Anthropic 于 2025 年 2 月正式发布 Claude Code",
        "strength": 5
      }
    ],
    "stats": {
      "entity_count": 25,
      "relation_count": 32,
      "entity_types": {
        "organization": 8,
        "product": 6,
        "event": 4,
        "person": 3,
        "topic": 3,
        "location": 1
      }
    }
  }
}
```

**实体类型枚举（`entity.type`）**：

| type | 说明 | 建议颜色 |
|---|---|---|
| `person` | 人物 | `#f59e0b` 橙 |
| `organization` | 组织/公司 | `#3b82f6` 蓝 |
| `product` | 产品/工具 | `#8b5cf6` 紫 |
| `event` | 事件 | `#ef4444` 红 |
| `location` | 地点 | `#10b981` 绿 |
| `topic` | 话题/概念 | `#6b7280` 灰 |

**情感枚举（`entity.sentiment`）**：

| sentiment | 说明 | 建议用于节点边框色 |
|---|---|---|
| `positive` | 正面 | `#10b981` |
| `negative` | 负面 | `#ef4444` |
| `neutral` | 中性 | `#94a3b8` |
| `mixed` | 混合 | `#f59e0b` |

**`entity.weight`**：1-10 整数，表示实体重要度。建议用于节点大小。

**`relation.strength`**：1-5 整数，表示关系强度。建议用于边的宽度。

---

## 二、Socket.IO 实时事件

连接地址与 HTTP 同源（默认 `http://localhost:9460`）。

### 2.1 服务端 → 客户端事件

#### `task_state`（连接时触发）

客户端连接后立即收到，同步当前任务状态。如果没有运行中的任务，`running=false`。

```json
{
  "running": true,
  "task_id": "20260410_143025",
  "query": "Claude Code 舆情分析",
  "stage": "analyzing",
  "agent_progress": { ... },
  "entries": [ ... ]
}
```

**说明**：`entries` 是完整的论坛发言历史数组（用于刷新页面后恢复状态），格式同 `GET /api/entries`。

---

#### `task_started`

任务开始时触发。

```json
{
  "task_id": "20260410_143025",
  "query": "Claude Code 舆情分析",
  "threshold": 5
}
```

---

#### `stage_update`

阶段切换时触发。

```json
{
  "stage": "reporting",
  "message": "综合成稿中..."
}
```

**`stage` 可能的值**：`analyzing` → `reporting` → `completed`

---

#### `forum_entry`（核心事件，高频）

**每当有新的论坛发言（智能体段落或主持人发言）时触发**。这是前端实时展示进度的核心事件。

```json
{
  "timestamp": 1712733025.123,
  "time_str": "14:30:25",
  "role": "INSIGHT",
  "content": "通过分析微博数据，发现 Claude Code 在程序员圈讨论度极高..."
}
```

**触发频率**：每个智能体每分析一个段落产出 2 条（首次总结 + 反思深化），全流程约 30-60 条。主持人每 N 条后插入一条 `HOST`。

---

#### `agent_progress`

某个智能体进度更新时触发。

```json
{
  "agent": "insight",
  "progress": {
    "current": 3,
    "total": 0,
    "status": "running"
  }
}
```

**`agent`**：`insight` / `media` / `query`

---

#### `task_completed`

任务成功完成时触发（含报告和图谱 URL）。

```json
{
  "task_id": "20260410_143025",
  "title": "Claude Code中文舆情全景图：技术理想与工程现实的张力解构",
  "stats": {
    "chapter_count": 6,
    "markdown_chars": 74790,
    "html_chars": 113290,
    "entity_count": 25,
    "relation_count": 32
  },
  "html_url": "/api/report/file/20260410_143025/final_report.html",
  "md_url": "/api/report/file/20260410_143025/final_report.md",
  "graph_url": "/api/graph/20260410_143025",
  "has_graph": true
}
```

---

#### `task_failed`

任务失败时触发。

```json
{
  "error": "API connection error",
  "traceback": "Traceback (most recent call last):\n..."
}
```

---

#### `task_cancelled`

任务被用户取消时触发。

```json
{
  "task_id": "20260410_143025",
  "message": "任务已被用户取消"
}
```

---

#### `cancel_requested`

取消请求已发出（但任务尚未真正停止）时触发。

```json
{
  "task_id": "20260410_143025"
}
```

**前端处理建议**：收到后把「取消」按钮改为「取消中...」并禁用，等收到 `task_cancelled` 后恢复。

---

## 三、典型前端交互流程

### 3.1 启动新任务

```
前端                                  后端
  │                                    │
  │── POST /api/start ────────────────>│
  │<── {"ok": true, "task_id": "..."} ─│
  │                                    │
  │<── [SocketIO] task_started ────────│
  │<── [SocketIO] stage_update ────────│  stage: "analyzing"
  │                                    │
  │<── [SocketIO] forum_entry ─────────│  role: "INSIGHT"
  │<── [SocketIO] agent_progress ──────│  agent: "insight"
  │<── [SocketIO] forum_entry ─────────│  role: "QUERY"
  │<── [SocketIO] forum_entry ─────────│  role: "MEDIA"
  │    ... (持续约 10-15 分钟) ...     │
  │<── [SocketIO] forum_entry ─────────│  role: "HOST" (每 N 条触发)
  │    ...                             │
  │<── [SocketIO] stage_update ────────│  stage: "reporting"
  │    ... (ReportAgent 工作约 3 分钟)  │
  │<── [SocketIO] task_completed ──────│  带 html_url + graph_url
  │                                    │
  │── GET /api/graph/{task_id} ───────>│  加载知识图谱
  │<── {"ok": true, "graph": {...}} ───│
```

### 3.2 取消任务

```
前端                                  后端
  │                                    │
  │── POST /api/cancel ───────────────>│
  │<── {"ok": true, "message": "..."} ─│
  │                                    │
  │<── [SocketIO] cancel_requested ────│  (UI 显示"取消中...")
  │    ... (等待当前 LLM 调用完成) ...  │  (最多 30-60 秒)
  │<── [SocketIO] task_cancelled ──────│  (UI 恢复)
```

### 3.3 刷新页面恢复状态

```
前端                                  后端
  │                                    │
  │── [SocketIO] connect ─────────────>│
  │<── [SocketIO] task_state ──────────│  包含 running/entries/progress
  │                                    │  前端用此数据恢复 UI 状态
```

### 3.4 查看历史报告

```
前端                                  后端
  │                                    │
  │── GET /api/history ───────────────>│
  │<── {"items": [...], "total": N} ───│
  │                                    │
  │  用户点击某条历史                   │
  │── GET /api/report/file/{id}/...───>│  查看 HTML 报告
  │── GET /api/graph/{id} ────────────>│  加载该任务的知识图谱
```

---

## 四、任务产物目录结构

每个任务的产物保存在 `reports/web/{safe_query}_{task_id}/`：

```
reports/web/Claude_Code_在中文程序员社区的舆情分析_20260410_143025/
├── final_report.html      # 综合 HTML 报告（含 Chart.js 图表）
├── final_report.md        # 综合 Markdown 报告
├── insight_report.md      # 舆情探察独立报告
├── media_report.md        # 多模态分析独立报告
├── query_report.md        # 新闻调查独立报告
├── forum_log.txt          # 完整论坛日志
├── graph.json             # 知识图谱（实体 + 关系）
└── meta.json              # 任务元数据
```

### meta.json 格式

```json
{
  "task_id": "20260410_143025",
  "query": "Claude Code 在中文程序员社区的舆情分析",
  "title": "Claude Code中文舆情全景图：...",
  "completed_at": "2026-04-10T15:01:23.456789",
  "duration_seconds": 1858,
  "chapter_count": 6,
  "markdown_chars": 74790,
  "html_chars": 113290,
  "entity_count": 25,
  "relation_count": 32
}
```

---

## 五、错误处理约定

所有 API 遵循统一的错误格式：

```json
{
  "ok": false,
  "error": "具体错误描述"
}
```

HTTP 状态码：

| 状态码 | 场景 |
|---|---|
| 200 | 成功 |
| 400 | 参数错误 / 操作不合法 |
| 404 | 资源不存在 |
| 409 | 冲突（如已有任务在运行） |
| 500 | 服务器内部错误 |
