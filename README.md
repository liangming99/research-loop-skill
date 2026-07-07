# research-loop-skill

`research-loop` is a Codex Skill for goal-driven research loops: frame a program, run one falsifiable trial at a time, verify against fixed metrics, record evidence, and inspect progress in a live local dashboard.

## 它解决什么问题

这个 Skill 把开放式优化任务拆成可审计的研究循环：

1. 固定目标、范围、指标和验证命令。
2. 每轮只验证一个假设。
3. 只修改允许范围。
4. 按证据做 `keep / rollback / needs-review` 决策。
5. 把每轮记录写入 `.research/trials/`。
6. 用中文实时 dashboard 观察循环测试进度。

适合用于：

- 代码性能优化
- 机器学习实验
- RAG / prompt eval
- agent workflow 调优
- 数据管道或 benchmark 改进

## 目录结构

```text
research-loop/
  SKILL.md
  agents/openai.yaml
  references/
    program-contract.md
    trial-record.md
  scripts/
    init_research_task.py
    validate_research_task.py
    run_eval_repeated.py
    export_research_snapshot.py
    serve_research_ui.py
tests/
  test_research_loop.py
```

## 安装

把 `research-loop/` 复制到你的 Codex Skill 目录。

Windows 示例：

```powershell
Copy-Item -Recurse .\research-loop $env:USERPROFILE\.agents\skills\research-loop -Force
```

macOS / Linux 示例：

```bash
cp -R research-loop ~/.agents/skills/research-loop
```

## 快速开始

在目标项目中初始化研究任务：

```bash
python path/to/research-loop/scripts/init_research_task.py --root .
```

填写 `.research/program.md`，至少定义：

- Goal
- Editable Scope
- Frozen Scope
- Primary Metric
- Guardrail Metrics
- Verification Commands
- Decision Rule
- Trial Budget

运行一轮实验后，把记录写入：

```text
.research/trials/001/record.md
```

校验记录：

```bash
python path/to/research-loop/scripts/validate_research_task.py --root . --strict
```

导出 snapshot：

```bash
python path/to/research-loop/scripts/export_research_snapshot.py --root .
```

启动中文实时 dashboard：

```bash
python path/to/research-loop/scripts/serve_research_ui.py --root . --port 8765
```

打开：

```text
http://127.0.0.1:8765
```

## Dashboard 通信方式

dashboard 是只读本地监控端。

- `/api/snapshot` 每次请求都会从当前 `.research` 文件重建快照。
- `/api/events` 使用 Server-Sent Events 推送变化。
- 浏览器优先用 `EventSource` 实时更新。
- 如果 SSE 不可用，前端会退回 2 秒轮询。
- 浏览器不会执行命令，也不会修改 `.research` 文件。

当前没有使用 WebSocket。只有当未来需要从浏览器启动、停止、批准或修改研究任务时，才建议引入 WebSocket 或明确的控制 API。

## 测试

本仓库测试只依赖 Python 标准库：

```bash
python -m unittest discover -s tests
```

测试覆盖：

- Skill 脚本语法
- `.research` 初始化
- trial record 校验
- snapshot 导出
- 中文 dashboard HTML
- `/api/snapshot`
- `/api/events` SSE 实时更新

## License

MIT
