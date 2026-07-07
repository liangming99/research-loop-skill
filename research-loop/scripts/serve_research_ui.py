#!/usr/bin/env python3
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from export_research_snapshot import build_snapshot  # noqa: E402


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>研究循环仪表盘</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #697586;
      --line: #d8dee8;
      --keep: #1f7a4d;
      --rollback: #a43f3f;
      --review: #7a5b12;
      --running: #315d8f;
      --accent: #315d8f;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      padding: 18px 24px;
    }
    h1, h2, h3, p { margin: 0; }
    h1 { font-size: 20px; font-weight: 700; letter-spacing: 0; }
    h2 { font-size: 15px; margin-bottom: 12px; }
    h3 { font-size: 14px; margin: 12px 0 8px; }
    main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 18px;
      display: grid;
      gap: 14px;
    }
    .topline {
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      margin-top: 8px;
    }
    .grid {
      display: grid;
      gap: 14px;
    }
    .grid.two { grid-template-columns: minmax(0, 1.1fr) minmax(300px, 0.9fr); }
    .grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    section, .tile {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    .muted { color: var(--muted); }
    .mono { font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace; }
    .stat {
      min-height: 86px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .stat strong { font-size: 28px; line-height: 1; }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 650;
      border: 1px solid currentColor;
      white-space: nowrap;
    }
    .keep { color: var(--keep); }
    .rollback { color: var(--rollback); }
    .needs-review { color: var(--review); }
    .running { color: var(--running); }
    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 8px 6px;
      vertical-align: top;
      text-align: left;
      overflow-wrap: anywhere;
    }
    th { color: var(--muted); font-size: 12px; font-weight: 650; }
    tr:last-child td { border-bottom: 0; }
    .timeline {
      display: grid;
      gap: 8px;
    }
    .trial-button {
      width: 100%;
      border: 1px solid var(--line);
      background: #fbfcfd;
      border-radius: 8px;
      padding: 10px;
      text-align: left;
      cursor: pointer;
    }
    .trial-button[aria-selected="true"] {
      border-color: var(--accent);
      box-shadow: inset 3px 0 0 var(--accent);
      background: #f2f7fc;
    }
    .bars {
      display: grid;
      gap: 10px;
    }
    .bar-row {
      display: grid;
      grid-template-columns: minmax(80px, 130px) 1fr minmax(80px, 150px);
      gap: 10px;
      align-items: center;
    }
    .bar-track {
      height: 12px;
      background: #e8edf4;
      border-radius: 999px;
      overflow: hidden;
    }
    .bar-fill {
      height: 100%;
      background: var(--accent);
      min-width: 2px;
      transition: width 160ms ease;
    }
    .empty, .error {
      padding: 20px;
      border: 1px dashed var(--line);
      border-radius: 8px;
      background: #fff;
    }
    .error { border-color: #d28b8b; color: #8f2525; }
    .fresh {
      display: inline-flex;
      gap: 8px;
      align-items: center;
      color: var(--muted);
      font-size: 12px;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--keep);
    }
    pre {
      margin: 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #f2f4f7;
      border-radius: 6px;
      padding: 10px;
      max-height: 240px;
      overflow: auto;
    }
    @media (max-width: 820px) {
      header { padding: 16px; }
      main { padding: 12px; }
      .grid.two, .grid.three { grid-template-columns: 1fr; }
      .bar-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>研究循环仪表盘</h1>
    <div class="topline">
      <p id="root" class="muted mono"></p>
      <p class="fresh"><span class="dot"></span><span id="refresh-status">正在读取...</span></p>
    </div>
  </header>
  <main id="app">
    <div class="empty">正在读取研究快照...</div>
  </main>
  <script>
    const app = document.getElementById("app");
    const rootLabel = document.getElementById("root");
    const refreshStatus = document.getElementById("refresh-status");
    let snapshot = null;
    let selectedTrialId = null;
    let manualSelection = false;
    let lastTrialCount = 0;
    let lastSnapshotSignature = "";
    let eventSource = null;
    let pollTimer = null;

    const POLL_MS = 2000;

    const decisionText = {
      "keep": "保留",
      "rollback": "回滚",
      "needs-review": "待复核",
      "running": "进行中"
    };

    const statusText = {
      "pass": "通过",
      "fail": "失败",
      "blocked": "阻塞",
      "unknown": "未知"
    };

    const resultText = {
      "improved": "提升",
      "regressed": "回退",
      "unchanged": "不变",
      "unknown": "未知",
      "inconclusive": "不确定",
      "pass": "通过",
      "fail": "失败"
    };

    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[char]));

    const fmt = (value) => {
      if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(6).replace(/0+$/, "").replace(/\.$/, "");
      return esc(value ?? "");
    };

    const displayDecision = (decision) => decisionText[decision] || (decision ? esc(decision) : "进行中");
    const decisionClass = (decision) => esc(String(decision || "running"));
    const displayStatus = (status) => statusText[status] || esc(status || "未知");
    const displayResult = (result) => resultText[result] || esc(result || "");

    function setRefreshStatus(text, ok = true) {
      refreshStatus.textContent = text;
      const dot = document.querySelector(".dot");
      dot.style.background = ok ? "var(--keep)" : "var(--rollback)";
    }

    function snapshotSignature(data) {
      const copy = JSON.parse(JSON.stringify(data));
      delete copy.runtime;
      return JSON.stringify(copy);
    }

    function renderError(message, detail) {
      rootLabel.textContent = "";
      app.innerHTML = `<div class="error"><h2>${esc(message)}</h2><p class="mono">${esc(detail || "")}</p></div>`;
    }

    function metricDelta(metric) {
      const before = Number(metric.before);
      const after = Number(metric.after);
      if (!Number.isFinite(before) || !Number.isFinite(after)) return "";
      const delta = after - before;
      return `${delta >= 0 ? "+" : ""}${fmt(delta)}`;
    }

    function renderMetricBars(trials) {
      const rows = [];
      for (const trial of trials) {
        const primary = (trial.metrics || [])[0];
        if (!primary) continue;
        const before = Number(primary.before);
        const after = Number(primary.after);
        const max = Math.max(Math.abs(before || 0), Math.abs(after || 0), 1);
        const pct = Math.max(0, Math.min(100, Math.abs(after) / max * 100));
        rows.push(`
          <div class="bar-row">
            <div><strong>${esc(trial.id)}</strong><div class="muted">${esc(primary.metric || "指标")}</div></div>
            <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
            <div class="mono">${fmt(primary.before)} -> ${fmt(primary.after)}</div>
          </div>
        `);
      }
      return rows.length ? rows.join("") : `<div class="empty">还没有可绘制的数值指标。</div>`;
    }

    function renderTimeline(trials) {
      if (!trials.length) return `<div class="empty">还没有记录试验。循环运行时，新试验会自动出现在这里。</div>`;
      return trials.map((trial) => {
        const selected = trial.id === selectedTrialId ? "true" : "false";
        const metric = (trial.metrics || [])[0] || {};
        return `
          <button class="trial-button" aria-selected="${selected}" onclick="selectTrial('${esc(trial.id)}')">
            <div><strong>试验 ${esc(trial.id)}</strong> <span class="badge ${decisionClass(trial.decision)}">${displayDecision(trial.decision)}</span></div>
            <div class="muted">${esc(metric.metric || "暂无指标")} ${metricDelta(metric)}</div>
            <div>${esc(trial.next_question || "")}</div>
          </button>
        `;
      }).join("");
    }

    function renderLogs(logs) {
      if (!logs || !logs.length) return `<div class="empty">暂无重复评估日志。</div>`;
      const rows = logs.map((log) => `
        <tr>
          <td class="mono">${esc(log.path)}</td>
          <td>${esc(log.runs ?? "")}</td>
          <td>${esc(log.successful_json_runs ?? "")}</td>
          <td class="mono">${esc(JSON.stringify(log.summary || log.error || {}))}</td>
        </tr>
      `).join("");
      return `<table><thead><tr><th>日志</th><th>次数</th><th>JSON 成功</th><th>摘要</th></tr></thead><tbody>${rows}</tbody></table>`;
    }

    function renderTrialDetail(trial) {
      if (!trial) return `<div class="empty">选择一个试验查看详情。</div>`;
      const metrics = (trial.metrics || []).map((metric) => `
        <tr>
          <td>${esc(metric.metric)}</td>
          <td class="mono">${fmt(metric.before)}</td>
          <td class="mono">${fmt(metric.after)}</td>
          <td>${esc(metric.direction)}</td>
          <td>${displayResult(metric.result)}</td>
        </tr>
      `).join("");
      const commands = (trial.commands || []).map((command) => `
        <tr>
          <td class="mono">${esc(command.command)}</td>
          <td>${displayStatus(command.status)}</td>
          <td class="mono">${esc(command.evidence)}</td>
        </tr>
      `).join("");
      return `
        <section>
          <h2>试验 ${esc(trial.id)} 详情</h2>
          <p><span class="badge ${decisionClass(trial.decision)}">${displayDecision(trial.decision)}</span></p>
          <h3>假设</h3>
          <p>${esc(trial.hypothesis)}</p>
          <h3>修改文件</h3>
          <p class="mono">${esc((trial.changed_files || []).join(", ") || "无")}</p>
          <h3>指标</h3>
          <table><thead><tr><th>指标</th><th>之前</th><th>之后</th><th>方向</th><th>结果</th></tr></thead><tbody>${metrics}</tbody></table>
          <h3>命令</h3>
          <table><thead><tr><th>命令</th><th>状态</th><th>证据</th></tr></thead><tbody>${commands}</tbody></table>
          <h3>决策依据</h3>
          <p>${esc(trial.reason)}</p>
          <h3>下一问题</h3>
          <p>${esc(trial.next_question)}</p>
        </section>
      `;
    }

    window.selectTrial = function(id) {
      selectedTrialId = id;
      manualSelection = true;
      render();
    };

    function chooseSelectedTrial(trials) {
      const exists = trials.some((trial) => trial.id === selectedTrialId);
      if (!exists) {
        selectedTrialId = trials.length ? trials[trials.length - 1].id : null;
        manualSelection = false;
        return;
      }
      if (!manualSelection && trials.length && trials.length !== lastTrialCount) {
        selectedTrialId = trials[trials.length - 1].id;
      }
    }

    function render() {
      const program = snapshot.program || {};
      const summary = snapshot.summary || {};
      const decisions = summary.decisions || {};
      const trials = snapshot.trials || [];
      chooseSelectedTrial(trials);
      lastTrialCount = trials.length;
      const selected = trials.find((trial) => trial.id === selectedTrialId);
      rootLabel.textContent = snapshot.root || "";
      app.innerHTML = `
        <section>
          <h2>研究计划</h2>
          <p>${esc(program.goal || "未找到目标。")}</p>
          <p class="muted">主要指标：<span class="mono">${esc((program.primary_metric || {}).name || "")}</span></p>
          <p class="muted">允许修改：<span class="mono">${esc((program.editable_scope || []).join(", "))}</span></p>
          <p class="muted">冻结范围：<span class="mono">${esc((program.frozen_scope || []).join(", "))}</span></p>
        </section>
        <div class="grid three">
          <div class="tile stat"><span class="muted">保留</span><strong class="keep">${esc(decisions.keep || 0)}</strong></div>
          <div class="tile stat"><span class="muted">回滚</span><strong class="rollback">${esc(decisions.rollback || 0)}</strong></div>
          <div class="tile stat"><span class="muted">待复核</span><strong class="needs-review">${esc(decisions["needs-review"] || 0)}</strong></div>
        </div>
        <div class="grid two">
          <section>
            <h2>试验时间线</h2>
            <div class="timeline">${renderTimeline(trials)}</div>
          </section>
          <section>
            <h2>指标变化</h2>
            <div class="bars">${renderMetricBars(trials)}</div>
          </section>
        </div>
        ${renderTrialDetail(selected)}
        <section>
          <h2>运行日志</h2>
          ${renderLogs(snapshot.logs || [])}
        </section>
      `;
    }

    function applySnapshot(data, source) {
      const signature = snapshotSignature(data);
      snapshot = data;
      if (signature !== lastSnapshotSignature) {
        lastSnapshotSignature = signature;
        render();
      }
      const generated = data.runtime && data.runtime.generated_at ? new Date(data.runtime.generated_at).toLocaleTimeString() : new Date().toLocaleTimeString();
      setRefreshStatus(`${source}；最近更新 ${generated}`, true);
    }

    async function fetchSnapshot() {
      try {
        const response = await fetch(`/api/snapshot?ts=${Date.now()}`, { cache: "no-store" });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || response.statusText);
        applySnapshot(data, "轮询刷新中，每 2 秒更新");
      } catch (error) {
        setRefreshStatus("读取失败，等待下一次刷新", false);
        renderError("无法读取研究快照", `${error.message}\n请确认 .research/program.md 存在，或重新运行研究循环。`);
      }
    }

    function startPolling() {
      if (pollTimer) return;
      fetchSnapshot();
      pollTimer = setInterval(fetchSnapshot, POLL_MS);
    }

    function startEvents() {
      if (!window.EventSource) {
        startPolling();
        return;
      }
      eventSource = new EventSource("/api/events");
      eventSource.addEventListener("snapshot", (event) => {
        try {
          applySnapshot(JSON.parse(event.data), "实时推送中，研究记录变化会自动更新");
        } catch (error) {
          setRefreshStatus("推送数据解析失败，已等待下一次更新", false);
        }
      });
      eventSource.addEventListener("heartbeat", () => {
        if (!snapshot) return;
        const generated = snapshot.runtime && snapshot.runtime.generated_at ? new Date(snapshot.runtime.generated_at).toLocaleTimeString() : new Date().toLocaleTimeString();
        setRefreshStatus(`实时推送中，最近更新 ${generated}`, true);
      });
      eventSource.onerror = () => {
        setRefreshStatus("实时连接断开，已切换到轮询", false);
        if (eventSource) eventSource.close();
        startPolling();
      };
    }

    startEvents();
  </script>
</body>
</html>
"""


class ResearchHandler(BaseHTTPRequestHandler):
    server_version = "ResearchLoopUI/2.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self.respond_text(HTML, "text/html; charset=utf-8")
            return
        if parsed.path == "/api/snapshot":
            self.respond_snapshot()
            return
        if parsed.path == "/api/events":
            self.respond_events()
            return
        if parsed.path == "/api/health":
            self.respond_json({"status": "ok", "root": str(self.server.project_root)})
            return
        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self.respond_json({"error": "未找到资源"}, status=404)

    def log_message(self, format, *args):
        if self.server.quiet:
            return
        super().log_message(format, *args)

    def respond_snapshot(self):
        try:
            data = self.server.build_live_snapshot()
        except (OSError, FileNotFoundError, ValueError) as error:
            self.respond_json(
                {
                    "error": f"无法构建研究快照：{error}",
                    "hint": "请确认项目下存在 .research/program.md，并且 trial record 格式完整。",
                },
                status=404,
            )
            return
        self.respond_json(data)

    def respond_events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        last_signature = None
        heartbeat_at = 0.0
        while True:
            try:
                data = self.server.build_live_snapshot()
                signature = self.server.snapshot_signature(data)
                now = time.time()
                if signature != last_signature:
                    self.write_sse("snapshot", data)
                    last_signature = signature
                    heartbeat_at = now
                elif now - heartbeat_at >= 15:
                    self.write_sse("heartbeat", {"generated_at": datetime.now(timezone.utc).isoformat()})
                    heartbeat_at = now
                time.sleep(self.server.event_interval)
            except (BrokenPipeError, ConnectionResetError):
                break
            except (OSError, FileNotFoundError, ValueError) as error:
                try:
                    self.write_sse("error", {"error": f"无法构建研究快照：{error}"})
                    time.sleep(2)
                except (BrokenPipeError, ConnectionResetError):
                    break

    def write_sse(self, event, data):
        payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
        message = f"event: {event}\ndata: {payload}\n\n".encode("utf-8")
        self.wfile.write(message)
        self.wfile.flush()

    def respond_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_text(self, text, content_type, status=200):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ResearchServer(ThreadingHTTPServer):
    def __init__(self, address, handler, project_root, quiet=False, event_interval=0.2):
        super().__init__(address, handler)
        self.project_root = project_root
        self.quiet = quiet
        self.event_interval = event_interval

    def build_live_snapshot(self):
        data = build_snapshot(self.project_root)
        data["runtime"] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "live",
            "transport": "sse",
        }
        snapshot_path = self.project_root / ".research" / "snapshot.json"
        snapshot_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return data

    def snapshot_signature(self, data):
        stable = dict(data)
        stable.pop("runtime", None)
        return json.dumps(stable, ensure_ascii=False, sort_keys=True)


def main():
    parser = argparse.ArgumentParser(description="Serve a read-only live dashboard for research-loop tasks.")
    parser.add_argument("--root", default=".", help="Project root containing .research/program.md.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Defaults to localhost.")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind.")
    parser.add_argument("--event-interval", type=float, default=0.2, help="Seconds between server-sent event checks.")
    parser.add_argument("--quiet", action="store_true", help="Suppress request logs.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"error: root does not exist: {root}", file=sys.stderr)
        return 1

    server = ResearchServer((args.host, args.port), ResearchHandler, root, quiet=args.quiet, event_interval=max(args.event_interval, 0.05))
    url = f"http://{args.host}:{server.server_address[1]}"
    print(f"研究循环仪表盘：{url}")
    print(f"项目目录：{root}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在停止研究循环仪表盘。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
