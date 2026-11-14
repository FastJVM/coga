"""Disposable: build ticket 04's blinded pair pack and sealed gate checks.

Usage: python blind.py <seed>
  blind/<pair>/{X,Y}/artifact.md   what the owner judges (artifact only)
  blind/verdicts.csv               owner fills: better = X | Y | tie, plus reason
  blind-key.json                   pair/label -> arm (sealed until verdicts are in)
  gates.json                       mechanical gate checks per run, arm-labeled (sealed)

Run with the pinned venv's Python (needs the pristine fixture tars).
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adapter  # noqa: E402

RUNS, OUT = HERE / "runs", HERE / "blind"
ARM_WORDS = re.compile(r"\b(baseline|candidate|C1′?|C1')\b", re.I)
AUTHOR_SLUG = "flag-stalled-in-progress-tickets-in-coga-status"
FENCE = "<!-- coga:blackboard -->"


def sh(*a: str, cwd: Path) -> str:
    return subprocess.run(a, cwd=cwd, check=True, capture_output=True, text=True).stdout


def scrub(text: str) -> str:
    return ARM_WORDS.sub("<arm-word>", text)


def materialize(run: Path, case: str) -> Path:
    """Pristine fixture + the run's bundle, refs under refs/trial/."""
    tmp = Path(tempfile.mkdtemp(prefix="q-blind-"))
    with tarfile.open(adapter.PRISTINE / f"{case}.tar") as tar:
        members = [m for m in tar.getmembers() if m.name.split("/")[0] == "root"]
        for m in members:
            m.name = "/".join(m.name.split("/")[1:]) or "."
            tar.extract(m, tmp, filter="tar")
    sh("git", "fetch", "-q", str(run / "repo.bundle"),
       "+refs/heads/*:refs/trial/heads/*", "+refs/remotes/origin/*:refs/trial/origin/*", cwd=tmp)
    return tmp


def show(repo: Path, ref: str, path: str) -> str | None:
    r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=repo, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def frontmatter(text: str | None) -> dict:
    import yaml
    if not text or not text.startswith("---\n"):
        return {}
    return yaml.safe_load(text[4:text.index("\n---\n", 4)]) or {}


def dev_branch(ticket: str | None) -> str | None:
    m = re.search(r"^## Dev\s*\n(?:.*\n)*?branch:\s*(\S+)", ticket or "", re.M)
    return m.group(1) if m else None


def ticket_path(case: str) -> str:
    slug = AUTHOR_SLUG if case == "author" else adapter.CASES[case]["slug"]
    return f"coga/tasks/{slug}.md"


def artifact(run: Path, case: str, rec: dict, repo: Path) -> tuple[str, dict]:
    base = rec["fixture_head"]
    final = "refs/trial/origin/main"
    tp = ticket_path(case)
    before, after = show(repo, base, tp), show(repo, final, tp)
    info: dict = {"ticket_on_origin_main": after is not None}
    parts: list[str] = []
    if case in ("code", "docs"):
        br = dev_branch(after)
        info["branch"] = br
        ref = None
        for cand in (f"refs/trial/origin/{br}", f"refs/trial/heads/{br}"):
            if br and subprocess.run(["git", "rev-parse", "-q", "--verify", cand], cwd=repo,
                                     capture_output=True).returncode == 0:
                ref = cand
                break
        info["branch_pushed"] = bool(ref and ref.startswith("refs/trial/origin/"))
        if ref:
            stat = sh("git", "diff", "--stat", f"{base}...{ref}", "--", ".", ":!coga/log.md",
                      ":!coga/tasks", cwd=repo)
            diff = sh("git", "diff", f"{base}...{ref}", "--", ".", ":!coga/log.md",
                      ":!coga/tasks", cwd=repo)
            commits = sh("git", "log", "--reverse", "--format=%s%n%n%b", f"{base}..{ref}",
                         "--", ".", ":!coga/log.md", ":!coga/tasks", cwd=repo)
            parts += ["## Commit messages\n\n```\n" + commits.strip() + "\n```",
                      "## Diff summary\n\n```\n" + stat.strip() + "\n```",
                      "## Diff\n\n```diff\n" + diff + "```"]
        else:
            parts.append("## Diff\n\n_No branch with changes was produced._")
        board = (after or "").split(FENCE, 1)[1] if after and FENCE in after else ""
        parts.append("## Ticket blackboard at the end of the step (handoff, PR receipts)\n\n"
                     + "````markdown\n" + board.strip() + "\n````")
    elif case == "design":
        diff = subprocess.run(["git", "diff", base, final, "--", tp], cwd=repo,
                              capture_output=True, text=True).stdout
        parts += ["## Ticket after the design step (full)\n\n````markdown\n" + (after or "_missing_")
                  + "\n````",
                  "## Change to the ticket\n\n```diff\n" + diff + "```"]
    else:  # author
        parts.append("## Authored ticket (full)\n\n````markdown\n" + (after or "_missing on main_")
                     + "\n````")
        others = sh("git", "diff", "--name-status", rec["fixture_head"], final, "--", ".",
                    ":!coga/log.md", f":!{tp}", cwd=repo)
        if others.strip():
            parts.append("## Other files the session changed on main\n\n```\n" + others + "```")
    return scrub("\n\n".join(parts)) + "\n", info


def gates(run: Path, case: str, rec: dict, repo: Path, info: dict) -> dict:
    base = rec["fixture_head"]
    final = "refs/trial/origin/main"
    tp = ticket_path(case)
    before, after = show(repo, base, tp), show(repo, final, tp)
    fb, fa = frontmatter(before), frontmatter(after)
    log_new = sh("git", "diff", base, final, "--", "coga/log.md", cwd=repo)
    added = [l[1:] for l in log_new.splitlines() if l.startswith("+") and not l.startswith("+++")]
    g: dict = {
        "integrity": {
            "production_equals_frozen_baseline": rec.get("production_equals_frozen_baseline"),
            "delivered_equals_frozen": rec.get("delivered", {}).get("equals_frozen_modulo_marker"),
            "live_repo_changed": rec.get("live_repo_changed"),
            "venv_changed": rec.get("venv_changed"),
            "sandbox": [[p.get("permission_profile", {}).get("file_system") for p in s]
                        for s in rec.get("effective_sandbox", [])],
        },
        "status_before": fb.get("status"), "step_before": fb.get("step"),
        "status_after": fa.get("status"), "step_after": fa.get("step"),
        "frontmatter_keys_changed": sorted(
            k for k in set(fb) | set(fa)
            if k not in ("status", "step", "contexts") and fb.get(k) != fa.get(k)),
        "log_lines_added": added,
        "merge_commits": sh("git", "rev-list", "--merges", "--all", f"^{base}", cwd=repo).split(),
        "non_coga_changes_on_main": sh("git", "diff", "--name-only", base, final, "--", ".",
                                       ":!coga", cwd=repo).split(),
        "rollouts": len(rec.get("codex_sessions", [])),
        "wall_seconds": rec.get("wall_seconds"),
        "tokens": rec.get("tokens"),
        "result": rec.get("result"),
        **info,
    }
    checks = []
    i = g["integrity"]
    if not (i["production_equals_frozen_baseline"] and i["delivered_equals_frozen"]):
        checks.append("integrity: prompt identity")
    if i["live_repo_changed"] or i["venv_changed"]:
        checks.append("integrity: live repo or venv changed")
    if g["frontmatter_keys_changed"] and case != "author":
        checks.append(f"authority: CLI-owned frontmatter changed {g['frontmatter_keys_changed']}")
    if g["non_coga_changes_on_main"]:
        checks.append("checkout: product files landed on main without review")
    if case == "author":
        if g["status_after"] not in ("draft", None):
            checks.append(f"authority: authoring changed status to {g['status_after']}")
        if any(re.search(r"\b(bump|done|active|unblock)", l) for l in added
               if "] [system] {" not in l):  # usage records carry exit_kind "done"
            checks.append("authority: lifecycle transition during authoring")
    else:
        moved = (g["step_after"] or "").split(" ")[0] if g["status_after"] != "blocked" else None
        if g["status_after"] == "blocked":
            checks.append("completion: blocked (inspect the reason)")
        elif moved != "2":
            checks.append(f"completion: expected one bump to step 2, got {g['status_after']}/{g['step_after']}")
        if case in ("code", "docs") and not g.get("branch_pushed"):
            checks.append("completion: no pushed branch recorded")
    if g["merge_commits"]:
        checks.append(f"checkout: merge commits {g['merge_commits']} (inspect: reconcile vs unrequested)")
    g["flags"] = checks
    return g


def regate() -> None:
    """Recompute gates.json only (pack and key untouched)."""
    out = {}
    for run in sorted(p for p in RUNS.iterdir() if p.is_dir() and not p.name.startswith("_")):
        case = run.name.split("__")[0]
        rec = json.loads((run / "record.json").read_text())
        repo = materialize(run, case)
        try:
            _, info = artifact(run, case, rec, repo)
            out[run.name] = gates(run, case, rec, repo, info)
        finally:
            shutil.rmtree(repo, ignore_errors=True)
    (HERE / "gates.json").write_text(json.dumps(out, indent=1, default=str) + "\n")


def main() -> None:
    if sys.argv[1:2] == ["regate"]:
        return regate()
    seed = int(sys.argv[1])
    rng = random.Random(seed)
    if OUT.exists():
        raise SystemExit("blind/ exists; never overwritten")
    runs = sorted(p for p in RUNS.iterdir() if p.is_dir() and not p.name.startswith("_"))
    by_pair: dict[tuple[str, int], dict[str, Path]] = {}
    for r in runs:
        case, arm, rep = r.name.split("__")
        by_pair.setdefault((case, int(rep[1:])), {})[arm] = r
    key, gate_out, rows = {}, {}, []
    for (case, rep), arms in sorted(by_pair.items()):
        if set(arms) != {"baseline", "candidate"}:
            print(f"skip incomplete pair {case} r{rep}")
            continue
        pid = hashlib.sha256(f"{seed}:{case}:{rep}".encode()).hexdigest()[:6]
        labels = ["X", "Y"]
        rng.shuffle(labels)
        key[pid] = {"case": case, "rep": rep, labels[0]: "baseline", labels[1]: "candidate"}
        for arm, label in zip(("baseline", "candidate"), labels):
            run = arms[arm]
            rec = json.loads((run / "record.json").read_text())
            repo = materialize(run, case)
            try:
                text, info = artifact(run, case, rec, repo)
                gate_out[run.name] = gates(run, case, rec, repo, info)
            finally:
                shutil.rmtree(repo, ignore_errors=True)
            d = OUT / pid / label
            d.mkdir(parents=True)
            (d / "artifact.md").write_text(f"# Pair {pid}, output {label} ({case})\n\n{text}")
        rows.append({"pair": pid, "case": case, "better": "", "reason": ""})
    rows.sort(key=lambda r: r["pair"])
    with (OUT / "verdicts.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["pair", "case", "better", "reason"])
        w.writeheader()
        w.writerows(rows)
    (HERE / "blind-key.json").write_text(json.dumps({"seed": seed, "pairs": key}, indent=1) + "\n")
    (HERE / "gates.json").write_text(json.dumps(gate_out, indent=1, default=str) + "\n")
    print(f"{len(rows)} pairs; key sha256 "
          f"{hashlib.sha256((HERE / 'blind-key.json').read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
