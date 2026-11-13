"""Disposable trial adapter for ticket 02 (owner-approved scope, 2026-11-12).

Not a reusable harness and not product code. Run only with the pinned venv's
Python (non-editable Coga at c66f6437). It rebuilds the isolated fixture at the
manifest's render root from `approved/fixtures`, injects frozen prompt bytes at
the existing seams, and captures evidence under `runs/`.

  adapter.py pristine                     build per-case pristine snapshots
  adapter.py run <case> <arm> <rep>       one session (interactive ones need a TTY)
  adapter.py control <arm> <n>            deterministic control (no prompt/agent)
  adapter.py transport                    non-model transport/parser checks
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
APPROVED = HERE / "approved"
RUNS = Path(os.environ.get("TRIAL_RUNS", HERE / "runs"))
ROOT = Path("/tmp/coga-prompt-trial-667707cc")
ORIGIN = Path("/tmp/coga-prompt-trial-667707cc-origin.git")
PRISTINE = Path(os.environ.get("TRIAL_PRISTINE", "/tmp/coga-prompt-trial-pristine"))
SINK_PORT = int(os.environ.get("TRIAL_SINK_PORT", "48765"))
MARKER_RE = re.compile(r"\n\ncoga-launch: [0-9a-f-]{36}\n\Z")
FIXED = {
    "GIT_AUTHOR_NAME": "Trial Fixture", "GIT_AUTHOR_EMAIL": "trial@example.invalid",
    "GIT_COMMITTER_NAME": "Trial Fixture", "GIT_COMMITTER_EMAIL": "trial@example.invalid",
    "GIT_AUTHOR_DATE": "2026-11-12T00:00:00Z", "GIT_COMMITTER_DATE": "2026-11-12T00:00:00Z",
}
PINS = ('-m gpt-6.1-sol -c model_reasoning_effort="medium" -a never '
        # Deviation D4 (owner, 2026-11-13): a permission profile replaces
        # `-s workspace-write`, whose protected <root>/.git blocked agent bumps.
        "-c 'permissions.trial.filesystem={\":root\"=\"read\",\":slash_tmp\"=\"write\","
        "\"/tmp/coga-prompt-trial-667707cc/.git\"=\"write\"}' "
        "-c permissions.trial.network.enabled=true "
        "-c 'default_permissions=\"trial\"' "
        # Deviation D2: pre-trust the trial root so no trust dialog appears.
        "-c 'projects.\"/tmp/coga-prompt-trial-667707cc\".trust_level=\"trusted\"'")
CODEX_AGENT = f'''
[agents.codex]
cli = "codex"
file = "AGENTS.md"
mode = "local"
launch_args = "--no-daemon {PINS.replace(chr(92), chr(92)*2).replace('"', chr(92)+'"')}"
discussion = "-c developer_instructions={{prompt}}"
analyze = "{PINS.replace(' -a never', '').replace(chr(92), chr(92)*2).replace('"', chr(92)+'"')} exec {{prompt}}"

[telemetry]
enabled = false
'''
_STUB_DIR = os.environ.get("TRIAL_STUB_DIR", "")  # captured before env is cleared
ENV_KEYS = {"HOME", "USER", "LOGNAME", "TERM", "LANG", "SHELL", "TMPDIR", "COLORTERM"}

CASES = {c["case"]: c for c in json.loads((APPROVED / "fixtures/cases.json").read_text())}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(*args: str, cwd: Path = ROOT, env: dict | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True, env={**os.environ, **(env or {})}).stdout


def allowlist_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in ENV_KEYS or k.startswith("LC_")}
    stub = [_STUB_DIR] if _STUB_DIR else []
    env["PATH"] = os.pathsep.join([*stub, str(Path(sys.executable).parent),
                                   str(Path.home() / ".local/bin"),
                                   "/usr/local/bin", "/usr/bin", "/bin"])
    return env


# --- fixtures ---------------------------------------------------------------

def config_text(case: str) -> str:
    base = (APPROVED / "fixtures/configuration.toml").read_text()
    # Deviation D1: the approved file puts `user` in shared config, which the
    # real loader rejects; it moves to coga.local.toml (see local_text()).
    base = base.replace('user = "trial-owner"\n', "")
    if case == "deterministic-control":
        # No configured agents at all for the control.
        base = re.sub(r"\[agents\.claude\]\n(?:[^\[\n].*\n)*", "", base)
        return base + "\n[telemetry]\nenabled = false\n"
    if case == "stateless-recurring":
        base = base.replace(
            "[notification.slack]\nenabled = false",
            f'[notification.slack]\nenabled = true\nwebhook = "http://127.0.0.1:{SINK_PORT}/hook"')
    return base + CODEX_AGENT


def build_pristine(case: str) -> dict:
    for p in (ROOT, ORIGIN):
        if p.exists():
            shutil.rmtree(p)
    ROOT.mkdir(parents=True)
    shutil.copytree(APPROVED / "fixtures/common", ROOT, dirs_exist_ok=True)
    overlay = APPROVED / "fixtures/cases" / case / "coga"
    if overlay.is_dir():
        shutil.copytree(overlay, ROOT / "coga", dirs_exist_ok=True)
    (ROOT / "coga/coga.toml").write_text(config_text(case))
    (ROOT / "coga/coga.local.toml").write_text('user = "trial-owner"\n')
    (ROOT / "coga/.gitignore").write_text(".agent-skills/\ncoga.local.toml\n")
    git("init", "-q", "-b", "main")
    git("add", "-A")
    git("commit", "-q", "-m", f"Trial fixture: {case}", env=FIXED)
    oid = git("rev-parse", "HEAD").strip()
    git("branch", "trial/assist")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(ORIGIN)], check=True)
    git("remote", "add", "origin", str(ORIGIN))
    git("push", "-q", "origin", "main", "trial/assist")
    git("fetch", "-q", "origin")
    git("branch", "-q", "--set-upstream-to=origin/main", "main")
    PRISTINE.mkdir(parents=True, exist_ok=True)
    with tarfile.open(PRISTINE / f"{case}.tar", "w") as tar:
        tar.add(ROOT, arcname="root")
        tar.add(ORIGIN, arcname="origin")
    return {"case": case, "commit": oid,
            "config_sha256": sha((ROOT / "coga/coga.toml").read_bytes())}


def reset(case: str) -> None:
    for p in (ROOT, ORIGIN):
        if p.exists():
            shutil.rmtree(p)
    with tarfile.open(PRISTINE / f"{case}.tar") as tar:
        for m in tar.getmembers():
            dest = ROOT if m.name.split("/")[0] == "root" else ORIGIN
            m.name = "/".join(m.name.split("/")[1:]) or "."
            tar.extract(m, dest, filter="tar")


# --- evidence ---------------------------------------------------------------

def state(case: str) -> dict:
    out = {
        "head": git("rev-parse", "HEAD").strip(),
        "branch": git("branch", "--show-current").strip(),
        "status": git("status", "--porcelain", "--untracked-files=all"),
        "origin_refs": git("for-each-ref", "--format=%(refname) %(objectname)", cwd=ORIGIN),
        "local_refs": git("for-each-ref", "--format=%(refname) %(objectname)"),
        "files": {},
    }
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and ".git" not in p.parts and ".agent-skills" not in p.parts:
            out["files"][str(p.relative_to(ROOT))] = sha(p.read_bytes())
    out["tree_sha256"] = sha(json.dumps(out["files"], sort_keys=True).encode())
    return out


LIVE = Path("/home/n/Code/coga")


def live_guard() -> dict:
    """Live-repo state, excluding this ticket's own (controller-written) dir."""
    own = str(HERE.relative_to(LIVE))
    status = [l for l in git("status", "--porcelain", "--untracked-files=all", cwd=LIVE).splitlines()
              if own not in l]
    return {"head": git("rev-parse", "HEAD", cwd=LIVE).strip(), "status": status}


def sandbox_of(rollout: Path) -> list:
    seen = []
    for line in rollout.read_text().splitlines():
        if '"sandbox_policy"' in line:
            pay = json.loads(line).get("payload", {})
            pol = {"sandbox_policy": pay.get("sandbox_policy"),
                   "permission_profile": pay.get("permission_profile")}
            if pol["sandbox_policy"] and pol not in seen:
                seen.append(pol)
    return seen


def frontmatter(path: Path) -> dict:
    if not path.is_file():
        return {}
    import yaml
    text = path.read_text()
    return yaml.safe_load(text.split("---", 2)[1]) if text.startswith("---") else {}


def codex_sessions() -> set[Path]:
    base = Path.home() / ".codex/sessions"
    return set(base.rglob("*.jsonl")) if base.is_dir() else set()


def rollout_cwd(rollout: Path) -> str:
    with contextlib.suppress(Exception):
        with rollout.open() as fh:
            return json.loads(fh.readline()).get("payload", {}).get("cwd", "")
    return ""


def run_dir(case: str, arm: str, rep: int) -> Path:
    d = RUNS / f"{case}__{arm}__r{rep}"
    if d.exists():
        raise SystemExit(f"{d} exists; runs are never overwritten")
    d.mkdir(parents=True)
    return d


def frozen(case: str, arm: str) -> bytes:
    return (APPROVED / "prompts" / case / f"{arm}.md").read_bytes()


# --- interactive ------------------------------------------------------------

def run_interactive(case: str, arm: str, rep: int) -> None:
    from coga import launch as L
    from coga.config import load_config, build_launch_env
    from coga.repl_supervisor import build_supervised_step_env, CHECKOUT_RETURN_ENV
    from coga.tasks import resolve_target, read_ticket

    spec = CASES[case]
    inv = spec["invocation"]
    reset(case)
    d = run_dir(case, arm, rep)
    os.chdir(ROOT)
    pre_sessions = codex_sessions()
    record: dict = {"case": case, "arm": arm, "rep": rep, "invocation": inv,
                    "start_utc": datetime.now(timezone.utc).isoformat()}
    raw = frozen(case, arm).decode()
    assert MARKER_RE.search(raw), "frozen prompt lacks its illustrative marker"
    composed = MARKER_RE.sub("\n", raw)

    if case == "owner-assist":
        git("switch", "-q", "trial/assist")
    if case == "script-handoff":
        from coga.launch_script import run_script_phase
        cfg = load_config()
        ref = resolve_target(cfg, inv["target"])
        res = run_script_phase(cfg, ref, read_ticket(ref), stateless=False)
        record["script_phase"] = repr(res)
        exp = APPROVED / "fixtures/cases/script-handoff/post-script/coga/tasks/script-handoff"
        record["post_script_matches"] = {
            n: (ROOT / "coga/tasks/script-handoff" / n).read_bytes() == (exp / n).read_bytes()
            for n in ("ticket.md", "prepared.txt")}
        for n in ("ticket.md", "prepared.txt"):
            src = ROOT / "coga/tasks/script-handoff" / n
            if src.is_file():
                shutil.copy(src, d / f"post-script-{n}")

    cfg = load_config()
    ref = resolve_target(cfg, inv["target"])
    ticket = read_ticket(ref)
    agent = cfg.agent_type("codex")
    record["pre"] = state(case)
    record["live_guard_pre"] = live_guard()
    record["config_sha256"] = sha((ROOT / "coga/coga.toml").read_bytes())

    delivered: dict = {}
    real_write = L.write_prompt_file

    def capture_prompt(prompt, ref_):
        delivered["bytes"] = prompt.encode()
        return real_write(prompt, ref_)
    L.write_prompt_file = capture_prompt
    real_run = L.run_with_done_marker

    def capture_cmd(cmd, env, **kw):
        p = delivered.get("bytes", b"").decode()
        record["argv"] = [(f"<prompt sha256={sha(a.encode())} bytes={len(a.encode())}>"
                           if a and (a == p or a.endswith(p[-200:]) and len(a) > 1000) else a)
                          for a in cmd]
        record["env_keys"] = sorted(env)
        return real_run(cmd, env, **kw)
    L.run_with_done_marker = capture_cmd

    base = allowlist_env()
    kw = dict(max_session=720.0, launch_context=inv["launch_context"],
              include_blocker_preamble=inv.get("include_blocker_preamble", True),
              composed_prompt=composed, commit_log=True)
    if inv["operation"] == "author":
        from coga.commands.ticket import _authoring_ticket, AUTHORING_SKILL
        from coga.config import scrub_op_auth_env
        auth_ticket = _authoring_ticket(ticket)
        call = dict(env=scrub_op_auth_env(base), actor=f"human:{cfg.current_user}",
                    log_message="ticket authoring launched (trial adapter)",
                    discussion=True, kickoff=inv["kickoff"], label="Ticket",
                    secrets_are_scoped=False,
                    stateless_identity=(AUTHORING_SKILL, ticket.title or ""))
        kw["include_blocker_preamble"] = False
        tk = auth_ticket
    else:
        env = build_supervised_step_env(
            build_launch_env(cfg, ticket.secrets, base_env=base),
            task_path=ref.path, step=getattr(ticket, "step", None), agent="codex")
        if inv.get("checkout"):
            env[CHECKOUT_RETURN_ENV] = "1"
        actor = "megalaunch" if inv["launch_context"] == "megalaunch" else f"human:{cfg.current_user}"
        call = dict(env=env, actor=actor, log_message=f"trial adapter launch ({case})",
                    name=ticket.title or "")
        tk = ticket
    record["spawn_kwargs"] = {k: v for k, v in {**kw, **call}.items()
                              if k not in ("env", "composed_prompt")}
    (d / "record.json").write_text(json.dumps(record, indent=1, default=str))
    t0 = time.monotonic()
    try:
        result = L.spawn_agent_session(cfg, ref, tk, agent, **call, **kw)
        record["result"] = result._asdict()
    except BaseException as exc:  # record, never hide
        record["result"] = {"exception": repr(exc)}
    record["wall_seconds"] = round(time.monotonic() - t0, 1)
    record["end_utc"] = datetime.now(timezone.utc).isoformat()
    finish(case, arm, d, record, delivered.get("bytes", b""), raw, pre_sessions)


def finish(case, arm, d, record, delivered: bytes, raw: str, pre_sessions) -> None:
    norm = re.sub(rb"coga-launch: [0-9a-f-]{36}", b"coga-launch: X", delivered)
    want = re.sub(rb"coga-launch: [0-9a-f-]{36}", b"coga-launch: X", raw.encode())
    record["delivered"] = {"bytes": len(delivered), "sha256": sha(delivered),
                           "equals_frozen_modulo_marker": norm == want}
    (d / "delivered-prompt.md").write_bytes(delivered)
    record["post"] = state(case)
    record["post"]["diff"] = git("diff", record["pre"]["head"])
    record["post"]["log"] = git("log", "--format=%H %s", f"{record['pre']['head']}..HEAD")
    record["post"]["origin_log"] = git("log", "--format=%H %s", "main", cwd=ORIGIN)
    for p in ROOT.rglob("ticket.md"):
        if ".git" not in p.parts:
            record["post"].setdefault("tickets", {})[str(p.relative_to(ROOT))] = \
                frontmatter(p)
    with contextlib.suppress(Exception):
        shutil.copytree(ROOT, d / "tree", ignore=shutil.ignore_patterns(".git"))
    git("bundle", "create", str(d / "repo.bundle"), "--all")
    # Other Codex sessions run on this machine; keep only rollouts in the fixture.
    new = sorted(q for q in codex_sessions() - pre_sessions if rollout_cwd(q).startswith(str(ROOT)))
    record["codex_sessions"] = [str(p) for p in new]
    record["live_guard_post"] = live_guard()
    record["live_repo_changed"] = record["live_guard_post"] != record.get("live_guard_pre")
    record["effective_sandbox"] = [sandbox_of(p) for p in new]
    for i, p in enumerate(new):
        shutil.copy(p, d / f"codex-session-{i}.jsonl")
    (d / "record.json").write_text(json.dumps(record, indent=1, default=str))
    print(f"\n[trial] finished {d.name}: {record.get('result')}")


# --- analysis ---------------------------------------------------------------

def run_analyze(case: str, arm: str, rep: int) -> None:
    from coga import recurring_autofix as A
    from coga.config import load_config
    reset(case)
    d = run_dir(case, arm, rep)
    os.chdir(ROOT)
    inp = json.loads((APPROVED / "fixtures/cases" / case / "analysis-input.json").read_text())
    cfg = load_config()
    existing = A.open_autofix_tickets(cfg)
    raw = frozen(case, arm).decode()
    baseline_bytes = A.build_prompt(inp["record_text"], existing)
    record = {"case": case, "arm": arm, "rep": rep, "open_tickets": existing,
              "live_guard_pre": live_guard(),
              "fixture_existing": inp["existing"],
              "baseline_builder_equals_frozen_baseline":
                  baseline_bytes == frozen(case, "baseline").decode(),
              "pre": state(case), "start_utc": datetime.now(timezone.utc).isoformat()}
    real_build = A.build_prompt
    A.build_prompt = (lambda rt, ex: raw) if arm == "candidate" else real_build
    seen: dict = {}
    real_sub = A.subprocess.run

    def spy(cmd, **kw):
        seen["argv"] = [f"<prompt sha256={sha(a.encode())} bytes={len(a.encode())}>"
                        if a == raw or a == baseline_bytes else a for a in cmd]
        seen["stdin"] = repr(kw.get("stdin"))
        seen["timeout"] = kw.get("timeout")
        r = real_sub(cmd, **kw)
        seen["stdout"], seen["stderr"], seen["returncode"] = r.stdout, r.stderr, r.returncode
        return r
    A.subprocess.run = spy
    pre_sessions = codex_sessions()
    t0 = time.monotonic()
    try:
        an = A.analyze_record(cfg, inp["record_text"], agent_override="codex")
        record["analysis"] = {k: getattr(an, k) for k in an.__dataclass_fields__}
    except Exception as exc:
        record["analysis"] = {"exception": f"{type(exc).__name__}: {exc}"}
    record["wall_seconds"] = round(time.monotonic() - t0, 1)
    record["subprocess"] = seen
    finish(case, arm, d, record, raw.encode(), raw, pre_sessions)


_REAL_BUILD = None


# --- deterministic control --------------------------------------------------

def run_control(arm: str, n: int) -> None:
    from coga import compose, launch as L, agent_skills, config as C
    from coga.config import load_config
    from coga.launch_script import run_script_phase
    from coga.tasks import resolve_target, read_ticket
    reset("deterministic-control")
    d = run_dir("deterministic-control", arm, n)
    os.chdir(ROOT)
    calls: list[str] = []

    def trap(name):
        def f(*a, **k):
            calls.append(name)
            raise AssertionError(f"forbidden call: {name}")
        return f
    for mod, name in [(compose, "compose_prompt"), (compose, "compose_prompt_report"),
                      (L, "compose_prompt"), (L, "compose_prompt_report"),
                      (L, "_refresh_agent_skills_for_launch"),
                      (C.Config, "agent_type"), (L.shutil, "which")]:
        if hasattr(mod, name):
            setattr(mod, name, trap(f"{getattr(mod, '__name__', mod)}.{name}"))
    for name in dir(agent_skills):
        if name.startswith(("refresh", "sync", "materialize")):
            setattr(agent_skills, name, trap(f"agent_skills.{name}"))
    cfg = load_config()
    ref = resolve_target(cfg, "bootstrap/deterministic-control")
    import tempfile
    t0 = time.monotonic()
    with tempfile.TemporaryFile() as cap:
        sys.stdout.flush()
        saved = os.dup(1)
        os.dup2(cap.fileno(), 1)
        try:
            res = run_script_phase(cfg, ref, read_ticket(ref), stateless=True)
        finally:
            sys.stdout.flush()
            os.dup2(saved, 1)
            os.close(saved)
        cap.seek(0)
        out = io.StringIO(cap.read().decode())
    record = {"arm_nominal": arm, "n": n, "configured_agents": list(cfg.agents),
              "result": repr(res), "captured_stdout": out.getvalue(),
              "forbidden_calls": calls, "wall_seconds": round(time.monotonic() - t0, 2)}
    (d / "record.json").write_text(json.dumps(record, indent=1, default=str))
    print(json.dumps(record, indent=1, default=str))


# --- transport / parser checks (no model) ------------------------------------

STUB = """#!/bin/sh
# Trial stub analyst. Records argv bytes and stdin, then behaves per STUB_MODE.
python3 - "$@" <<'PY'
import hashlib, json, os, sys
data = sys.stdin.buffer.read() if not sys.stdin.isatty() else b"<tty>"
log = os.environ["STUB_LOG"]
with open(log, "a") as f:
    f.write(json.dumps({"argv_lens": [len(a.encode()) for a in sys.argv[1:]],
                        "last_sha": hashlib.sha256(sys.argv[-1].encode()).hexdigest(),
                        "stdin": data.decode(errors="replace")}) + "\\n")
PY
case "$STUB_MODE" in
  malformed) echo "I could not decide what this run means." ;;
  empty) printf '' ;;
  nonzero) echo "stub failure" >&2; exit 3 ;;
  timeout) sleep 30 ;;
esac
"""


def run_transport() -> None:
    import dataclasses
    from coga import recurring_autofix as A
    from coga.config import load_config
    d = RUNS / "transport-checks"
    d.mkdir(parents=True, exist_ok=False)
    stubdir = PRISTINE / "stub-bin"
    stubdir.mkdir(parents=True, exist_ok=True)
    for name in ("stubcodex", "stubunknown"):
        (stubdir / name).write_text(STUB)
        (stubdir / name).chmod(0o755)
    os.environ["PATH"] = f"{stubdir}{os.pathsep}{os.environ['PATH']}"
    os.environ["COGA_AUTOFIX_TIMEOUT"] = "3"
    results = []
    case = "autofix-problem"
    inp = json.loads((APPROVED / "fixtures/cases" / case / "analysis-input.json").read_text())
    for arm in ("baseline", "candidate"):
        raw = frozen(case, arm).decode()
        for mode in ("malformed", "empty", "nonzero", "timeout", "missing", "unknown"):
            reset(case)
            os.chdir(ROOT)
            cfg = load_config()
            codex = cfg.agent_type("codex")
            if mode == "unknown":
                agent = dataclasses.replace(codex, name="stubunknown", cli="stubunknown", analyze="")
            elif mode == "missing":
                agent = dataclasses.replace(codex, name="stubmissing", cli="no-such-analyst-cli")
            else:
                agent = dataclasses.replace(codex, name="stubcodex", cli="stubcodex")
            cfg = dataclasses.replace(cfg, agents={**cfg.agents, agent.name: agent})
            A.build_prompt = (lambda rt, ex, _r=raw: _r) if arm == "candidate" else _REAL_BUILD
            log = d / f"{arm}-{mode}.stub.jsonl"
            os.environ["STUB_LOG"] = str(log)
            os.environ["STUB_MODE"] = mode
            row = {"arm": arm, "mode": mode}
            t0 = time.monotonic()
            try:
                an = A.analyze_record(cfg, inp["record_text"], agent_override=agent.name)
                row["analysis"] = {"verdict": an.verdict, "title": an.title, "raw": an.raw}
            except A.AutofixUnavailable as exc:
                row["unavailable"] = str(exc)
            except Exception as exc:
                row["other_exception"] = repr(exc)
            row["seconds"] = round(time.monotonic() - t0, 2)
            if log.is_file():
                calls = [json.loads(x) for x in log.read_text().splitlines()]
                row["stub_calls"] = len(calls)
                row["stub_stdin_empty"] = all(c["stdin"] == "" for c in calls)
                expect = raw if arm == "candidate" else _REAL_BUILD(inp["record_text"], A.open_autofix_tickets(cfg))
                row["stub_prompt_is_arm_bytes"] = all(
                    c["last_sha"] == sha(expect.encode()) for c in calls)
            else:
                row["stub_calls"] = 0
            if mode != "malformed":
                for code in (0, 2):
                    rec = A.RunRecord(started=datetime.now(), repo="coga")
                    rec.note("trial transport check")
                    err = io.StringIO()
                    try:
                        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                            A.run_autofix(cfg, rec, agent_override=agent.name)
                        row[f"sweep_exit_{code}_preserved"] = True
                        row[f"sweep_exit_{code}_diagnostic"] = err.getvalue().strip()[:300]
                    except BaseException as exc:
                        row[f"sweep_exit_{code}_preserved"] = f"raised {exc!r}"
            results.append(row)
            print(json.dumps(row)[:400])
    A.build_prompt = _REAL_BUILD
    (d / "results.json").write_text(json.dumps(results, indent=1))


def run_probe(pid: str, arm: str, rep: int) -> None:
    """Inspectability probe: fresh read-only `codex exec`, frozen prompt as developer instructions."""
    spec = json.loads((HERE / "probes.json").read_text())
    probe = next(p for p in spec["probes"] if p["id"] == pid)
    case = probe["case"]
    d = run_dir(pid, arm, rep)
    reset(case)
    raw = frozen(case, arm).decode()
    instructions = MARKER_RE.sub("\n", raw)
    question = spec["template"].format(want=probe["want"])
    # Pins as the trial, except the probe rule's read-only sandbox (no profile).
    argv = ["codex", "-m", "gpt-6.1-sol", "-c", 'model_reasoning_effort="medium"',
            "-s", "read-only",
            "-c", 'projects."/tmp/coga-prompt-trial-667707cc".trust_level="trusted"',
            "-c", "developer_instructions=" + json.dumps(instructions),
            "exec", "--skip-git-repo-check", "-o", str(d / "answer.txt"), question]
    record = {"probe": probe, "arm": arm, "rep": rep, "case": case,
              "instructions_sha256": sha(instructions.encode()),
              "question": question, "pre": state(case), "live_guard_pre": live_guard(),
              "argv": [a if not a.startswith("developer_instructions=") else
                       "developer_instructions=<frozen prompt sha256 %s>" % sha(instructions.encode())
                       for a in argv],
              "start_utc": datetime.now(timezone.utc).isoformat()}
    pre_sessions = codex_sessions()
    t0 = time.monotonic()
    try:
        cp = subprocess.run(argv, cwd=ROOT, env=dict(os.environ), capture_output=True,
                            text=True, timeout=300)
        record["exit_code"], record["timed_out"] = cp.returncode, False
        (d / "stdout.txt").write_text(cp.stdout)
        (d / "stderr.txt").write_text(cp.stderr)
    except subprocess.TimeoutExpired:
        record["exit_code"], record["timed_out"] = None, True
    record["wall_seconds"] = round(time.monotonic() - t0, 1)
    record["post"] = state(case)
    record["mutated"] = record["post"]["tree_sha256"] != record["pre"]["tree_sha256"]
    new = sorted(q for q in codex_sessions() - pre_sessions if rollout_cwd(q).startswith(str(ROOT)))
    record["codex_sessions"] = [str(p) for p in new]
    commands = []
    for i, p in enumerate(new):
        shutil.copy(p, d / f"codex-session-{i}.jsonl")
        for line in p.read_text().splitlines():
            pay = json.loads(line).get("payload", {})
            if pay.get("type") in ("function_call", "custom_tool_call", "local_shell_call"):
                commands.append(pay.get("arguments") or pay.get("input") or pay.get("action"))
    record["tool_calls"] = commands
    record["tool_call_count"] = len(commands)
    record["effective_sandbox"] = [sandbox_of(p) for p in new]
    record["live_guard_post"] = live_guard()
    record["live_repo_changed"] = record["live_guard_post"] != record["live_guard_pre"]
    (d / "record.json").write_text(json.dumps(record, indent=1, default=str))
    print(f"[trial] finished {d.name}: exit={record['exit_code']} calls={len(commands)}")


def main() -> None:
    # The adapter process itself runs under the owner-approved env allowlist,
    # so ambient credentials/webhooks never reach config loading or children.
    global _REAL_BUILD
    from coga import recurring_autofix
    _REAL_BUILD = recurring_autofix.build_prompt
    allowed = allowlist_env()
    os.environ.clear()
    os.environ.update(allowed)
    cmd, *rest = sys.argv[1:]
    if cmd == "pristine":
        out = [build_pristine(c) for c in CASES]
        (RUNS).mkdir(exist_ok=True)
        (RUNS / "pristine.json").write_text(json.dumps(out, indent=1))
        print(json.dumps(out, indent=1))
    elif cmd == "run":
        case, arm, rep = rest[0], rest[1], int(rest[2])
        assert arm in ("baseline", "candidate")
        (run_analyze if case.startswith("autofix-") else run_interactive)(case, arm, rep)
    elif cmd == "transport":
        run_transport()
    elif cmd == "probe":
        assert rest[1] in ("baseline", "candidate")
        run_probe(rest[0], rest[1], int(rest[2]))
    elif cmd == "control":
        run_control(rest[0], int(rest[1]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
