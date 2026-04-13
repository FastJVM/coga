"""relay launch — compose prompt, inject secrets, spawn agent (or run script)."""
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ..config import Config
from ..logfile import append as log_append
from ..slack import post as slack_post
from ..tasks import find_task
from ..ticket import parse_step_field


def register(sub):
    p = sub.add_parser(
        "launch",
        help="Compose prompt and start work on a task (or run script)",
    )
    p.add_argument("--task", required=True)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Compose the prompt and print a summary, but do not spawn the "
        "agent or run the script. Useful for inspecting exactly what the "
        "agent would receive before committing to a real launch.",
    )
    p.set_defaults(func=run)


# ------------- helpers -------------


def _read(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def _read_body_section(body: str, heading: str) -> str:
    """Extract a markdown h2 section by heading, up to the next h2 or EOF."""
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(body)
    return m.group(1).strip() if m else ""


def _load_skill(cfg: Config, ref: str) -> str:
    path = cfg.root / "skills" / ref / "SKILL.md"
    if not path.exists():
        raise SystemExit(
            f"error: skill not found: {ref} (looked for {path})"
        )
    return path.read_text()


def _load_context(cfg: Config, ref: str) -> str:
    path = cfg.root / "contexts" / ref / "SKILL.md"
    if not path.exists():
        raise SystemExit(
            f"error: context not found: {ref} (looked for {path})"
        )
    return path.read_text()


def _compose_prompt(cfg: Config, ticket, project: str, mode: str) -> str:
    parts: list[str] = []

    # 1. Protocol (how to operate within Relay)
    parts.append(_read(cfg.root / "protocol.md"))

    # 2. Mode-specific behavioral block
    mode_file = cfg.root / f"protocol-{mode}.md"
    if mode_file.exists():
        parts.append(_read(mode_file))

    # 3. Global rules
    parts.append(_read(cfg.root / "rules.md"))

    # 4. Project base context
    proj_path = cfg.project_path(project)
    if proj_path:
        parts.append(_read(proj_path / ".relay" / "context.md"))

    # 5. Task contexts (domain knowledge attached to this ticket)
    for ref in ticket.contexts or []:
        parts.append(f"# Context: {ref}\n\n" + _load_context(cfg, ref))

    # 6. Inline task-specific context from the ticket body
    inline = _read_body_section(ticket.body, "Context")
    if inline:
        parts.append("# Task-specific context\n\n" + inline)

    # 7. Current workflow step — load skill if referenced, else inline
    wf = ticket.workflow
    if wf and wf.get("steps") and ticket.step:
        n, _name = parse_step_field(ticket.step)
        if n and 1 <= n <= len(wf["steps"]):
            step_def = wf["steps"][n - 1]
            skill_ref = step_def.get("skill")
            if skill_ref:
                parts.append(
                    f"# Current step: {step_def['name']}\n\n"
                    + _load_skill(cfg, skill_ref)
                )
            else:
                parts.append(
                    f"# Current step: {step_def['name']}\n\n"
                    f"(no skill — follow the inline workflow instructions)"
                )

    # 8. Blackboard (live state — decisions and findings from prior runs)
    parts.append(
        "# Blackboard (live state)\n\n"
        + _read(ticket.dir / "blackboard.md")
    )

    return "\n\n---\n\n".join(p for p in parts if p.strip())


def _launch_env(cfg: Config) -> dict:
    env = os.environ.copy()
    env.update(cfg.secrets_env())
    return env


def _resolve_script(cfg: Config, ticket):
    wf = ticket.workflow
    if not wf or not wf.get("steps"):
        raise SystemExit("error: script mode requires a workflow")
    n, _ = parse_step_field(ticket.step)
    if not n:
        raise SystemExit(f"error: invalid step field: {ticket.step!r}")
    step_def = wf["steps"][n - 1]
    skill_ref = step_def.get("skill")
    if not skill_ref:
        raise SystemExit(
            f"error: step '{step_def['name']}' has no skill — cannot run in "
            f"script mode"
        )
    skill_dir = cfg.root / "skills" / skill_ref
    for name in ("run.sh", "run.py"):
        cand = skill_dir / name
        if cand.exists():
            return skill_ref, cand
    raise SystemExit(f"error: no run.sh or run.py found in {skill_dir}")


def _run_script_mode(cfg: Config, ticket, project: str, dry_run: bool) -> int:
    skill_ref, script = _resolve_script(cfg, ticket)
    actor = cfg.user or "unknown"

    if dry_run:
        print(f"[dry-run] script mode")
        print(f"[dry-run] would exec: {script}")
        print(f"[dry-run] secrets env vars: {sorted(cfg.secrets_env().keys())}")
        print(f"[dry-run] no log entry written, no Slack post, no subprocess spawned")
        return 0

    log_append(
        ticket.dir,
        actor=f"cli:{actor}",
        message=f"launched in script mode: {skill_ref}/{script.name}",
    )
    slack_post(
        f"{project} {ticket.id}: running {skill_ref}/{script.name} (script mode)"
    )

    env = _launch_env(cfg)
    print(f"exec {script}")
    try:
        result = subprocess.run([str(script)], env=env)
    except FileNotFoundError as e:
        raise SystemExit(f"error: failed to exec {script}: {e}")
    if result.returncode != 0:
        log_append(
            ticket.dir,
            actor=f"cli:{actor}",
            message=f"script exited {result.returncode}",
        )
        slack_post(
            f'{project} {ticket.id} "{ticket.title}" — script exited '
            f"{result.returncode}"
        )
    return result.returncode


def run(args):
    cfg = Config()
    ticket, project = find_task(cfg, args.task)

    if ticket.status != "active" and not args.dry_run:
        raise SystemExit(
            f"error: task {ticket.id} is '{ticket.status}', not active. "
            f"Set status to 'active' before launching, or use --dry-run "
            f"to preview without launching."
        )

    mode = ticket.mode or "interactive"

    if mode == "script":
        return _run_script_mode(cfg, ticket, project, args.dry_run)

    if mode not in ("interactive", "auto"):
        raise SystemExit(f"error: unknown mode: {mode!r}")

    assignee = ticket.assignee
    if not assignee:
        raise SystemExit(
            f"error: task {ticket.id} has no assignee — cannot resolve agent"
        )
    agent = cfg.resolve_assignee(assignee)
    if not agent:
        raise SystemExit(
            f"error: task {ticket.id} is assigned to '{assignee}', which is "
            f"not an agent nickname for user '{cfg.user}'. Edit relay.toml "
            f"[assignees.{cfg.user}] agents to add it, or reassign the task."
        )

    prompt = _compose_prompt(cfg, ticket, project, mode)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    tmp = Path(tempfile.gettempdir()) / f"relay-{ticket.id}-{ts}.md"
    tmp.write_text(prompt)

    cli = agent["cli"]
    actor = cfg.user or "unknown"

    if args.dry_run:
        flag_i = agent.get("interactive", "?")
        flag_a = agent.get("auto", "?")
        print(f"[dry-run] mode: {mode}")
        print(f"[dry-run] assignee: {assignee} -> agent type cli={cli}")
        print(f"[dry-run] prompt file: {tmp}")
        print(f"[dry-run] prompt length: {len(prompt)} chars, "
              f"{prompt.count(chr(10)) + 1} lines")
        if mode == "interactive":
            print(f"[dry-run] would exec: {cli} {flag_i} {tmp}")
        else:
            preview = prompt[:200].replace("\n", " ")
            print(f"[dry-run] would exec: {cli} {flag_a} <prompt>  "
                  f"(preview: {preview!r}...)")
        print(f"[dry-run] secrets env vars: {sorted(cfg.secrets_env().keys())}")
        print(f"[dry-run] no log entry written, no Slack post, no subprocess spawned")
        print(f"[dry-run] inspect the prompt: cat {tmp}")
        return 0

    log_append(
        ticket.dir,
        actor=f"cli:{actor}",
        message=f"launched in {mode} mode ({cli}, assignee {assignee})",
    )
    slack_post(
        f"{actor}'s {assignee} started work on {project} {ticket.id} "
        f'"{ticket.title}" ({mode})'
    )

    if mode == "interactive":
        flag = agent["interactive"]
        # Spec: interactive flag receives the path to the composed prompt file.
        cmd = [cli, flag, str(tmp)]
    else:
        flag = agent["auto"]
        # Spec: auto flag receives the prompt content itself as a single arg.
        cmd = [cli, flag, prompt]

    env = _launch_env(cfg)
    print(f"launching: {cli} {flag} <prompt> (prompt file: {tmp})")
    try:
        result = subprocess.run(cmd, env=env)
    except FileNotFoundError:
        raise SystemExit(f"error: '{cli}' not found in PATH")
    return result.returncode
