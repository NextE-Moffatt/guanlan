# main.py
# 观澜 (GuanLan) Web 前端入口
# Flask + Flask-SocketIO 实时推送智能体段落 / 主持人发言 / 进度

import os
# 必须最先设置环境，避免 agno 读取系统代理
for _k in ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
    os.environ.pop(_k, None)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import asyncio
import json
import threading
import traceback
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from typing import Dict, Any, Optional

from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from flask_socketio import SocketIO, emit

# ============== 前置 patch，必须在导入 agno 之前 ==============
from agno_team import _agno_setup  # noqa: F401

from agno_team.forum_state import ForumEntry
from agno_team.opinion_team import run_opinion_pipeline


# ============== Flask 应用 ==============

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = "agno-mirofish-web-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

PROJECT_ROOT = Path(__file__).resolve().parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "web"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ============== 任务状态 ==============

class TaskState:
    """当前正在运行的任务状态（单任务模式，简化实现）"""
    def __init__(self):
        self.running: bool = False
        self.task_id: Optional[str] = None
        self.query: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.stage: str = "idle"  # idle | analyzing | reporting | completed | failed
        self.agent_progress: Dict[str, Dict[str, int]] = {}
        self.forum_entries: list = []
        self.error: Optional[str] = None
        self.output_dir: Optional[Path] = None

    def reset(self, query: str):
        self.running = True
        self.task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.query = query
        self.start_time = datetime.now()
        self.stage = "analyzing"
        self.agent_progress = {
            "insight": {"current": 0, "total": 0, "status": "pending"},
            "media":   {"current": 0, "total": 0, "status": "pending"},
            "query":   {"current": 0, "total": 0, "status": "pending"},
        }
        self.forum_entries = []
        self.error = None

        safe_query = query[:30].replace(" ", "_").replace("/", "_")
        self.output_dir = REPORTS_DIR / f"{safe_query}_{self.task_id}"
        self.output_dir.mkdir(parents=True, exist_ok=True)


TASK = TaskState()


# ============== SocketIO 事件推送辅助 ==============

def emit_event(event: str, payload: dict):
    """线程安全的 SocketIO 推送"""
    try:
        socketio.emit(event, payload)
    except Exception as e:
        print(f"⚠️  SocketIO emit {event} 失败: {e}")


def on_forum_entry(entry: ForumEntry):
    """ForumState observer：每次有新条目就推给前端"""
    entry_dict = {
        "timestamp": entry.timestamp,
        "time_str": datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S"),
        "role": entry.role,
        "content": entry.content,
    }
    TASK.forum_entries.append(entry_dict)
    emit_event("forum_entry", entry_dict)


# ============== 路由 ==============

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    """查询当前任务状态"""
    return jsonify({
        "running": TASK.running,
        "task_id": TASK.task_id,
        "query": TASK.query,
        "stage": TASK.stage,
        "agent_progress": TASK.agent_progress,
        "entries_count": len(TASK.forum_entries),
        "start_time": TASK.start_time.isoformat() if TASK.start_time else None,
        "error": TASK.error,
    })


@app.route("/api/start", methods=["POST"])
def api_start():
    """启动分析任务"""
    if TASK.running:
        return jsonify({"ok": False, "error": "已有任务在运行，请等待完成"}), 409

    data = request.get_json() or {}
    query = (data.get("query") or "").strip()
    threshold = int(data.get("threshold", 5))

    if not query:
        return jsonify({"ok": False, "error": "请输入分析主题"}), 400

    TASK.reset(query)
    thread = threading.Thread(
        target=run_pipeline_in_thread,
        args=(query, threshold),
        daemon=True,
    )
    thread.start()

    emit_event("task_started", {
        "task_id": TASK.task_id,
        "query": query,
        "threshold": threshold,
    })

    return jsonify({
        "ok": True,
        "task_id": TASK.task_id,
        "query": query,
    })


@app.route("/api/entries")
def api_entries():
    """获取当前任务的所有论坛条目（刷新页面时的历史拉取）"""
    return jsonify({"entries": TASK.forum_entries})


@app.route("/api/report/latest")
def api_report_latest():
    """获取最新生成的报告信息"""
    if not TASK.output_dir or not TASK.output_dir.exists():
        return jsonify({"ok": False, "error": "暂无报告"}), 404

    html_path = TASK.output_dir / "final_report.html"
    md_path = TASK.output_dir / "final_report.md"
    return jsonify({
        "ok": True,
        "task_id": TASK.task_id,
        "has_html": html_path.exists(),
        "has_md": md_path.exists(),
        "html_url": f"/api/report/file/{TASK.task_id}/final_report.html" if html_path.exists() else None,
        "md_url": f"/api/report/file/{TASK.task_id}/final_report.md" if md_path.exists() else None,
    })


@app.route("/api/report/file/<task_id>/<path:filename>")
def api_report_file(task_id: str, filename: str):
    """提供报告文件下载/查看"""
    # 防止目录穿越
    if ".." in filename or filename.startswith("/"):
        abort(400)

    # 在 REPORTS_DIR 下查找匹配 task_id 的目录
    matching_dirs = [d for d in REPORTS_DIR.iterdir() if d.is_dir() and d.name.endswith(task_id)]
    if not matching_dirs:
        abort(404)

    target_dir = matching_dirs[0]
    file_path = target_dir / filename
    if not file_path.exists():
        abort(404)

    return send_from_directory(str(target_dir), filename)


# ============== SocketIO 事件 ==============

@socketio.on("connect")
def on_connect():
    print(f"🔌 客户端连接: {request.sid}")
    # 发送当前任务状态
    emit("task_state", {
        "running": TASK.running,
        "task_id": TASK.task_id,
        "query": TASK.query,
        "stage": TASK.stage,
        "agent_progress": TASK.agent_progress,
        "entries": TASK.forum_entries,
    })


@socketio.on("disconnect")
def on_disconnect():
    print(f"🔌 客户端断开: {request.sid}")


# ============== 管道执行线程 ==============

def run_pipeline_in_thread(query: str, threshold: int):
    """在独立线程中跑 asyncio 管道（因为 Flask 默认是同步的）"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 包一层带进度统计的 observer
        def observer(entry: ForumEntry):
            on_forum_entry(entry)
            # 更新 agent 进度
            role_lower = entry.role.lower()
            if role_lower in TASK.agent_progress:
                TASK.agent_progress[role_lower]["current"] += 1
                TASK.agent_progress[role_lower]["status"] = "running"
                emit_event("agent_progress", {
                    "agent": role_lower,
                    "progress": TASK.agent_progress[role_lower],
                })

        emit_event("stage_update", {"stage": "analyzing", "message": "三 Agent 并发分析中..."})

        result = loop.run_until_complete(
            run_opinion_pipeline(
                query=query,
                host_threshold=threshold,
                forum_observer=observer,
            )
        )

        # 三 agent 完成，标记状态
        for agent_type in ("insight", "media", "query"):
            if agent_type in result.get("agent_results", {}):
                TASK.agent_progress[agent_type]["status"] = "done"

        TASK.stage = "reporting"
        emit_event("stage_update", {"stage": "reporting", "message": "生成综合报告..."})

        # 保存三份 agent 报告
        for at, ar in result["agent_results"].items():
            (TASK.output_dir / f"{at}_report.md").write_text(
                ar["final_report"], encoding="utf-8"
            )
        (TASK.output_dir / "forum_log.txt").write_text(result["forum_log"], encoding="utf-8")

        # 调 ReportAgent 生成综合报告
        from agno_agents import run_report_generation_async
        report = loop.run_until_complete(
            run_report_generation_async(
                query=query,
                agent_results=result["agent_results"],
                forum_log=result["forum_log"],
                host_speeches=result["host_speeches"],
            )
        )

        (TASK.output_dir / "final_report.md").write_text(report["markdown"], encoding="utf-8")
        (TASK.output_dir / "final_report.html").write_text(report["html"], encoding="utf-8")

        TASK.stage = "completed"
        TASK.running = False

        emit_event("task_completed", {
            "task_id": TASK.task_id,
            "title": report["title"],
            "stats": report["stats"],
            "html_url": f"/api/report/file/{TASK.task_id}/final_report.html",
            "md_url": f"/api/report/file/{TASK.task_id}/final_report.md",
        })

        print(f"✅ 任务 {TASK.task_id} 完成")

    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ 任务失败: {e}\n{tb}")
        TASK.stage = "failed"
        TASK.running = False
        TASK.error = str(e)
        emit_event("task_failed", {"error": str(e), "traceback": tb[:2000]})


# ============== 入口 ==============

def _find_free_port(candidates: list) -> int:
    """从候选端口中选一个没被占用的"""
    import socket
    for p in candidates:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("0.0.0.0", p))
            sock.close()
            return p
        except OSError:
            continue
    return candidates[-1]  # 都不行就用最后一个


if __name__ == "__main__":
    from config import settings
    host = settings.HOST or "0.0.0.0"

    # 按优先级尝试端口（5000 在 macOS 上常被 AirPlay 占，9458 是 BettaFish 默认）
    env_port = int(os.environ.get("MAIN_PORT", 0)) or int(settings.PORT or 0)
    if env_port:
        port = env_port
    else:
        port = _find_free_port([9460, 9461, 9462, 8080, 8000])

    print(f"\n🌊 观澜 · 多智能体舆情分析系统")
    print(f"   访问: http://localhost:{port}")
    print(f"   报告保存目录: {REPORTS_DIR}")
    print(f"   「观水有术，必观其澜」")
    print()
    socketio.run(
        app,
        host=host,
        port=port,
        debug=False,
        allow_unsafe_werkzeug=True,
    )
