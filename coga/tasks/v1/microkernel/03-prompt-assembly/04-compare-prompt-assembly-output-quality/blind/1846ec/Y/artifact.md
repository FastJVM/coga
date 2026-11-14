# Pair 1846ec, output Y (code)

## Commit messages

```
Add execution-ready validation preflight

Task: fail-validation-when-local-user-is-required-for-ex
```

## Diff summary

```
docs/contexts/coga-dev/testing/SKILL.md            |  6 ++
 src/coga/commands/validate.py                      |  7 ++
 .../contexts/coga/recurring/scheduling/SKILL.md    | 22 +++++
 src/coga/validate.py                               | 19 +++--
 tests/test_cli.py                                  | 95 ++++++++++++++++++++++
 tests/test_validate.py                             | 40 +++++++++
 6 files changed, 184 insertions(+), 5 deletions(-)
```

## Diff

```diff
diff --git a/docs/contexts/coga-dev/testing/SKILL.md b/docs/contexts/coga-dev/testing/SKILL.md
index d584cc6..15a8c9d 100644
--- a/docs/contexts/coga-dev/testing/SKILL.md
+++ b/docs/contexts/coga-dev/testing/SKILL.md
@@ -21,6 +21,12 @@ command with `PIP_REQUIRE_HASHES=0`. A venv made with `uv venv` (or
 or `uv pip install -e ".[test]"` installs all test tools, including pip. Run
 `coga validate --json` after config, workflow, or task-model changes.
 
+For checkouts expected to execute mutating or recurring work, use
+`coga validate --execution-ready --json` before invoking the work. The strict
+scheduler preflight and per-target requirement for aggregate sweeps are owned
+by [coga/recurring/scheduling](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md#scheduler-preflight).
+Keep ordinary validation for fresh-clone diagnostics.
+
 **Validate `tests/fixtures/seeded-repo/coga` with `env -u SLACK_WEBHOOK_URL coga validate --json`**
 when your shell exports that variable. The fixture has notifications off, and
 the config-load guard rejects a bare exported `SLACK_WEBHOOK_URL` with no
diff --git a/src/coga/commands/validate.py b/src/coga/commands/validate.py
index 98832e5..719d024 100644
--- a/src/coga/commands/validate.py
+++ b/src/coga/commands/validate.py
@@ -31,6 +31,11 @@ def validate(
         "--fix",
         help="Apply conservative safe repairs before reporting.",
     ),
+    execution_ready: bool = typer.Option(
+        False,
+        "--execution-ready",
+        help="Treat a missing local user as an error for execution preflight.",
+    ),
     idle_hours: float = typer.Option(
         72.0, "--idle-hours", help="Active-task idle threshold."
     ),
@@ -78,6 +83,7 @@ def validate(
             cfg,
             task,
             fix=fix,
+            execution_ready=execution_ready,
             max_blackboard_bytes=int(max_blackboard_kb * 1024),
             idle_hours=idle_hours,
         )
@@ -89,6 +95,7 @@ def validate(
             check_slack=check_slack,
             check_github=check_github,
             fix=fix,
+            execution_ready=execution_ready,
         )
 
     if json_output:
diff --git a/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md b/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md
index 8b071c7..92ed409 100644
--- a/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md
+++ b/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md
@@ -8,6 +8,28 @@ description: How a recurring sweep runs due work — period keys and the service
 The repo-inactivity gate and `run_when_inactive` are in the leaf
 [coga/recurring/scheduling/inactivity](inactivity/SKILL.md).
 
+## Scheduler preflight
+
+Before invoking recurring work, run strict validation in every intended target
+checkout and stop provisioning or execution on a non-zero exit:
+
+```sh
+coga validate --execution-ready --json
+coga recurring
+```
+
+Ordinary validation permits a missing local actor for fresh-clone diagnostics.
+`--execution-ready` instead reports `missing-user` as an error and exits 1;
+set `user = "<name>"` in that checkout's gitignored `coga.local.toml` before
+retrying. Coga never chooses an actor, including with `--fix`. The flag works
+with `--task` and with whole-repo `--check-slack` / `--check-github` probes;
+those network checks remain incompatible with `--task`.
+
+For `coga recurring --all <path>`, preflight each real scheduler target in its
+own checkout before the aggregate sweep. Discovery intentionally skips
+unconfigured checkouts, including ones missing a user; a successful aggregate
+exit does not establish that every intended target was ready.
+
 ## Periods and the serviced-period ledger
 
 The scan takes each template's last firing strictly before now and buckets it
diff --git a/src/coga/validate.py b/src/coga/validate.py
index 9b1f7ca..c6450d3 100644
--- a/src/coga/validate.py
+++ b/src/coga/validate.py
@@ -196,8 +196,8 @@ def _duplicate_slug_issue(exc: DuplicateTaskSlugError) -> Issue:
     )
 
 
-def _missing_user_issue(cfg: Config) -> Issue | None:
-    """Point a user-less clone at its machine-local setup without blocking reads."""
+def _missing_user_issue(cfg: Config, *, execution_ready: bool = False) -> Issue | None:
+    """Report missing local identity, optionally as an execution preflight error."""
     if cfg.current_user:
         return None
     return Issue(
@@ -209,7 +209,7 @@ def _missing_user_issue(cfg: Config) -> Issue | None:
             '`user = "<name>"` (the file is gitignored, so every clone '
             "sets its own)"
         ),
-        severity="warn",
+        severity="error" if execution_ready else "warn",
     )
 
 
@@ -220,6 +220,7 @@ def run(
     check_slack: bool = False,
     check_github: bool = False,
     fix: bool = False,
+    execution_ready: bool = False,
 ) -> Report:
     report = Report(generated_at=_now_iso())
 
@@ -227,7 +228,7 @@ def run(
     # fresh clone (no gitignored `coga.local.toml` yet) can run diagnostics at
     # all — so the missing name must surface here as a finding instead of
     # silently validating clean.
-    missing_user = _missing_user_issue(cfg)
+    missing_user = _missing_user_issue(cfg, execution_ready=execution_ready)
     if missing_user is not None:
         report.issues.append(missing_user)
     important_webhook = _important_webhook_issue(cfg)
@@ -278,11 +279,12 @@ def validate_task(
     fix: bool = False,
     max_blackboard_bytes: int = BLACKBOARD_WARN_BYTES,
     idle_hours: float = 72.0,
+    execution_ready: bool = False,
 ) -> Report:
     """Validate exactly one task directory. Used by `coga validate --task`
     and by every Coga-owned command that mutates a task file."""
     report = Report(generated_at=_now_iso())
-    missing_user = _missing_user_issue(cfg)
+    missing_user = _missing_user_issue(cfg, execution_ready=execution_ready)
     if missing_user is not None:
         report.issues.append(missing_user)
     important_webhook = _important_webhook_issue(cfg)
@@ -1981,6 +1983,11 @@ def _main(argv: list[str] | None = None) -> int:
         action="store_true",
         help="Apply conservative safe repairs before reporting.",
     )
+    parser.add_argument(
+        "--execution-ready",
+        action="store_true",
+        help="Treat a missing local user as an error for execution preflight.",
+    )
     parser.add_argument("--idle-hours", type=float, default=72.0)
     parser.add_argument(
         "--max-blackboard-kb",
@@ -2017,6 +2024,7 @@ def _main(argv: list[str] | None = None) -> int:
             cfg,
             args.task,
             fix=args.fix,
+            execution_ready=args.execution_ready,
             max_blackboard_bytes=int(args.max_blackboard_kb * 1024),
             idle_hours=args.idle_hours,
         )
@@ -2028,6 +2036,7 @@ def _main(argv: list[str] | None = None) -> int:
             check_slack=args.check_slack,
             check_github=args.check_github,
             fix=args.fix,
+            execution_ready=args.execution_ready,
         )
 
     if args.json:
diff --git a/tests/test_cli.py b/tests/test_cli.py
index acc3d77..911ba67 100644
--- a/tests/test_cli.py
+++ b/tests/test_cli.py
@@ -547,3 +547,98 @@ def test_launch_adapter_keeps_windows_dword_exit_codes(
     result = CliRunner().invoke(app, ["launch", "x"])
     assert result.exit_code == expected
     assert expected & 0xFFFFFFFF == code
+
+
+@pytest.mark.parametrize("entrypoint", ["typer", "module"])
+@pytest.mark.parametrize("json_output", [False, True])
+@pytest.mark.parametrize("task_only", [False, True])
+@pytest.mark.parametrize("fix", [False, True])
+@pytest.mark.parametrize("user", [None, "runner"])
+def test_validate_execution_ready(
+    clone: Path,
+    capsys: pytest.CaptureFixture[str],
+    entrypoint: str,
+    json_output: bool,
+    task_only: bool,
+    fix: bool,
+    user: str | None,
+) -> None:
+    from coga.validate import _main
+
+    if user:
+        _write(clone / "coga.local.toml", f'user = "{user}"\n')
+    argv = ["--execution-ready"]
+    if json_output:
+        argv.append("--json")
+    if task_only:
+        argv.extend(["--task", "fix-retry-logic"])
+    if fix:
+        argv.append("--fix")
+    if entrypoint == "typer":
+        result = CliRunner().invoke(app, ["validate", *argv])
+        code, output = result.exit_code, result.output
+    else:
+        code = _main(argv)
+        output = capsys.readouterr().out
+    assert code == (0 if user else 1)
+    if json_output:
+        issues = json.loads(output)["issues"]
+        missing_user = [i for i in issues if i["kind"] == "missing-user"]
+        assert len(missing_user) == (0 if user else 1)
+        if not user:
+            assert missing_user[0]["severity"] == "error"
+            assert 'user = "<name>"' in missing_user[0]["message"]
+    elif not user:
+        assert "[ERROR] (config): missing-user" in output
+        assert "coga.local.toml" in output
+    assert (clone / "coga.local.toml").exists() == bool(user)
+
+
+@pytest.mark.parametrize("entrypoint", ["typer", "module"])
+@pytest.mark.parametrize(
+    "checks",
+    [["--check-slack"], ["--check-github"], ["--check-slack", "--check-github"]],
+)
+@pytest.mark.parametrize("task_only", [False, True])
+def test_validate_execution_ready_network_checks(
+    clone: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+    entrypoint: str,
+    checks: list[str],
+    task_only: bool,
+) -> None:
+    from coga.validate import _main
+
+    calls: list[str] = []
+
+    def slack(cfg) -> list:
+        calls.append("slack")
+        return []
+
+    def github(cfg) -> list:
+        calls.append("github")
+        return []
+
+    monkeypatch.setattr("coga.validate._notification_issues", slack)
+    monkeypatch.setattr("coga.validate._github_issues", github)
+    argv = ["--execution-ready", "--json", *checks]
+    if task_only:
+        argv.extend(["--task", "fix-retry-logic"])
+    if entrypoint == "typer":
+        result = CliRunner().invoke(app, ["validate", *argv])
+        code, output = result.exit_code, result.output
+    else:
+        code = _main(argv)
+        captured = capsys.readouterr()
+        output = captured.out + captured.err
+    assert code == (2 if task_only else 1)
+    if task_only:
+        assert "not supported with --task" in output
+        assert calls == []
+    else:
+        assert calls == [check.removeprefix("--check-") for check in checks]
+        issue = next(
+            i for i in json.loads(output)["issues"] if i["kind"] == "missing-user"
+        )
+        assert issue["severity"] == "error"
diff --git a/tests/test_validate.py b/tests/test_validate.py
index 48cb8e1..d95ea1e 100644
--- a/tests/test_validate.py
+++ b/tests/test_validate.py
@@ -3095,3 +3095,43 @@ def test_validate_accepts_absent_resource_root(repo: Path) -> None:
     report = run(load_config(repo))
 
     assert not [i for i in report.issues if i.kind == "unreadable-resource-override"]
+
+
+@pytest.mark.parametrize("execution_ready", [False, True])
+@pytest.mark.parametrize("task_only", [False, True])
+def test_missing_user_severity(
+    repo: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+    execution_ready: bool,
+    task_only: bool,
+) -> None:
+    cfg = load_config(repo)
+    task = create_task(
+        cfg=cfg,
+        title="Check local actor",
+        workflow_name=None,
+        contexts=[],
+        owner="marc",
+        agent="claude",
+        status="draft",
+    )
+    (repo / "coga.local.toml").unlink()
+    cfg = load_config(repo, require_user=False)
+    if task_only:
+        report = validate_task(cfg, task["slug"], execution_ready=execution_ready)
+    else:
+        report = run(cfg, execution_ready=execution_ready)
+    issue = next(i for i in report.issues if i.kind == "missing-user")
+    assert issue.severity == ("error" if execution_ready else "warn")
+
+    monkeypatch.chdir(repo)
+    argv = ["--json"]
+    if execution_ready:
+        argv.append("--execution-ready")
+    if task_only:
+        argv.extend(["--task", task["slug"]])
+    assert _main(argv) == (1 if execution_ready else 0)
+    payload = json.loads(capsys.readouterr().out)
+    missing_user = next(i for i in payload["issues"] if i["kind"] == "missing-user")
+    assert missing_user["severity"] == issue.severity
```

## Ticket blackboard at the end of the step (handoff, PR receipts)

````markdown
## Dev

branch: coga/fail-validation-execution-ready

## Implement handoff

Implemented and pushed 44fedf0723b145a29f2272a6b6ac1f1f3ed99769.
`validate.run`, `validate.validate_task`, and both CLI entrypoints accept
execution_ready / --execution-ready. Missing actors retain the same finding
and remediation; strict mode changes severity to error. Default diagnostics
remain lenient. No actor is inferred or created, including with --fix.

Updated the package-owned scheduling topic (the sole live user-topic owner,
so no local twin was recreated) and local testing guidance. The seeded fixture
needs no semantic change; both strict and ordinary validation report 5 tasks,
no issues. New tests cover both entrypoints, text/JSON, task/repo scope, --fix,
actor present/absent, network-check combinations and task incompatibilities.

Regression first failed as expected: strict Typer invocation exited 2 because
--execution-ready was unknown. Ambient Python lacked tomlkit; installed declared
.[test] dependencies into /tmp/coga-execution-ready-venv. Focused CLI/validator
run then passed 239 tests in 3.72s before final formatting/rebase. The full
committed revision was separately verified below. No unresolved adjacent bugs.

Start was clean main at df5b042, with no recorded branch or PR. Branch linkage
was published before switching. Final fetch confirmed no incoming main commits;
tested branch pushed and checkout returned to clean, current main. No PR opened.
Implementing agent: this Codex session; precise runtime model identity is not
independently exposed (not inferred from ticket configuration).

Next: independent peer review. Native Windows/macOS verification is deferred to
release per coga-dev/testing; Python 3.11 floor was not exercised here.

## PR

```yaml
title: Add execution-ready validation preflight
author: codex
author_evidence: >-
  Implemented by this Codex session; exact runtime model identity is unavailable.
head: 44fedf0723b145a29f2272a6b6ac1f1f3ed99769
base: 919a60cfb8f48e9f5abcd038a70186ada6b6799e
depth: deep
rationale: >-
  Bounded opt-in severity change with passing full Linux verification;
  independent code review has not yet run and is the next workflow step.
implementation: >-
  Thread execution_ready through shared repo/task validation and expose
  --execution-ready in both CLI entrypoints. Promote missing-user to error
  only when requested; retain lenient defaults and existing remediation.
deviations: >-
  No local scheduling twin created because the package copy is the single
  committed owner after the repository cutover. No fixture changes needed
  for unchanged layout, prompt composition and workflow semantics.
limitations: >-
  Windows/macOS deferred to release. Python 3.11 floor not exercised;
  verification used Python 3.12.12. Network composition tested with deterministic
  probe stubs; no live Slack/GitHub authentication probe performed.
files:
  src/coga/commands/validate.py: >-
    Expose the Typer flag and forward it to repo/task validation.
  src/coga/validate.py: >-
    Select missing-user severity and expose equivalent argparse behavior.
  tests/test_cli.py: >-
    Exercise both entrypoints across output, scope, fixes, actors and network options.
  tests/test_validate.py: >-
    Verify shared validators and module entrypoint retain lenient defaults.
  docs/contexts/coga-dev/testing/SKILL.md: >-
    Direct execution checkouts to strict preflight and link the scheduling owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: >-
    Document strict preflight in every intended scheduler target checkout.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: >-
    Independent peer review belongs to the next workflow step.
checks:
  - command: PYTHONPATH=$PWD/src TERM=dumb /tmp/coga-execution-ready-venv/bin/python -m pytest --basetemp=/tmp/coga-execution-ready-pytest
    status: passed
    head: 44fedf0723b145a29f2272a6b6ac1f1f3ed99769
    base: 919a60cfb8f48e9f5abcd038a70186ada6b6799e
    detail: >-
      4947 passed, 34 skipped in 650.29s; Linux Pop!_OS 24.04 LTS,
      Python 3.12.12. Ran on clean committed head after rebase.
      Log retained at /tmp/coga-execution-ready-pytest.log.
  - command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/tmp/coga-quality-trial/src /tmp/coga-execution-ready-venv/bin/coga validate --execution-ready --json
    status: passed
    head: 44fedf0723b145a29f2272a6b6ac1f1f3ed99769
    base: 919a60cfb8f48e9f5abcd038a70186ada6b6799e
    detail: >-
      Exit 0; 5 tasks checked, no issues or fixes; 0.15s. Cwd
      tests/fixtures/seeded-repo/coga; Pop!_OS 24.04, Python 3.12.12.
  - command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/tmp/coga-quality-trial/src /tmp/coga-execution-ready-venv/bin/python -m coga.validate --json
    status: passed
    head: 44fedf0723b145a29f2272a6b6ac1f1f3ed99769
    base: 919a60cfb8f48e9f5abcd038a70186ada6b6799e
    detail: >-
      Exit 0; 5 tasks checked, no issues or fixes; 0.06s. Cwd
      tests/fixtures/seeded-repo/coga; Pop!_OS 24.04, Python 3.12.12.
  - command: Native Windows/macOS full suites and Python 3.11 floor verification
    status: not-run
    detail: >-
      Native checks deferred to release under repository policy;
      this implementation run used Linux Python 3.12.12.
```
````
