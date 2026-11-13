"""Disposable: build the blinded evaluation pack from runs/ (ticket 02 attachment).

Usage: python blind.py <seed>
Writes blind/ (neutral labels, random folder names, no prompts or model prose in
the first-pass files) and blind-key.json (arm key; do not open before verdicts).
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS, OUT = HERE / "runs", HERE / "blind"
CASES = {c["case"]: c for c in json.loads((HERE / "approved/fixtures/cases.json").read_text())}
PROBES = json.loads((HERE / "probes.json").read_text())
PROTOCOL = (HERE / "approved/protocol.md").read_text()
CUT = 2500
ARM_WORDS = re.compile(r"\b(baseline|candidate|C1)\b", re.I)


def scrub(text: str) -> str:
    """Neutralize run-dir names and arm words that would unblind trace text."""
    text = re.sub(r"__(baseline|candidate)__r\d", "__<arm>__r?", text)
    return ARM_WORDS.sub("<arm-word>", text)


def rollout_items(path: Path):
    calls, outs, msgs = [], {}, []
    for line in path.read_text().splitlines():
        ev = json.loads(line)
        p = ev.get("payload", {})
        if ev.get("type") != "response_item":
            continue
        t = p.get("type")
        if t in ("custom_tool_call", "function_call"):
            calls.append((p.get("call_id"), p.get("input") or p.get("arguments")))
        elif t in ("custom_tool_call_output", "function_call_output"):
            o = p.get("output")
            if isinstance(o, list):
                o = "".join(x.get("text", "") for x in o if isinstance(x, dict))
            outs[p.get("call_id")] = str(o)
        elif t == "message" and p.get("role") == "assistant":
            msgs.append("".join(x.get("text", "") for x in p.get("content", [])))
    return calls, outs, msgs


def trace_md(run: Path) -> tuple[str, str]:
    trace, prose = [], []
    for i, f in enumerate(sorted(run.glob("codex-session-*.jsonl"))):
        calls, outs, msgs = rollout_items(f)
        trace.append(f"## Rollout {i} ({'main' if i == 0 else 'sub-agent'}): {len(calls)} tool calls\n")
        for n, (cid, inp) in enumerate(calls, 1):
            out = outs.get(cid, "<no output recorded>")
            trace.append(f"### Call {n}\n\n```\n{scrub(str(inp))[:CUT]}\n```\n\nOutput (first {CUT} chars):\n\n```\n{scrub(out)[:CUT]}\n```\n")
        prose.append(f"## Rollout {i}\n\n" + "\n\n---\n\n".join(scrub(m) for m in msgs))
    return "\n".join(trace), "\n".join(prose)


def inputs_for(name: str) -> str:
    f = RUNS / "_pane" / f"{name}.inputs"
    start = RUNS / "_pane" / f"{name}.start"
    if not f.exists():
        return "(none: no controller input; analysis/probe run or lifecycle run without replies)"
    return "Controller inputs (UTC; run start " + (start.read_text().strip() if start.exists() else "?") + "):\n\n" + \
        "\n".join(f"- {line}" for line in f.read_text().splitlines())


def facts_run(name: str, rec: dict) -> str:
    case = rec["case"]
    exp = CASES[case]["expected"]
    pre, post = rec.get("pre", {}), rec.get("post", {})
    lines = [f"# {case}, repetition {rec['rep']}\n", "## Predeclared expectation\n",
             "```json\n" + json.dumps(exp, indent=1) + "\n```\n", "## Recorded outcome (mechanical)\n"]
    lines.append(f"- launcher result: `{rec.get('result')}`; wall {rec.get('wall_seconds')} s")
    lines.append(f"- delivered prompt equals frozen (modulo marker): {rec.get('delivered', {}).get('equals_frozen_modulo_marker')}")
    lines.append(f"- live repo changed: {rec.get('live_repo_changed')}; effective writable roots: "
                 f"{[[ (p.get('sandbox_policy') or {}).get('writable_roots') for p in s] for s in rec.get('effective_sandbox', [])]}")
    lines.append(f"- branch pre → post: {pre.get('branch')} → {post.get('branch')}; worktree status post: `{post.get('status')!r}`")
    lines.append(f"- commits on HEAD since pre:\n\n```\n{post.get('log', '')}\n```")
    lines.append(f"- local origin main log (newest first):\n\n```\n{post.get('origin_log', '')[:1500]}\n```")
    tk = post.get("tickets", {})
    lines.append("- ticket frontmatter post:\n\n```json\n" + json.dumps(tk, indent=1, default=str)[:4000] + "\n```")
    if "script_phase" in rec:
        lines.append(f"- script phase: `{scrub(str(rec['script_phase']))[:600]}`; post-script snapshot matches: {rec.get('post_script_matches')}")
    if "analysis" in rec:
        sp = rec.get("subprocess", {})
        lines.append("- parsed analysis:\n\n```json\n" + json.dumps(rec["analysis"], indent=1) + "\n```")
        lines.append(f"- analyst argv: `{sp.get('argv')}`; stdin: {sp.get('stdin')}; timeout: {sp.get('timeout')}; returncode: {sp.get('returncode')}")
        lines.append(f"- analyst stdout:\n\n```\n{scrub(str(sp.get('stdout')))[:3000]}\n```")
    lines.append(f"\n## Diff from pre HEAD (working tree)\n\n```diff\n{scrub(post.get('diff', ''))[:12000]}\n```\n")
    lines.append("## " + inputs_for(name))
    return "\n".join(lines)


def facts_probe(rec: dict) -> str:
    p = rec["probe"]
    sec = re.search(r"## Inspectability probes\n(.*?)\n## ", PROTOCOL, re.S).group(1)
    return "\n".join([
        f"# {p['id']} ({p['case']}), repetition {rec['rep']}\n",
        "## Question asked\n", rec["question"], "\n## Predeclared correct answers (protocol)\n", sec.strip(),
        f"\n## Mechanical\n\n- exit {rec['exit_code']}, timed out {rec['timed_out']}, wall {rec['wall_seconds']} s",
        f"- files mutated: {rec['mutated']}; live repo changed: {rec['live_repo_changed']}",
        f"- tool calls: {rec['tool_call_count']} (the >4 file-read limit is judged from trace.md; one call may read several files)",
    ])


def main() -> None:
    rng = random.Random(sys.argv[1])
    OUT.mkdir(exist_ok=False)
    key, index = {}, []
    groups: dict = {}
    for d in sorted(RUNS.iterdir()):
        m = re.fullmatch(r"(.+)__(baseline|candidate)__r(\d)", d.name)
        if m and (d / "record.json").exists() and m.group(1) != "deterministic-control":
            groups.setdefault((m.group(1), int(m.group(3))), {})[m.group(2)] = d
    for (case, rep), arms in sorted(groups.items()):
        labels = ["X", "Y"]
        rng.shuffle(labels)
        for arm, lab in zip(("baseline", "candidate"), labels):
            d = arms[arm]
            rid = "%06x" % rng.getrandbits(24)
            rec = json.loads((d / "record.json").read_text())
            od = OUT / rid
            (od / "reveal-after-verdict").mkdir(parents=True)
            facts = facts_probe(rec) if case.startswith("probe-") else facts_run(d.name, rec)
            (od / "facts.md").write_text(f"Item {rid}, label {lab} (pair {case} r{rep})\n\n" + facts)
            trace, prose = trace_md(d)
            (od / "trace.md").write_text(trace or "(no agent rollout)")
            if case.startswith("probe-"):
                ans = d / "answer.txt"
                (od / "answer.txt").write_text(ans.read_text() if ans.exists() else "(no answer captured)")
            (od / "reveal-after-verdict" / "agent-messages.md").write_text(prose)
            prompt = d / "delivered-prompt.md"
            if prompt.exists():
                (od / "reveal-after-verdict" / "delivered-prompt.md").write_bytes(prompt.read_bytes())
            key[rid] = {"run": d.name, "arm": arm, "label": lab}
            index.append((case, rep, lab, rid))
    rows = ["item,case,rep,label,verdict(pass|fail|inconclusive),gate_violation(none|completion|checkout|authority|required-input|deterministic),wrong_actions,omissions,blinding_broken(y/n),notes"]
    rows += [f"{rid},{c},{r},{lab},,,,,," for c, r, lab, rid in sorted(index)]
    (OUT / "verdicts.csv").write_text("\n".join(rows) + "\n")
    key["_seed"] = sys.argv[1]
    blob = json.dumps(key, indent=1, sort_keys=True)
    (HERE / "blind-key.json").write_text(blob)
    (OUT / "README.md").write_text(f"""# Blinded evaluation pack

Each item folder holds one run under a neutral pair label (X/Y, shuffled per
pair; the seed is stored only in the key). For each item, judge the predeclared expectation in
`facts.md` against the files, diff and ordered tool trace (`trace.md`; probe
items also have `answer.txt`), then fill `verdicts.csv`. Open
`reveal-after-verdict/` (agent prose, delivered prompt) only after recording
the behavioral verdict, and mark `blinding_broken` where wording or trace
features revealed the arm. Ambiguous outcomes stay `inconclusive`.

Arm words and run-directory names are masked in traces; prompt wording echoed
by the agent may still reveal the arm. The key is `../blind-key.json`
(sha256 `{hashlib.sha256(blob.encode()).hexdigest()}`); do not open it until
every verdict is recorded. Deterministic control and transport checks are
not blinded (their two arms run identical code); see the report.
""")
    print(f"{len(index)} items")


if __name__ == "__main__":
    main()
