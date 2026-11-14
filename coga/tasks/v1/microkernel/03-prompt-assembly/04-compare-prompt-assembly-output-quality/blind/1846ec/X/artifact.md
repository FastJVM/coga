# Pair 1846ec, output X (code)

## Commit messages

```
Add execution-ready validation for missing local actors

Task: fail-validation-when-local-user-is-required-for-ex
```

## Diff summary

```
docs/contexts/coga-dev/testing/SKILL.md            |  6 ++
 src/coga/commands/validate.py                      |  7 ++
 .../bootstrap/contexts/coga/first-task/SKILL.md    |  9 ++-
 .../contexts/coga/recurring/scheduling/SKILL.md    | 16 ++++
 src/coga/validate.py                               | 19 +++--
 tests/test_cli.py                                  | 92 ++++++++++++++++++++++
 tests/test_validate.py                             | 24 ++++++
 7 files changed, 167 insertions(+), 6 deletions(-)
```

## Diff

```diff
diff --git a/docs/contexts/coga-dev/testing/SKILL.md b/docs/contexts/coga-dev/testing/SKILL.md
index d584cc6..0b5a605 100644
--- a/docs/contexts/coga-dev/testing/SKILL.md
+++ b/docs/contexts/coga-dev/testing/SKILL.md
@@ -20,6 +20,12 @@ command with `PIP_REQUIRE_HASHES=0`. A venv made with `uv venv` (or
 `python -m venv --without-pip`) initially has no `pip`; `uv sync --extra test`
 or `uv pip install -e ".[test]"` installs all test tools, including pip. Run
 `coga validate --json` after config, workflow, or task-model changes.
+Before invoking recurring work in a runner checkout, gate it with
+`coga validate --execution-ready --json && coga recurring` in that checkout.
+Use this strict preflight for every intended target of an aggregate sweep;
+see [scheduler preflight](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md#scheduler-preflight)
+and the [validation contract](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md#0-check-readiness).
+Ordinary validation remains suitable for fresh-clone diagnostics.
 
 **Validate `tests/fixtures/seeded-repo/coga` with `env -u SLACK_WEBHOOK_URL coga validate --json`**
 when your shell exports that variable. The fixture has notifications off, and
diff --git a/src/coga/commands/validate.py b/src/coga/commands/validate.py
index 98832e5..97d47e6 100644
--- a/src/coga/commands/validate.py
+++ b/src/coga/commands/validate.py
@@ -31,6 +31,11 @@ def validate(
         "--fix",
         help="Apply conservative safe repairs before reporting.",
     ),
+    execution_ready: bool = typer.Option(
+        False,
+        "--execution-ready",
+        help="Treat a missing local user as an error before executing work.",
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
index a48dd6b..cfd3790 100644
--- a/src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md
+++ b/src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md
@@ -46,7 +46,14 @@ check reads the working-tree mode; on Windows, or with a repo-local
 skips a root that has neither source.
 
 Run `coga validate` again after any config, workflow, or ticket change. It
-warns when `user` is unset. Network probes are opt-in:
+warns when `user` is unset so fresh-clone diagnostics remain usable.
+For a checkout expected to execute mutating or recurring work, use
+`coga validate --execution-ready`: the same `missing-user` finding becomes an
+error and validation exits 1. This applies to text, `--json`, and `--task`
+output; `--fix` cannot repair it because Coga must not invent the actor.
+Set `user` explicitly in that checkout's gitignored `coga.local.toml`.
+The `python -m coga.validate` entrypoint accepts the same flag.
+Network probes are opt-in and compose with `--execution-ready`:
 `coga validate --check-github` checks git and `gh` auth readiness, and
 `--check-slack` checks the Slack webhook
 ([coga/notifications](../notifications/SKILL.md)). Neither combines with
diff --git a/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md b/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md
index 8b071c7..679af4c 100644
--- a/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md
+++ b/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md
@@ -8,6 +8,22 @@ description: How a recurring sweep runs due work — period keys and the service
 The repo-inactivity gate and `run_when_inactive` are in the leaf
 [coga/recurring/scheduling/inactivity](inactivity/SKILL.md).
 
+## Scheduler preflight
+
+Before invoking recurring work, run strict validation in each real scheduler
+target's checkout and stop if it fails:
+
+```sh
+coga validate --execution-ready --json && coga recurring
+```
+
+The [validation contract](../../first-task/SKILL.md#0-check-readiness) explains
+local actor setup and optional `--check-slack` / `--check-github` probes.
+A successful ordinary validation or secret check does not establish execution
+readiness. `coga recurring --all <path>` intentionally skips unconfigured
+checkouts, including ones without a local user; its aggregate success cannot
+replace strict preflight in each intended target.
+
 ## Periods and the serviced-period ledger
 
 The scan takes each template's last firing strictly before now and buckets it
diff --git a/src/coga/validate.py b/src/coga/validate.py
index 9b1f7ca..8184abc 100644
--- a/src/coga/validate.py
+++ b/src/coga/validate.py
@@ -196,8 +196,8 @@ def _duplicate_slug_issue(exc: DuplicateTaskSlugError) -> Issue:
     )
 
 
-def _missing_user_issue(cfg: Config) -> Issue | None:
-    """Point a user-less clone at its machine-local setup without blocking reads."""
+def _missing_user_issue(cfg: Config, *, execution_ready: bool = False) -> Issue | None:
+    """Report missing local setup, blocking execution preflights only."""
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
+        help="Treat a missing local user as an error before executing work.",
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
index acc3d77..d0f9c5c 100644
--- a/tests/test_cli.py
+++ b/tests/test_cli.py
@@ -194,6 +194,98 @@ def test_task_validate_runs_and_warns_without_user(clone: Path) -> None:
     assert missing_user[0]["severity"] == "warn"
 
 
+@pytest.mark.parametrize("module_entrypoint", [False, True])
+@pytest.mark.parametrize("task_only", [False, True])
+@pytest.mark.parametrize("fix", [False, True])
+@pytest.mark.parametrize("json_output", [False, True])
+@pytest.mark.parametrize("configured_user", [False, True])
+def test_validate_execution_ready(
+    clone: Path,
+    capsys: pytest.CaptureFixture[str],
+    module_entrypoint: bool,
+    task_only: bool,
+    fix: bool,
+    json_output: bool,
+    configured_user: bool,
+) -> None:
+    from coga.validate import _main
+
+    if configured_user:
+        _write(clone / "coga.local.toml", 'user = "marc"\n')
+    args = ["--execution-ready"]
+    if task_only:
+        args += ["--task", "fix-retry-logic"]
+    if fix:
+        args.append("--fix")
+    if json_output:
+        args.append("--json")
+    if module_entrypoint:
+        exit_code = _main(args)
+        output = capsys.readouterr().out
+    else:
+        result = CliRunner().invoke(app, ["validate", *args])
+        exit_code, output = result.exit_code, result.output
+
+    assert exit_code == (0 if configured_user else 1)
+    if json_output:
+        issues = json.loads(output)["issues"]
+        missing_user = [i for i in issues if i["kind"] == "missing-user"]
+        assert len(missing_user) == (0 if configured_user else 1)
+        if missing_user:
+            assert missing_user[0]["severity"] == "error"
+            assert "coga.local.toml" in missing_user[0]["message"]
+    elif configured_user:
+        assert "missing-user" not in output
+    else:
+        assert "[ERROR] (config): missing-user" in output
+        assert "coga.local.toml" in output
+    assert (clone / "coga.local.toml").exists() == configured_user
+
+@pytest.mark.parametrize("module_entrypoint", [False, True])
+@pytest.mark.parametrize(
+    "checks",
+    [["--check-slack"], ["--check-github"], ["--check-slack", "--check-github"]],
+)
+@pytest.mark.parametrize("task_only", [False, True])
+def test_validate_execution_ready_network_checks(
+    clone: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+    module_entrypoint: bool,
+    checks: list[str],
+    task_only: bool,
+) -> None:
+    from coga.validate import Issue, _main
+
+    called: list[str] = []
+
+    def probe(name: str) -> list[Issue]:
+        called.append(name)
+        return [Issue(kind=name, task="(config)", message="probe failed", severity="error")]
+
+    monkeypatch.setattr("coga.validate._notification_issues", lambda cfg: probe("slack"))
+    monkeypatch.setattr("coga.validate._github_issues", lambda cfg: probe("github"))
+    args = ["--execution-ready", "--json", *checks]
+    if task_only:
+        args += ["--task", "fix-retry-logic"]
+    if module_entrypoint:
+        exit_code = _main(args)
+        captured = capsys.readouterr()
+        output = captured.out + captured.err
+    else:
+        result = CliRunner().invoke(app, ["validate", *args])
+        exit_code, output = result.exit_code, result.output
+    if task_only:
+        assert exit_code == 2
+        assert "not supported with --task" in output
+        assert called == []
+    else:
+        assert exit_code == 1
+        issues = {i["kind"]: i for i in json.loads(output)["issues"]}
+        assert issues["missing-user"]["severity"] == "error"
+        assert called == [check.removeprefix("--check-") for check in checks]
+        assert all(issues[name]["severity"] == "error" for name in called)
+
 def test_usage_runs_without_user(clone: Path) -> None:
     result = CliRunner().invoke(app, ["usage"])
     assert result.exit_code == 0
diff --git a/tests/test_validate.py b/tests/test_validate.py
index 48cb8e1..d87dd76 100644
--- a/tests/test_validate.py
+++ b/tests/test_validate.py
@@ -63,6 +63,30 @@ def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
     return company
 
 
+@pytest.mark.parametrize("execution_ready", [False, True])
+@pytest.mark.parametrize("task_only", [False, True])
+def test_missing_user_severity(repo: Path, execution_ready: bool, task_only: bool) -> None:
+    _write(repo / "tasks" / "example.md", """
+    ---
+    title: Example
+    status: draft
+    owner: marc
+    agent: claude
+    workflow: null
+    ---
+    <!-- coga:blackboard -->
+    """)
+    (repo / "coga.local.toml").unlink()
+    cfg = load_config(repo, require_user=False)
+    if task_only:
+        report = validate_task(cfg, "example", execution_ready=execution_ready)
+    else:
+        report = run(cfg, execution_ready=execution_ready)
+    missing_user = [i for i in report.issues if i.kind == "missing-user"]
+    assert len(missing_user) == 1
+    assert missing_user[0].severity == ("error" if execution_ready else "warn")
+    assert "coga.local.toml" in missing_user[0].message
+
 def _write_skillless_release_workflow(
     repo: Path, *, instructions: str = "Ship the release."
 ) -> Path:
```

## Ticket blackboard at the end of the step (handoff, PR receipts)

````markdown
## Dev

branch: coga/execution-ready-validation

Plan: thread an opt-in execution-ready policy through both validation entrypoints,
cover fresh-clone defaults and strict modes, and document scheduler preflight.
Checkout started clean on main, current with origin/main; no prior branch or PR
is recorded. Package-owned scheduling topic is the sole shipped owner; no local
twin will be recreated.


## Implementation handoff

Implemented and pushed `coga/execution-ready-validation` at
`635da1703d65399065baca338a27328d0cf8b557`. Latest origin/main is contained;
final fetch/rebase required no changes. Manual checkout returned to main.
No PR opened; peer review is next.

The opt-in policy changes only missing-user severity. Ordinary validation,
status/show/recurring-list fresh-clone behavior is retained. `--fix` never
creates a local actor. Network probes still run and retain their findings;
network checks with `--task` still exit 2. No fixture changes needed because
task layout, prompt composition and workflow semantics are unchanged.
No adjacent bugs or unresolved implementation questions found.

Development evidence (intermediate trees, not final commit receipts):
- Initial `python -m pytest tests/test_cli.py -q -k execution_ready` could not
  set up tests: 44 errors, 38 deselected due to missing tomlkit in system Python.
  Created /tmp/coga-execution-ready-venv and installed `.[test]` there.
- Before the fix, `TERM=dumb /tmp/coga-execution-ready-venv/bin/python -m pytest tests/test_cli.py -q -k execution_ready -x`
  failed as expected: 1 failed, 38 deselected (unknown flag exited 2).
- After wiring the flag, `TERM=dumb /tmp/coga-execution-ready-venv/bin/python -m pytest tests/test_cli.py tests/test_validate.py -q`
  passed 235 tests in 3.46s before adding the four core policy cases.
- Final committed-tree verification and exact OIDs are recorded below.

## PR

```yaml
"title": "Add execution-ready validation for missing local actors"
"author": "codex"
"author_evidence": "Implemented in this Codex session. Session model identifier and\
  \ reasoning overrides are not exposed; configured ticket agent was not used as execution\
  \ evidence."
"head": "635da1703d65399065baca338a27328d0cf8b557"
"base": "d91c13a52aafb9223a2e5ba77d4c9e08b2630cd9"
"depth": "deep"
"rationale": "Bounded opt-in validation change with full Linux coverage; independent\
  \ review is pending the next workflow step."
"implementation": "Thread execution_ready through repository and task validators and\
  \ both CLI entrypoints. Preserve diagnostic defaults, issue kind/message and actor\
  \ ownership. Add 48 regression cases and scheduler preflight documentation."
"deviations": "The repository has completed package-definition cutover: scheduling\
  \ has one package owner, so no unapproved local twin was recreated. Add the owning\
  \ first-task validation contract and link it from scheduling/testing."
"limitations": "No native Windows/macOS or Python 3.11 receipt; deferred to release.\
  \ Strict validation checks actor presence, not scheduler owner authorization or\
  \ agent authentication."
"files":
  "docs/contexts/coga-dev/testing/SKILL.md": "Document strict runner preflight and\
    \ link the owning user contracts."
  "src/coga/commands/validate.py": "Expose and forward --execution-ready in the Typer\
    \ CLI."
  "src/coga/validate.py": "Promote missing-user only for opt-in execution preflights\
    \ and expose the argparse flag."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md": "Own\
    \ the strict validation contract alongside existing validation documentation."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md": "Require\
    \ strict preflight per intended scheduler target before recurring work."
  "tests/test_cli.py": "Cover both entrypoints, text/JSON, task/fix, configured actors\
    \ and network probes."
  "tests/test_validate.py": "Cover shared validator severity policy for repository\
    \ and task validation."
"review":
  "reviewer": "none"
  "kind": "none"
  "status": "not-run"
  "detail": "Independent peer review is the next workflow step; implementation does\
    \ not perform that step."
"checks":
- "command": "PATH=/tmp/coga-execution-ready-venv/bin:$PATH PYTHONPATH=/tmp/coga-quality-trial/src\
    \ TERM=dumb python -m pytest"
  "status": "passed"
  "head": "635da1703d65399065baca338a27328d0cf8b557"
  "base": "d91c13a52aafb9223a2e5ba77d4c9e08b2630cd9"
  "detail": "4947 passed, 34 skipped, 0 failed in 663.59s. Pop!_OS 24.04 LTS, Linux\
    \ x86_64, Python 3.12.12. Ran on committed clean feature tree."
- "command": "env -u SLACK_WEBHOOK_URL /tmp/coga-execution-ready-venv/bin/coga validate\
    \ --json"
  "status": "passed"
  "head": "635da1703d65399065baca338a27328d0cf8b557"
  "base": "d91c13a52aafb9223a2e5ba77d4c9e08b2630cd9"
  "detail": "Exit 0; 5 tasks checked, no issues or fixes. Working directory: /tmp/coga-quality-trial/tests/fixtures/seeded-repo/coga.\
    \ Python 3.12.12 on Linux; each completed in under one second."
- "command": "env -u SLACK_WEBHOOK_URL /tmp/coga-execution-ready-venv/bin/coga validate\
    \ --execution-ready --json"
  "status": "passed"
  "head": "635da1703d65399065baca338a27328d0cf8b557"
  "base": "d91c13a52aafb9223a2e5ba77d4c9e08b2630cd9"
  "detail": "Exit 0; 5 tasks checked, no issues or fixes. Working directory: /tmp/coga-quality-trial/tests/fixtures/seeded-repo/coga.\
    \ Python 3.12.12 on Linux; each completed in under one second."
- "command": "env -u SLACK_WEBHOOK_URL /tmp/coga-execution-ready-venv/bin/python -m\
    \ coga.validate --execution-ready --json"
  "status": "passed"
  "head": "635da1703d65399065baca338a27328d0cf8b557"
  "base": "d91c13a52aafb9223a2e5ba77d4c9e08b2630cd9"
  "detail": "Exit 0; 5 tasks checked, no issues or fixes. Working directory: /tmp/coga-quality-trial/tests/fixtures/seeded-repo/coga.\
    \ Python 3.12.12 on Linux; each completed in under one second."
- "command": "Native Windows/macOS and Python 3.11 verification"
  "status": "not-run"
  "detail": "Deferred to release verification per coga-dev/testing; local interpreter\
    \ is Python 3.12.12."
```
````
