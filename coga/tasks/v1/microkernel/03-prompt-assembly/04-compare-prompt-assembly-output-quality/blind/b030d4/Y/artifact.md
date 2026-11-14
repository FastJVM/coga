# Pair b030d4, output Y (code)

## Commit messages

```
Add execution-ready validation for local actor setup

Task: fail-validation-when-local-user-is-required-for-ex
```

## Diff summary

```
docs/contexts/coga-dev/testing/SKILL.md            |  8 ++
 src/coga/commands/validate.py                      |  7 ++
 .../bootstrap/contexts/coga/first-task/SKILL.md    | 10 ++-
 .../contexts/coga/recurring/scheduling/SKILL.md    | 16 ++++
 src/coga/validate.py                               | 23 ++++--
 tests/test_cli.py                                  | 91 ++++++++++++++++++++++
 tests/test_validate.py                             | 61 +++++++++++++++
 7 files changed, 208 insertions(+), 8 deletions(-)
```

## Diff

```diff
diff --git a/docs/contexts/coga-dev/testing/SKILL.md b/docs/contexts/coga-dev/testing/SKILL.md
index d584cc6..eb48b97 100644
--- a/docs/contexts/coga-dev/testing/SKILL.md
+++ b/docs/contexts/coga-dev/testing/SKILL.md
@@ -21,6 +21,14 @@ command with `PIP_REQUIRE_HASHES=0`. A venv made with `uv venv` (or
 or `uv pip install -e ".[test]"` installs all test tools, including pip. Run
 `coga validate --json` after config, workflow, or task-model changes.
 
+Before invoking recurring work in a provisioned checkout, use
+`coga validate --execution-ready` (add `--check-slack` and `--check-github`
+when those probes apply). Run it separately in each intended target before an
+aggregate sweep. The [scheduler preflight](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md#scheduler-preflight)
+explains why discovery success is insufficient; the
+[validation contract](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md#0-check-readiness)
+owns strict versus diagnostic severity and exit behavior.
+
 **Validate `tests/fixtures/seeded-repo/coga` with `env -u SLACK_WEBHOOK_URL coga validate --json`**
 when your shell exports that variable. The fixture has notifications off, and
 the config-load guard rejects a bare exported `SLACK_WEBHOOK_URL` with no
diff --git a/src/coga/commands/validate.py b/src/coga/commands/validate.py
index 98832e5..50dbfd3 100644
--- a/src/coga/commands/validate.py
+++ b/src/coga/commands/validate.py
@@ -31,6 +31,11 @@ def validate(
         "--fix",
         help="Apply conservative safe repairs before reporting.",
     ),
+    execution_ready: bool = typer.Option(
+        False,
+        "--execution-ready",
+        help="Require a local user for executing mutating or recurring work.",
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
diff --git a/src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md b/src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md
index a48dd6b..e1c39b7 100644
--- a/src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md
+++ b/src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md
@@ -46,7 +46,15 @@ check reads the working-tree mode; on Windows, or with a repo-local
 skips a root that has neither source.
 
 Run `coga validate` again after any config, workflow, or ticket change. It
-warns when `user` is unset. Network probes are opt-in:
+warns when `user` is unset, keeping fresh-clone diagnostics usable. Add
+`--execution-ready` for a preflight before mutating or recurring work: the
+same `missing-user` issue becomes an error and validation exits 1. This works
+for whole-repo and `--task` validation, in text or `--json`, including with
+`--fix`; Coga never invents the actor. Set `user = "<name>"` in the checkout's
+`coga.local.toml` yourself. Both `coga validate` and `python -m coga.validate`
+accept this flag.
+
+Network probes are opt-in and compose with `--execution-ready`:
 `coga validate --check-github` checks git and `gh` auth readiness, and
 `--check-slack` checks the Slack webhook
 ([coga/notifications](../notifications/SKILL.md)). Neither combines with
diff --git a/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md b/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md
index 8b071c7..8913656 100644
--- a/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md
+++ b/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md
@@ -8,6 +8,22 @@ description: How a recurring sweep runs due work — period keys and the service
 The repo-inactivity gate and `run_when_inactive` are in the leaf
 [coga/recurring/scheduling/inactivity](inactivity/SKILL.md).
 
+## Scheduler preflight
+
+Before invoking recurring work, validate each intended scheduler checkout:
+
+```sh
+coga validate --execution-ready --check-slack --check-github && coga recurring
+```
+
+Choose the network probes appropriate to that checkout. The
+[strict validation contract](../../first-task/SKILL.md#0-check-readiness)
+requires a configured local actor; ordinary diagnostic validation can succeed
+without one. Provision the intended `user` in `coga.local.toml` explicitly.
+Run this preflight in every real target before a `coga recurring --all <path>`
+sweep: discovery intentionally skips unconfigured checkouts, so aggregate
+success does not prove that each intended target could execute.
+
 ## Periods and the serviced-period ledger
 
 The scan takes each template's last firing strictly before now and buckets it
diff --git a/src/coga/validate.py b/src/coga/validate.py
index 9b1f7ca..62e50a0 100644
--- a/src/coga/validate.py
+++ b/src/coga/validate.py
@@ -3,8 +3,8 @@
 Exposed as `coga validate` (see `coga.commands.validate`); also runnable
 directly as a module:
 
-    coga validate [--json] [--task <slug>] [--fix] [--max-blackboard-kb N] [--check-slack] [--check-github]
-    python -m coga.validate [--json] [--task <slug>] [--fix] [--max-blackboard-kb N] [--check-slack] [--check-github]
+    coga validate [--json] [--task <slug>] [--fix] [--execution-ready] [--max-blackboard-kb N] [--check-slack] [--check-github]
+    python -m coga.validate [--json] [--task <slug>] [--fix] [--execution-ready] [--max-blackboard-kb N] [--check-slack] [--check-github]
 
 Two entry points:
 - `run(cfg, ...)` — whole-repo sweep (every task under `coga/tasks/`).
@@ -196,8 +196,8 @@ def _duplicate_slug_issue(exc: DuplicateTaskSlugError) -> Issue:
     )
 
 
-def _missing_user_issue(cfg: Config) -> Issue | None:
-    """Point a user-less clone at its machine-local setup without blocking reads."""
+def _missing_user_issue(cfg: Config, *, execution_ready: bool = False) -> Issue | None:
+    """Report missing actor setup, optionally as an execution preflight error."""
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
@@ -1998,6 +2000,11 @@ def _main(argv: list[str] | None = None) -> int:
         action="store_true",
         help="Also probe git/GitHub auth readiness via git/gh (network call).",
     )
+    parser.add_argument(
+        "--execution-ready",
+        action="store_true",
+        help="Require a local user for executing mutating or recurring work.",
+    )
     args = parser.parse_args(argv)
 
     try:
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
index acc3d77..fdcdb40 100644
--- a/tests/test_cli.py
+++ b/tests/test_cli.py
@@ -547,3 +547,94 @@ def test_launch_adapter_keeps_windows_dword_exit_codes(
     result = CliRunner().invoke(app, ["launch", "x"])
     assert result.exit_code == expected
     assert expected & 0xFFFFFFFF == code
+
+
+@pytest.mark.parametrize("entrypoint", ["typer", "module"])
+@pytest.mark.parametrize("json_output", [False, True])
+@pytest.mark.parametrize("task_only", [False, True])
+@pytest.mark.parametrize("fix", [False, True])
+@pytest.mark.parametrize("configured", [False, True])
+def test_validate_execution_ready(
+    clone: Path,
+    capsys: pytest.CaptureFixture[str],
+    entrypoint: str,
+    json_output: bool,
+    task_only: bool,
+    fix: bool,
+    configured: bool,
+) -> None:
+    from coga.validate import _main
+
+    if configured:
+        _write(clone / "coga.local.toml", 'user = "marc"\n')
+    args = ["--execution-ready"]
+    if json_output:
+        args.append("--json")
+    if task_only:
+        args.extend(["--task", "fix-retry-logic"])
+    if fix:
+        args.append("--fix")
+    if entrypoint == "typer":
+        result = CliRunner().invoke(app, ["validate", *args])
+        code, output = result.exit_code, result.output
+    else:
+        code = _main(args)
+        output = capsys.readouterr().out
+    assert code == (0 if configured else 1)
+    if json_output:
+        issues = json.loads(output)["issues"]
+        missing = [i for i in issues if i["kind"] == "missing-user"]
+        assert len(missing) == (0 if configured else 1)
+        if missing:
+            assert missing[0]["severity"] == "error"
+            assert "coga.local.toml" in missing[0]["message"]
+    elif not configured:
+        assert "[ERROR] (config): missing-user" in output
+    assert (clone / "coga.local.toml").exists() == configured
+
+
+@pytest.mark.parametrize("entrypoint", ["typer", "module"])
+@pytest.mark.parametrize("network_flags", [
+    ["--check-slack"], ["--check-github"], ["--check-slack", "--check-github"],
+])
+@pytest.mark.parametrize("task_only", [False, True])
+def test_validate_execution_ready_network_checks(
+    clone: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+    entrypoint: str,
+    network_flags: list[str],
+    task_only: bool,
+) -> None:
+    from coga.validate import _main
+
+    calls: list[str] = []
+
+    def slack(cfg):
+        calls.append("--check-slack")
+        return []
+
+    def github(cfg):
+        calls.append("--check-github")
+        return []
+
+    monkeypatch.setattr("coga.validate._notification_issues", slack)
+    monkeypatch.setattr("coga.validate._github_issues", github)
+    args = ["--execution-ready", "--json", *network_flags]
+    if task_only:
+        args.extend(["--task", "fix-retry-logic"])
+    if entrypoint == "typer":
+        result = CliRunner().invoke(app, ["validate", *args])
+        code, output = result.exit_code, result.output
+    else:
+        code = _main(args)
+        captured = capsys.readouterr()
+        output = captured.out + captured.err
+    assert code == (2 if task_only else 1)
+    if task_only:
+        assert "not supported with --task" in output
+        assert calls == []
+    else:
+        assert calls == network_flags
+        assert any(i["kind"] == "missing-user" and i["severity"] == "error"
+                   for i in json.loads(output)["issues"])
diff --git a/tests/test_validate.py b/tests/test_validate.py
index 48cb8e1..991df7b 100644
--- a/tests/test_validate.py
+++ b/tests/test_validate.py
@@ -3095,3 +3095,64 @@ def test_validate_accepts_absent_resource_root(repo: Path) -> None:
     report = run(load_config(repo))
 
     assert not [i for i in report.issues if i.kind == "unreadable-resource-override"]
+
+
+@pytest.mark.parametrize("execution_ready", [False, True])
+@pytest.mark.parametrize("task_only", [False, True])
+def test_missing_user_severity_is_opt_in(
+    repo: Path, execution_ready: bool, task_only: bool,
+) -> None:
+    _write(repo / "tasks" / "inspect.md", """
+        ---
+        title: Inspect
+        status: draft
+        owner: marc
+        agent: claude
+        workflow: null
+        ---
+        ## Description
+        Inspect readiness.
+        <!-- coga:blackboard -->
+    """)
+    (repo / "coga.local.toml").unlink()
+    cfg = load_config(repo, require_user=False)
+    if task_only:
+        report = validate_task(cfg, "inspect", execution_ready=execution_ready)
+    else:
+        report = run(cfg, execution_ready=execution_ready)
+    missing = [issue for issue in report.issues if issue.kind == "missing-user"]
+    assert len(missing) == 1
+    assert missing[0].severity == ("error" if execution_ready else "warn")
+
+
+@pytest.mark.parametrize("task_only", [False, True])
+@pytest.mark.parametrize("json_output", [False, True])
+def test_main_warns_without_user_by_default(
+    repo: Path, monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str], task_only: bool, json_output: bool,
+) -> None:
+    _write(repo / "tasks" / "inspect.md", """
+        ---
+        title: Inspect
+        status: draft
+        owner: marc
+        agent: claude
+        workflow: null
+        ---
+        ## Description
+        Inspect readiness.
+        <!-- coga:blackboard -->
+    """)
+    (repo / "coga.local.toml").unlink()
+    monkeypatch.chdir(repo)
+    args = ["--task", "inspect"] if task_only else []
+    if json_output:
+        args.append("--json")
+    assert _main(args) == 0
+    output = capsys.readouterr().out
+    if json_output:
+        missing = [i for i in json.loads(output)["issues"] if i["kind"] == "missing-user"]
+        assert len(missing) == 1
+        assert missing[0]["severity"] == "warn"
+    else:
+        assert "[WARN] (config): missing-user" in output
```

## Ticket blackboard at the end of the step (handoff, PR receipts)

````markdown
## Dev

branch: coga/fail-validation-execution-ready

## Implement handoff

Implemented and pushed `coga/fail-validation-execution-ready`. Both entrypoints
thread `execution_ready` into shared missing-user reporting for repo and task
validation. Defaults stay diagnostic-friendly; strict mode errors without an
actor, including under `--fix`. Network probes still run when requested and
retain their task-scope incompatibility.

Regression demonstrated before implementation: strict validation exited 2
because the flag was unknown, instead of the required 1. Final coverage spans
both entrypoints, text/JSON, task/repo, configured/missing actor, fixes,
network combinations, and module-default warnings. Existing status/show and
other read-only fresh-clone tests pass. Initial ambient Python lacked tomlkit;
created `/tmp/coga-validation-venv` with editable test extras and used it for
verification. Initial focused run passed 235 cases; final focused run passed
243 after adding shared API and module-default regressions.

Updated the validation contract owner (`coga/first-task`), packaged scheduler
preflight and local testing guidance. No local scheduling twin was created:
package ownership rules prohibit duplicate live definitions. Seeded fixture
unchanged because actor provisioning/layout/workflows are unchanged; both
validation modes checked its five tasks without issues. No adjacent issues or
unresolved implementation questions found. No PR opened; peer review is next.

Verification platform: Pop!_OS 24.04 LTS, Linux, Python 3.12.12. Python 3.11
floor and native Windows/macOS checks are deferred to release. The committed
tree was verified identical to the tested working tree with clean staged and
unstaged diffs. Final fetch/rebase made no changes; branch remains pushed at
the recorded head, and manual return left this checkout on clean main before
writing this handoff.

## PR

```yaml
"title": "Add execution-ready validation for local actor setup"
"author": "codex"
"author_evidence": "Implemented in this Codex (GPT-6) session; no agent override or\
  \ delegated implementation."
"head": "373470bf7c88fe03b7381c37591c86748893037d"
"base": "4da73b4cbbd58ade44df1c3a39373c5708fcb754"
"depth": "deep"
"rationale": "Bounded opt-in severity change with full Linux verification; independent\
  \ review has not run and belongs to the next workflow step."
"implementation": "Expose --execution-ready in Typer and module entrypoints; promote\
  \ only missing-user to error through shared repo/task reporting. Document strict\
  \ preflight per scheduler target."
"deviations": "No duplicate local scheduling topic: shipped topics have a single packaged\
  \ owner under repository packaging rules. Seeded fixture needs no content changes."
"limitations": "Network combinations use deterministic probe stubs. Native Windows/macOS\
  \ and Python 3.11 floor verification are deferred to release."
"files":
  "docs/contexts/coga-dev/testing/SKILL.md": "Direct recurring-work preflight to strict\
    \ validation and link the user contract."
  "src/coga/commands/validate.py": "Expose and forward the opt-in flag from the Typer\
    \ command."
  "src/coga/validate.py": "Select missing-user severity in shared reporting and expose\
    \ identical argparse behavior."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md": "Own\
    \ the strict validation flag, scope, output, fix and network composition contract."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md": "Show\
    \ strict preflight before recurring work and explain per-target aggregate provisioning\
    \ checks."
  "tests/test_cli.py": "Cover both entrypoints across actor setup, output modes, task\
    \ scope, fixes and network combinations."
  "tests/test_validate.py": "Cover shared severity selection and module default warning\
    \ behavior."
"review":
  "reviewer": "none"
  "kind": "none"
  "status": "not-run"
  "detail": "Independent peer review is the next workflow step; this implement step\
    \ does not perform self-QA."
"checks":
- "command": "PYTHONPATH=$PWD/src /tmp/coga-validation-venv/bin/python -m pytest tests/test_cli.py\
    \ tests/test_validate.py -q"
  "status": "passed"
  "head": "373470bf7c88fe03b7381c37591c86748893037d"
  "base": "4da73b4cbbd58ade44df1c3a39373c5708fcb754"
  "detail": "243 passed in 3.50s on Linux, Python 3.12.12."
- "command": "PATH=/tmp/coga-validation-venv/bin:$PATH PYTHONPATH=$PWD/src TERM=dumb\
    \ python -m pytest"
  "status": "passed"
  "head": "373470bf7c88fe03b7381c37591c86748893037d"
  "base": "4da73b4cbbd58ade44df1c3a39373c5708fcb754"
  "detail": "4951 passed, 34 skipped in 647.52s on Pop!_OS 24.04 LTS, Python 3.12.12.\
    \ Committed tree identical to tested tree."
- "command": "cd tests/fixtures/seeded-repo/coga && env -u SLACK_WEBHOOK_URL PYTHONPATH=/tmp/coga-quality-trial/src\
    \ /tmp/coga-validation-venv/bin/coga validate --execution-ready --json"
  "status": "passed"
  "head": "373470bf7c88fe03b7381c37591c86748893037d"
  "base": "4da73b4cbbd58ade44df1c3a39373c5708fcb754"
  "detail": "Exit 0, five tasks checked, no issues or fixes; 0.15s."
- "command": "cd tests/fixtures/seeded-repo/coga && env -u SLACK_WEBHOOK_URL PYTHONPATH=/tmp/coga-quality-trial/src\
    \ /tmp/coga-validation-venv/bin/coga validate --json"
  "status": "passed"
  "head": "373470bf7c88fe03b7381c37591c86748893037d"
  "base": "4da73b4cbbd58ade44df1c3a39373c5708fcb754"
  "detail": "Exit 0, five tasks checked, no issues or fixes; 0.14s."
- "command": "git diff --check"
  "status": "passed"
  "head": "373470bf7c88fe03b7381c37591c86748893037d"
  "base": "4da73b4cbbd58ade44df1c3a39373c5708fcb754"
  "detail": "Exit 0; no whitespace errors."
- "command": "Native Windows/macOS and Python 3.11 floor verification"
  "status": "not-run"
  "detail": "Deferred to release under coga-dev/testing; Linux used Python 3.12.12."
```
````
