# Pair b030d4, output X (code)

## Commit messages

```
Add execution-ready validation for local actors

Task: fail-validation-when-local-user-is-required-for-ex
```

## Diff summary

```
docs/contexts/coga-dev/testing/SKILL.md            |   5 +
 src/coga/commands/validate.py                      |   7 ++
 .../bootstrap/contexts/coga/first-task/SKILL.md    |   8 +-
 .../contexts/coga/recurring/scheduling/SKILL.md    |  15 +++
 src/coga/validate.py                               |  23 ++--
 tests/test_cli.py                                  | 123 +++++++++++++++++++++
 tests/test_validate.py                             |  34 ++++++
 7 files changed, 207 insertions(+), 8 deletions(-)
```

## Diff

```diff
diff --git a/docs/contexts/coga-dev/testing/SKILL.md b/docs/contexts/coga-dev/testing/SKILL.md
index d584cc6..34fcf57 100644
--- a/docs/contexts/coga-dev/testing/SKILL.md
+++ b/docs/contexts/coga-dev/testing/SKILL.md
@@ -20,6 +20,11 @@ command with `PIP_REQUIRE_HASHES=0`. A venv made with `uv venv` (or
 `python -m venv --without-pip`) initially has no `pip`; `uv sync --extra test`
 or `uv pip install -e ".[test]"` installs all test tools, including pip. Run
 `coga validate --json` after config, workflow, or task-model changes.
+Before executing recurring work, require a successful
+`coga validate --execution-ready --json` in each scheduler target's checkout;
+add `--check-slack` / `--check-github` when testing service readiness.
+The [scheduler preflight](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md#scheduler-preflight)
+explains why an aggregate recurring sweep is insufficient.
 
 **Validate `tests/fixtures/seeded-repo/coga` with `env -u SLACK_WEBHOOK_URL coga validate --json`**
 when your shell exports that variable. The fixture has notifications off, and
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
index a48dd6b..f78d7d8 100644
--- a/src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md
+++ b/src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md
@@ -46,7 +46,13 @@ check reads the working-tree mode; on Windows, or with a repo-local
 skips a root that has neither source.
 
 Run `coga validate` again after any config, workflow, or ticket change. It
-warns when `user` is unset. Network probes are opt-in:
+warns when `user` is unset. `coga validate --execution-ready` promotes that
+same `missing-user` finding to an error and exits 1; ordinary validation
+keeps it a warning and exits 0 when there are no other errors. Use the strict
+mode before mutating or recurring work. It works with text or `--json`,
+whole-repo or `--task` checks, and `--fix`; repairs never invent an actor.
+Both `coga validate` and `python -m coga.validate` accept the flag.
+Network probes are opt-in:
 `coga validate --check-github` checks git and `gh` auth readiness, and
 `--check-slack` checks the Slack webhook
 ([coga/notifications](../notifications/SKILL.md)). Neither combines with
diff --git a/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md b/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md
index 8b071c7..803a428 100644
--- a/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md
+++ b/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md
@@ -8,6 +8,21 @@ description: How a recurring sweep runs due work — period keys and the service
 The repo-inactivity gate and `run_when_inactive` are in the leaf
 [coga/recurring/scheduling/inactivity](inactivity/SKILL.md).
 
+## Scheduler preflight
+
+Before invoking recurring work, run strict validation in each real scheduler
+target's checkout and proceed only on success:
+
+```sh
+coga validate --execution-ready --json && coga recurring
+```
+
+Add `--check-slack` and/or `--check-github` when provisioning should also
+probe those services. [Readiness checks](../../first-task/SKILL.md#0-check-readiness)
+own the validation modes and option contract. `recurring --all <path>`
+intentionally skips unconfigured checkouts, including ones without a local
+user; its aggregate success cannot replace this per-target preflight.
+
 ## Periods and the serviced-period ledger
 
 The scan takes each template's last firing strictly before now and buckets it
diff --git a/src/coga/validate.py b/src/coga/validate.py
index 9b1f7ca..9fe7b21 100644
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
+    """Report missing local identity, strictly when execution is required."""
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
+        help="Require a local user for executing mutating or recurring work.",
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
index acc3d77..f4aa1a6 100644
--- a/tests/test_cli.py
+++ b/tests/test_cli.py
@@ -194,6 +194,129 @@ def test_task_validate_runs_and_warns_without_user(clone: Path) -> None:
     assert missing_user[0]["severity"] == "warn"
 
 
+@pytest.mark.parametrize("entrypoint", ["typer", "module"])
+@pytest.mark.parametrize("json_output", [False, True])
+@pytest.mark.parametrize("task_only", [False, True])
+@pytest.mark.parametrize("fix", [False, True])
+def test_validate_execution_ready_requires_user(
+    clone: Path,
+    capsys: pytest.CaptureFixture[str],
+    entrypoint: str,
+    json_output: bool,
+    task_only: bool,
+    fix: bool,
+) -> None:
+    from coga.validate import _main
+
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
+    assert code == 1
+    if json_output:
+        issues = json.loads(output)["issues"]
+        missing = [issue for issue in issues if issue["kind"] == "missing-user"]
+        assert len(missing) == 1
+        assert missing[0]["severity"] == "error"
+        assert "coga.local.toml" in missing[0]["message"]
+    else:
+        assert "[ERROR] (config): missing-user" in output
+        assert "coga.local.toml" in output
+    assert not (clone / "coga.local.toml").exists()
+
+
+@pytest.mark.parametrize("entrypoint", ["typer", "module"])
+@pytest.mark.parametrize("checks", [["--check-slack"], ["--check-github"],
+                                     ["--check-slack", "--check-github"]])
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
+    probes: list[str] = []
+
+    def slack(cfg):
+        probes.append("--check-slack")
+        return []
+
+    def github(cfg):
+        probes.append("--check-github")
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
+    if task_only:
+        assert code == 2
+        assert "is not supported with --task" in output
+        assert probes == []
+    else:
+        assert code == 1
+        assert probes == checks
+        assert any(issue["kind"] == "missing-user" and issue["severity"] == "error"
+                   for issue in json.loads(output)["issues"])
+
+
+@pytest.mark.parametrize("entrypoint", ["typer", "module"])
+@pytest.mark.parametrize("task_only", [False, True])
+@pytest.mark.parametrize("execution_ready,has_user", [(False, False), (True, True)])
+def test_validate_execution_readiness_success(
+    clone: Path,
+    capsys: pytest.CaptureFixture[str],
+    entrypoint: str,
+    task_only: bool,
+    execution_ready: bool,
+    has_user: bool,
+) -> None:
+    from coga.validate import _main
+
+    if has_user:
+        _write(clone / "coga.local.toml", 'user = "marc"\n')
+    argv = ["--json"]
+    if execution_ready:
+        argv.append("--execution-ready")
+    if task_only:
+        argv.extend(["--task", "fix-retry-logic"])
+    if entrypoint == "typer":
+        result = CliRunner().invoke(app, ["validate", *argv])
+        code, output = result.exit_code, result.output
+    else:
+        code = _main(argv)
+        output = capsys.readouterr().out
+    assert code == 0
+    missing = [issue for issue in json.loads(output)["issues"]
+               if issue["kind"] == "missing-user"]
+    if has_user:
+        assert missing == []
+    else:
+        assert len(missing) == 1
+        assert missing[0]["severity"] == "warn"
+
+
 def test_usage_runs_without_user(clone: Path) -> None:
     result = CliRunner().invoke(app, ["usage"])
     assert result.exit_code == 0
diff --git a/tests/test_validate.py b/tests/test_validate.py
index 48cb8e1..3ae7cd8 100644
--- a/tests/test_validate.py
+++ b/tests/test_validate.py
@@ -63,6 +63,40 @@ def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
     return company
 
 
+@pytest.mark.parametrize("execution_ready", [False, True])
+@pytest.mark.parametrize("task_only", [False, True])
+@pytest.mark.parametrize("has_user", [False, True])
+def test_execution_ready_missing_user_severity(
+    repo: Path, execution_ready: bool, task_only: bool, has_user: bool
+) -> None:
+    _write(repo / "tasks" / "example.md", """
+        ---
+        title: Example
+        status: draft
+        owner: marc
+        agent: claude
+        workflow: null
+        ---
+
+        ## Description
+
+        <!-- coga:blackboard -->
+    """)
+    if not has_user:
+        (repo / "coga.local.toml").unlink()
+    cfg = load_config(repo, require_user=False)
+    if task_only:
+        report = validate_task(cfg, "example", execution_ready=execution_ready)
+    else:
+        report = run(cfg, execution_ready=execution_ready)
+    missing = [issue for issue in report.issues if issue.kind == "missing-user"]
+    if has_user:
+        assert missing == []
+    else:
+        assert len(missing) == 1
+        assert missing[0].severity == ("error" if execution_ready else "warn")
+
+
 def _write_skillless_release_workflow(
     repo: Path, *, instructions: str = "Ship the release."
 ) -> Path:
```

## Ticket blackboard at the end of the step (handoff, PR receipts)

````markdown
## Dev

branch: coga/execution-ready-validation

## Plan

Clean manual checkout on main, fetched and fast-forwarded before edits. Add an
opt-in execution_ready argument through both entrypoints and shared validators;
retain lenient config loading and promote only missing-user. Cover text/JSON,
task/fix, configured actor and network option combinations. Update the package
scheduling owner and local testing topic; no live scheduling twin exists under
the completed package-definition cutover.

## Implementation handoff

Implemented and pushed `coga/execution-ready-validation`; no PR opened.
The default missing-user warning remains unchanged. Strict validation reports
that same issue as an error (exit 1), including task-only and fix mode; no
actor is created. Network checks still run for repo validation and remain
incompatible with task-only checks. No recurring discovery behavior changed.

Regression evidence: before implementation, the new Typer regression failed
because the absent flag yielded exit 2 rather than 1. The original ambient
interpreters lacked pytest or tomlkit, so declared test extras were installed
in `/tmp/coga-quality-trial-venv`. An initial full run was interrupted for
reconciliation; the final complete receipt below is a fresh post-rebase run.
Earlier focused results are superseded by the recorded 235-test run.

No seeded-layout change was needed: this adds an opt-in validation mode and
leaves task layout, prompt composition and workflow semantics unchanged.
No adjacent bugs or unresolved implementation decisions found.

Feature commit and merge base are recorded below. A final fetch confirmed
that origin/main had not moved; branch is pushed and primary checkout is
back on clean, fast-forwarded main before writing this handoff. Next step:
independent peer review of the committed diff; native checks defer to release.

## PR

```yaml
title: "Add execution-ready validation for local actors"
author: "codex"
author_evidence: "Implemented by this Codex session; no delegated agents or model overrides were\
  \ used. Exact underlying model identity is not independently available in session metadata."
head: "c8399403c0f0e3a74d6b32b038359cc97b7f93c1"
base: "0461533d61639190462b779dd3b920569aae716e"
depth: "deep"
rationale: "Bounded opt-in behavior with passing Linux checks; independent code review belongs to\
  \ the next workflow step and has not run."
implementation: "Both CLI entrypoints forward execution_ready through whole-repo and single-task\
  \ validation. Only missing-user severity changes; lenient config loading, default diagnostics and\
  \ actor identity ownership are preserved."
deviations: "Updated the packaged scheduling owner only: the completed package-definition cutover\
  \ prohibits recreating a live twin. Added the CLI-owning first-task topic to keep the contract\
  \ in its canonical home."
limitations: "Native Windows and macOS checks are deferred to release by repository policy. Tested\
  \ on Python 3.12.12, without Python 3.11 floor evidence. Network combinations use deterministic\
  \ probe stubs; no live service probes were run."
files:
  docs/contexts/coga-dev/testing/SKILL.md: "Require strict validation before recurring execution\
    \ in each scheduler target."
  src/coga/commands/validate.py: "Expose and forward the Typer execution-ready flag."
  src/coga/validate.py: "Promote missing-user only in strict mode and expose the same flag through\
    \ argparse."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: "Own the validation\
    \ mode contract and supported combinations."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: "Document\
    \ per-target strict preflight and the aggregate discovery limitation."
  tests/test_cli.py: "Cover both entrypoints, output formats, task/fix modes, network composition,\
    \ default leniency and configured actors."
  tests/test_validate.py: "Cover core validators across strict/default modes and present/absent actors."
review:
  reviewer: "none"
  kind: "none"
  status: "not-run"
  detail: "Independent peer review is the next workflow step; implement does not perform formal code\
    \ review."
checks:
- command: "PYTHONPATH=$PWD/src TERM=dumb /tmp/coga-quality-trial-venv/bin/python -m pytest --basetemp=/tmp/coga-quality-trial-verified-pytest\
    \ -q"
  status: "passed"
  head: "c8399403c0f0e3a74d6b32b038359cc97b7f93c1"
  base: "0461533d61639190462b779dd3b920569aae716e"
  detail: "Pop!_OS 24.04 LTS Linux, Python 3.12.12: 4943 passed, 34 skipped in 638.38s. Run started\
    \ after commit and rebase on a clean feature tree; tracked implementation remained unchanged."
- command: "PYTHONPATH=$PWD/src TERM=dumb /tmp/coga-quality-trial-venv/bin/python -m pytest tests/test_cli.py\
    \ tests/test_validate.py -q"
  status: "passed"
  head: "c8399403c0f0e3a74d6b32b038359cc97b7f93c1"
  base: "0461533d61639190462b779dd3b920569aae716e"
  detail: "235 passed in 3.46s on the committed tree, same Linux environment."
- command: "env -u SLACK_WEBHOOK_URL PYTHONPATH=/tmp/coga-quality-trial/src /tmp/coga-quality-trial-venv/bin/coga\
    \ validate --execution-ready --json"
  status: "passed"
  head: "c8399403c0f0e3a74d6b32b038359cc97b7f93c1"
  base: "0461533d61639190462b779dd3b920569aae716e"
  detail: "From tests/fixtures/seeded-repo/coga: exit 0, 5 tasks checked, no issues or fixes."
- command: "env -u SLACK_WEBHOOK_URL PYTHONPATH=/tmp/coga-quality-trial/src /tmp/coga-quality-trial-venv/bin/coga\
    \ validate --json"
  status: "passed"
  head: "c8399403c0f0e3a74d6b32b038359cc97b7f93c1"
  base: "0461533d61639190462b779dd3b920569aae716e"
  detail: "From tests/fixtures/seeded-repo/coga: exit 0, 5 tasks checked, no issues or fixes."
- command: "git diff --check origin/main...HEAD"
  status: "passed"
  head: "c8399403c0f0e3a74d6b32b038359cc97b7f93c1"
  base: "0461533d61639190462b779dd3b920569aae716e"
  detail: "Exit 0; no whitespace errors on the committed feature branch."
```
````
