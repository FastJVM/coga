"""Disposable trial adapter for ticket 04 (evidence, not product code).

Adapted from ticket 02's adapter. Runs the *real* launch path (`launch._launch`
with megalaunch conduct, or `commands.ticket.ticket` for guided authoring) in a
snapshot fixture of this repo, and substitutes the frozen arm prompt at the one
seam both use: `spawn_agent_session(composed_prompt=...)`. Before substituting,
it asserts that the prompt production would have delivered equals the frozen
baseline byte for byte, so the baseline arm is production and the candidate arm
is exactly the frozen C1' text.

Run only with the pinned venv's Python (non-editable Coga at PIN).

  adapter.py pristine               build per-case pristine fixture snapshots
  adapter.py render <case>          compose the baseline via the real path, freeze baseline + C1'
  adapter.py run <case> <arm> <rep> one session (needs a TTY: use ctl.sh)
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
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = Path("/home/n/Code/coga")
PIN = "abbe9ece3cf24acdc24fd89376f9636faf83f40f"
ROOT = Path("/tmp/coga-quality-trial")
ORIGIN = Path("/tmp/coga-quality-trial-origin.git")
PRISTINE = Path("/tmp/coga-quality-trial-pristine")
BIN = Path("/tmp/coga-quality-trial-bin")
CODEX_EXE = Path("/home/n/.codex/packages/standalone/releases/"
                 "0.167.2-x86_64-unknown-linux-musl/bin/codex")
CODEX_SHA = "a9672d0fa0dd8fcf8cad136fa0d056b914bc046f5ac3d78f4a5cf390655af56b"
PROMPTS = HERE / "prompts"
RUNS = HERE / "runs"
MAX_SESSION = 1800.0
STRIPPED = "coga/tasks/v1/microkernel/03-prompt-assembly"  # trial packages: never in the fixture
FIXED = {
    "GIT_AUTHOR_NAME": "Trial Fixture", "GIT_AUTHOR_EMAIL": "trial@example.invalid",
    "GIT_COMMITTER_NAME": "Trial Fixture", "GIT_COMMITTER_EMAIL": "trial@example.invalid",
    "GIT_AUTHOR_DATE": "2026-11-14T00:00:00Z", "GIT_COMMITTER_DATE": "2026-11-14T00:00:00Z",
}
# Ticket 02's pins (model, effort, D2 trust, D4 permission profile), re-rooted.
PINS = ('-m gpt-6.1-sol -c model_reasoning_effort="medium" -a never '
        "-c 'permissions.trial.filesystem={\":root\"=\"read\",\":slash_tmp\"=\"write\","
        f"\"{ROOT}/.git\"=\"write\"}}' "
        "-c permissions.trial.network.enabled=true "
        "-c 'default_permissions=\"trial\"' "
        f"-c 'projects.\"{ROOT}\".trust_level=\"trusted\"'")


def _toml_str(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


AGENTS = f'''
[agents.codex]
cli = "codex"
file = "AGENTS.md"
mode = "local"
peer = "claude"
launch_args = "--no-daemon {_toml_str(PINS)}"
discussion = "-c developer_instructions={{prompt}}"

# Trial: the peer exists only so `other-agent` resolves; its CLI is absent, so
# the launch supervisor stops after the one measured step instead of chaining.
[agents.claude]
cli = "claude-absent-in-trial"
file = "CLAUDE.md"
mode = "local"

[telemetry]
enabled = false
'''

CASES = {
    "code": {"op": "execute", "workflow": "code/with-review",
             "src": "coga/tasks/_v2/fail-validation-when-local-user-is-required-for-ex.md",
             "slug": "fail-validation-when-local-user-is-required-for-ex"},
    "design": {"op": "execute", "workflow": "code/design-then-implement",
               "src": "coga/tasks/warn-when-coga-delete-or-coga-retire-leaves-a-live.md",
               "slug": "warn-when-coga-delete-or-coga-retire-leaves-a-live"},
    "docs": {"op": "execute", "workflow": "docs/with-review",
             "src": "coga/tasks/_v2/document-untrusted-tool-output-verify-through-grou.md",
             "slug": "document-untrusted-tool-output-verify-through-grou"},
    "author": {"op": "author", "title": "Flag stalled in-progress tickets in coga status"},
}
ENV_KEYS = {"HOME", "USER", "LOGNAME", "TERM", "LANG", "SHELL", "TMPDIR", "COLORTERM"}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(*args: str, cwd: Path = ROOT, env: dict | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True, env={**os.environ, **(env or {})}).stdout


def allowlist_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in ENV_KEYS or k.startswith("LC_")}
    env["PATH"] = os.pathsep.join([str(BIN), str(Path(sys.executable).parent),
                                   str(Path.home() / ".local/bin"),
                                   "/usr/local/bin", "/usr/bin", "/bin"])
    return env


def enter_env() -> None:
    """The adapter itself runs under the allowlist (ticket 02 D3)."""
    env = allowlist_env()
    os.environ.clear()
    os.environ.update(env)


# --- fixtures ---------------------------------------------------------------

def _frontmatter_split(text: str) -> tuple[str, str]:
    assert text.startswith("---\n")
    end = text.index("\n---\n", 4)
    return text[4:end], text[end + 5:]


def _prepare_case_ticket(case: str) -> str:
    spec = CASES[case]
    src = ROOT / spec["src"]
    import yaml
    fm_text, body = _frontmatter_split(src.read_text())
    fm = yaml.safe_load(fm_text)
    new_fm = (f"title: {fm['title']}\nstatus: draft\nowner: {fm['owner']}\n"
              f"agent: codex\nworkflow: {spec['workflow']}\n")
    dst = ROOT / "coga/tasks" / f"{spec['slug']}.md"
    src.unlink()
    dst.write_text(f"---\n{new_fm}---\n{body}")
    return spec["slug"]


def build_pristine(case: str) -> dict:
    for p in (ROOT, ORIGIN):
        if p.exists():
            shutil.rmtree(p)
    ROOT.mkdir(parents=True)
    archive = subprocess.run(["git", "archive", PIN], cwd=LIVE, check=True,
                             capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(ROOT, filter="tar")
    shutil.rmtree(ROOT / STRIPPED)
    cfg = ROOT / "coga/coga.toml"
    text = cfg.read_text()
    # Replace the repo's agent tables with the pinned trial agents.
    text = re.sub(r"\n\[agents\.claude\]\n(?:(?!\n\[).)*", "\n", text, flags=re.S)
    text = re.sub(r"\n\[agents\.codex\]\n(?:(?!\n\[).)*", "\n", text, flags=re.S)
    text = re.sub(r"\n\[telemetry\]\n(?:(?!\n\[).)*", "\n", text, flags=re.S)
    cfg.write_text(text.rstrip("\n") + "\n" + AGENTS)
    (ROOT / "coga/coga.local.toml").write_text(
        'user = "trial-owner"\n\n[notification.slack]\nenabled = false\n')
    git("init", "-q", "-b", "main")
    git("add", "-A")
    # Track exactly PIN's tracked set: some tracked files (skills/_template)
    # match ignore rules and are force-added upstream.
    tracked = subprocess.run(["git", "ls-tree", "-r", "-z", "--name-only", PIN], cwd=LIVE,
                             check=True, capture_output=True, text=True).stdout.split("\0")
    tracked = [t for t in tracked if t and not t.startswith(STRIPPED + "/")]
    for i in range(0, len(tracked), 500):
        git("add", "-f", "--", *tracked[i:i + 500])
    have = set(git("ls-files", "-z").split("\0")) - {""}
    assert have == set(tracked), sorted(have ^ set(tracked))[:10]
    git("commit", "-q", "-m", f"Trial fixture snapshot of {PIN[:9]} (03-prompt-assembly stripped)", env=FIXED)
    base = git("rev-parse", "HEAD").strip()
    slug = None
    if CASES[case]["op"] == "execute":
        slug = _prepare_case_ticket(case)
        git("add", "-A")
        git("commit", "-q", "-m", f"Trial fixture: {case}", env=FIXED)
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(ORIGIN)], check=True)
    git("remote", "add", "origin", str(ORIGIN))
    git("push", "-q", "origin", "main")
    git("fetch", "-q", "origin")
    git("branch", "-q", "--set-upstream-to=origin/main", "main")
    if slug:
        out = subprocess.run([str(Path(sys.executable).parent / "coga"), "mark", "active", slug],
                             cwd=ROOT, capture_output=True, text=True, env=allowlist_env())
        if out.returncode:
            raise SystemExit(f"mark active failed: {out.stdout}{out.stderr}")
    status = git("status", "--porcelain", "--untracked-files=all")
    PRISTINE.mkdir(parents=True, exist_ok=True)
    with tarfile.open(PRISTINE / f"{case}.tar", "w") as tar:
        tar.add(ROOT, arcname="root")
        tar.add(ORIGIN, arcname="origin")
    return {"case": case, "snapshot_commit": base, "head": git("rev-parse", "HEAD").strip(),
            "status_after_activation": status,
            "config_sha256": sha(cfg.read_bytes())}


def reset(case: str) -> None:
    for p in (ROOT, ORIGIN):
        if p.exists():
            shutil.rmtree(p)
    with tarfile.open(PRISTINE / f"{case}.tar") as tar:
        for m in tar.getmembers():
            dest = ROOT if m.name.split("/")[0] == "root" else ORIGIN
            m.name = "/".join(m.name.split("/")[1:]) or "."
            tar.extract(m, dest, filter="tar")


def ensure_bin() -> None:
    assert sha(CODEX_EXE.read_bytes()) == CODEX_SHA, "pinned codex binary changed"
    BIN.mkdir(exist_ok=True)
    link = BIN / "codex"
    if not link.is_symlink():
        link.symlink_to(CODEX_EXE)


# --- prompt substitution ------------------------------------------------------

class Captured(Exception):
    pass


def _compose_like_spawn(L, cfg, ref, ticket, kw) -> str:
    if kw.get("composed_prompt") is not None:
        return kw["composed_prompt"]
    return L.compose_prompt(cfg, ref, ticket,
                            include_blocker_preamble=kw.get("include_blocker_preamble", True),
                            launch_context=kw.get("launch_context", "attended"),
                            checkout=kw.get("checkout_notice"))


def _drive(case: str, spawn_hook) -> None:
    """Run the real entry point for `case` with spawn_agent_session hooked."""
    from coga import launch as L
    from coga.commands import ticket as T
    real = L.spawn_agent_session

    def hooked(cfg, ref, ticket, agent, **kw):
        return spawn_hook(real, L, cfg, ref, ticket, agent, kw)

    L.spawn_agent_session = hooked
    T.spawn_agent_session = hooked
    os.chdir(ROOT)
    if CASES[case]["op"] == "author":
        T.ticket(target=CASES[case]["title"], agent_override="codex", pick_agent=False)
    else:
        L._launch(CASES[case]["slug"], args=None, agent_override=None, prompt_report=False,
                  idle_timeout=None, max_session=MAX_SESSION, return_timeout=False,
                  launch_context="megalaunch", before_recompose=None,
                  before_final_spawn=None, require_agent_target=False,
                  record_launch=True, recurring_authorized=False,
                  script_failure_important=False)


def _facts(case: str, kw: dict, prompt: str, ref) -> dict:
    author = CASES[case]["op"] == "author"
    checkout = None
    if not author:
        notice = [l for l in prompt.split("\n\n---\n\n") if l.startswith("## Checkout (runtime)")]
        para = notice[0].split("\n\n")[1].strip() if notice else ""
        # Ticket 02 convention: no preparation supplied -> checkout null.
        if para and not para.startswith("No checkout preparation was supplied"):
            checkout = {"summary": para,
                        "return_owner": "The launcher returns this checkout after the session; "
                                        "do not return it yourself."}
    return {
        "operation": "author" if author else "execute",
        "execution_kind": "agent",
        "target_kind": "task",
        "target": ref.id_slug,
        "launch_context": kw.get("launch_context", "attended"),
        "include_blocker_preamble": kw.get("include_blocker_preamble", True),
        "completion": "authoring return" if author else "one workflow transition or terminal block",
        "owner_assist": False,
        "checkout": checkout,
        "script_result": None,
        "kickoff": "Begin (new ticket)" if author else None,
        "discussion": bool(kw.get("discussion", False)),
        "launch_arguments": [],
        "fixture_ticket": str(ref.ticket_path.relative_to(ROOT)),
        "transport": ("discussion template + separate kickoff, PTY" if author
                      else "interactive argv, PTY"),
        "invocation_source": ("commands.ticket._run_authoring_session" if author
                              else "launch._launch (megalaunch conduct)"),
    }


def _position(ticket) -> dict | None:
    wf = getattr(ticket, "workflow", None)
    step = getattr(ticket, "step", None)
    if not isinstance(wf, dict) or not step:
        return None
    n = int(str(step).split()[0])
    s = wf["steps"][n - 1]
    return {"position": str(step), "name": s.get("name"), "assignee": s.get("assignee"),
            "requires": s.get("requires"), "skills": s.get("skills") or []}


def render(case: str) -> None:
    sys.path.insert(0, str(HERE))
    import c1prime
    enter_env()
    ensure_bin()
    reset(case)
    out = PROMPTS / case
    if out.exists():
        raise SystemExit(f"{out} exists; frozen prompts are never overwritten")

    def hook(real, L, cfg, ref, ticket, agent, kw):
        base = _compose_like_spawn(L, cfg, ref, ticket, kw)
        facts = _facts(case, kw, base, ref)
        pos = _position(ticket)
        cand = c1prime.build(base, facts, author=facts["operation"] == "author",
                             position=pos, prime=True)
        out.mkdir(parents=True)
        (out / "baseline.md").write_text(base)
        (out / "candidate.md").write_text(cand)
        (out / "facts.json").write_text(json.dumps(facts, indent=2) + "\n")
        (out / "position.json").write_text(json.dumps(pos, indent=2) + "\n")
        (out / "spawn-kwargs.json").write_text(json.dumps(
            {k: v for k, v in kw.items() if k not in ("env", "composed_prompt")},
            indent=1, default=repr) + "\n")
        raise Captured()

    try:
        _drive(case, hook)
    except Captured:
        print(f"[render] froze {out}")
        return
    except SystemExit as exc:
        if (out / "baseline.md").exists():
            print(f"[render] froze {out} (launch exit {exc.code})")
            return
        raise
    raise SystemExit("render: spawn was never reached")


# --- evidence ---------------------------------------------------------------

def live_guard() -> dict:
    own = str(HERE.relative_to(LIVE))
    status = [l for l in git("status", "--porcelain", "--untracked-files=all", cwd=LIVE).splitlines()
              if own not in l]
    return {"head": git("rev-parse", "HEAD", cwd=LIVE).strip(), "status": status}


def venv_guard() -> str:
    site = Path(sys.executable).parent.parent / "lib"
    h = hashlib.sha256()
    for p in sorted(site.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(str(p.relative_to(site)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def codex_sessions() -> set[Path]:
    base = Path.home() / ".codex/sessions"
    return set(base.rglob("*.jsonl")) if base.is_dir() else set()


def rollout_cwd(rollout: Path) -> str:
    with contextlib.suppress(Exception):
        with rollout.open() as fh:
            return json.loads(fh.readline()).get("payload", {}).get("cwd", "")
    return ""


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


def tokens_of(rollout: Path) -> dict | None:
    last = None
    for line in rollout.read_text().splitlines():
        if '"token_count"' in line:
            with contextlib.suppress(Exception):
                info = json.loads(line)["payload"].get("info") or {}
                last = info.get("total_token_usage") or last
    return last


def snapshot(base: str) -> dict:
    return {
        "head": git("rev-parse", "HEAD").strip(),
        "branch": git("branch", "--show-current").strip(),
        "status": git("status", "--porcelain", "--untracked-files=all"),
        "local_refs": git("for-each-ref", "--format=%(refname) %(objectname)"),
        "origin_refs": git("for-each-ref", "--format=%(refname) %(objectname)", cwd=ORIGIN),
        "log_all": git("log", "--all", "--format=%H %D %s", f"^{base}"),
    }


def run(case: str, arm: str, rep: int) -> None:
    enter_env()
    ensure_bin()
    d = RUNS / f"{case}__{arm}__r{rep}"
    if d.exists():
        raise SystemExit(f"{d} exists; runs are never overwritten")
    d.mkdir(parents=True)
    frozen_base = (PROMPTS / case / "baseline.md").read_text()
    frozen_arm = (PROMPTS / case / f"{arm}.md").read_text()
    reset(case)
    base = git("rev-parse", "HEAD").strip()
    record: dict = {"case": case, "arm": arm, "rep": rep, "pin": PIN, "fixture_head": base,
                    "start_utc": datetime.now(timezone.utc).isoformat(),
                    "frozen_sha256": sha(frozen_arm.encode()),
                    "live_guard_pre": live_guard(), "venv_pre": venv_guard(),
                    "pre": snapshot(base)}
    pre_sessions = codex_sessions()
    delivered: dict = {}

    def hook(real, L, cfg, ref, ticket, agent, kw):
        live = _compose_like_spawn(L, cfg, ref, ticket, kw)
        record["production_equals_frozen_baseline"] = live == frozen_base
        if live != frozen_base:
            (d / "production-prompt.md").write_text(live)
            raise SystemExit("production prompt drifted from the frozen baseline; run aborted")
        record["target"] = ref.id_slug
        record["spawn_kwargs"] = {k: v for k, v in kw.items()
                                  if k not in ("env", "composed_prompt")}
        kw = {**kw, "composed_prompt": frozen_arm}
        real_write = L.write_prompt_file

        def capture(prompt, ref_):
            delivered["text"] = prompt
            return real_write(prompt, ref_)
        L.write_prompt_file = capture
        try:
            return real(cfg, ref, ticket, agent, **kw)
        finally:
            L.write_prompt_file = real_write

    (d / "record.json").write_text(json.dumps(record, indent=1, default=str))
    t0 = time.monotonic()
    try:
        _drive(case, hook)
        record["result"] = "returned"
    except SystemExit as exc:
        record["result"] = f"exit {exc.code}"
    except BaseException as exc:  # record, never hide
        record["result"] = f"exception {exc!r}"
    record["wall_seconds"] = round(time.monotonic() - t0, 1)
    record["end_utc"] = datetime.now(timezone.utc).isoformat()
    finish(d, record, base, delivered.get("text", ""), frozen_arm, pre_sessions)


def finish(d: Path, record: dict, base: str, delivered: str, frozen: str, pre_sessions) -> None:
    os.chdir(ROOT)
    norm = re.sub(r"\n\ncoga-launch: [0-9a-f-]{36}\n\Z", "", delivered)
    record["delivered"] = {"bytes": len(delivered.encode()), "sha256": sha(delivered.encode()),
                           "equals_frozen_modulo_marker": norm == frozen.rstrip("\n")}
    (d / "delivered-prompt.md").write_text(delivered)
    record["post"] = snapshot(base)
    git("bundle", "create", str(d / "repo.bundle"), "--all", f"^{base}")
    new = sorted(q for q in codex_sessions() - pre_sessions if rollout_cwd(q).startswith(str(ROOT)))
    record["codex_sessions"] = [str(p) for p in new]
    record["effective_sandbox"] = [sandbox_of(p) for p in new]
    record["tokens"] = [tokens_of(p) for p in new]
    for i, p in enumerate(new):
        shutil.copy(p, d / f"codex-session-{i}.jsonl")
    record["live_guard_post"] = live_guard()
    record["live_repo_changed"] = record["live_guard_post"] != record["live_guard_pre"]
    record["venv_post"] = venv_guard()
    record["venv_changed"] = record["venv_post"] != record["venv_pre"]
    (d / "record.json").write_text(json.dumps(record, indent=1, default=str))
    print(f"\n[trial] finished {d.name}: {record['result']} in {record['wall_seconds']}s")


def main() -> None:
    cmd = sys.argv[1:2]
    if cmd == ["pristine"]:
        enter_env()
        ensure_bin()
        info = [build_pristine(c) for c in CASES]
        (HERE / "pristine.json").write_text(json.dumps(info, indent=1) + "\n")
        print(json.dumps(info, indent=1))
    elif cmd == ["render"]:
        render(sys.argv[2])
    elif cmd == ["run"]:
        run(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
