import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "research-loop"
SCRIPTS = SKILL_DIR / "scripts"


PROGRAM = """# Research Program

## Goal
验证研究循环测试夹具。

## Editable Scope
- simulate_loop.py
- .research/trials/

## Frozen Scope
- .research/program.md

## Primary Metric
- Name: score
- Direction: higher-is-better
- Minimum useful movement: 0.100
- Measurement command: python simulate_loop.py

## Guardrail Metrics
- Name: stability
- Failure threshold: 不得低于 0.800
- Measurement command: python simulate_loop.py

## Verification Commands
1. Command: python simulate_loop.py
   Purpose: 逐步生成 trial record。
   Required for decision: yes

## Decision Rule
- keep: score 提升至少 0.100 且 stability 不低于 0.800。
- rollback: score 回退或 stability 低于 0.800。
- needs-review: 证据不足、正在运行或需要人工判断。

## Trial Budget
- Max changed files: 3
- Max runtime: 1 minute
- Max trials before review: 3
"""


SIMULATOR = r'''import time
from pathlib import Path

trials = [
    ("001", 0.0, 0.4, 1.0, 0.98, "keep"),
    ("002", 0.4, 0.6, 0.98, 0.91, "keep"),
    ("003", 0.6, 0.64, 0.91, 0.72, "rollback"),
]

template = """# Trial {id}

## Hypothesis

如果写入 trial {id}，dashboard 应该实时更新。

## Scope

Changed:
- simulate_loop.py

Frozen:
- .research/program.md

## Commands

| Command | Status | Evidence |
| --- | --- | --- |
| `python simulate_loop.py` | pass | `trial {id} generated` |

## Metrics

| Metric | Before | After | Direction | Result |
| --- | ---: | ---: | --- | --- |
| score | {score_before:.3f} | {score_after:.3f} | higher | improved |
| stability | {stability_before:.3f} | {stability_after:.3f} | guardrail | {stability_result} |

## Decision

{decision}

## Reason

按测试夹具规则生成 {decision} 决策。

## Next Question

继续观察下一轮。
"""

root = Path(__file__).resolve().parent
for id, score_before, score_after, stability_before, stability_after, decision in trials:
    target = root / ".research" / "trials" / id
    target.mkdir(parents=True, exist_ok=True)
    target.joinpath("record.md").write_text(
        template.format(
            id=id,
            score_before=score_before,
            score_after=score_after,
            stability_before=stability_before,
            stability_after=stability_after,
            stability_result="pass" if stability_after >= 0.8 else "fail",
            decision=decision,
        ),
        encoding="utf-8",
    )
    time.sleep(0.35)
'''


class ResearchLoopTests(unittest.TestCase):
    def run_script(self, name, *args, cwd=None, timeout=10):
        command = [sys.executable, str(SCRIPTS / name), *args]
        return subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=True,
        )

    def test_scripts_compile(self):
        scripts = sorted(str(path) for path in SCRIPTS.glob("*.py"))
        subprocess.run([sys.executable, "-m", "py_compile", *scripts], check=True)

    def test_snapshot_validation_and_live_dashboard(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.run_script("init_research_task.py", "--root", str(root))
            (root / ".research" / "program.md").write_text(PROGRAM, encoding="utf-8")
            (root / "simulate_loop.py").write_text(SIMULATOR, encoding="utf-8")

            port = 9876
            server = subprocess.Popen(
                [
                    sys.executable,
                    str(SCRIPTS / "serve_research_ui.py"),
                    "--root",
                    str(root),
                    "--port",
                    str(port),
                    "--quiet",
                    "--event-interval",
                    "0.1",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                self.wait_for_health(port)
                seen = self.collect_sse_counts(port, root)
                self.assertEqual(seen[:4], [0, 1, 2, 3])

                self.run_script("validate_research_task.py", "--root", str(root), "--strict")
                self.run_script("export_research_snapshot.py", "--root", str(root))

                snapshot = json.loads((root / ".research" / "snapshot.json").read_text(encoding="utf-8"))
                self.assertEqual(snapshot["summary"]["decisions"], {"keep": 2, "needs-review": 0, "rollback": 1})

                html = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3).read().decode("utf-8")
                self.assertIn("研究循环仪表盘", html)
                self.assertIn("EventSource", html)
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)

    def wait_for_health(self, port):
        for _ in range(40):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2).read()
                return
            except Exception:
                time.sleep(0.1)
        self.fail("dashboard server did not start")

    def collect_sse_counts(self, port, root):
        seen = []
        errors = []
        stop = threading.Event()

        def reader():
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/events", timeout=15) as response:
                    event = None
                    for raw in response:
                        if stop.is_set():
                            break
                        line = raw.decode("utf-8").strip()
                        if line.startswith("event: "):
                            event = line[7:]
                        elif line.startswith("data: ") and event == "snapshot":
                            data = json.loads(line[6:])
                            count = data["summary"]["trial_count"]
                            if not seen or seen[-1] != count:
                                seen.append(count)
                            if count >= 3:
                                stop.set()
                                break
            except Exception as error:
                errors.append(repr(error))
                stop.set()

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        deadline = time.time() + 5
        while not seen and time.time() < deadline:
            time.sleep(0.05)
        self.assertEqual(seen[:1], [0])

        simulator = subprocess.run(
            [sys.executable, str(root / "simulate_loop.py")],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        )
        self.assertEqual(simulator.returncode, 0)

        deadline = time.time() + 10
        while not stop.is_set() and time.time() < deadline:
            time.sleep(0.05)
        stop.set()
        thread.join(timeout=2)
        if errors:
            self.fail(errors[0])
        return seen


if __name__ == "__main__":
    unittest.main()
