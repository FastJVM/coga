"""Disposable C1 / C1' prompt builder for ticket 04 (evidence, not product code).

C1 is ticket 01's hand-assembled candidate. This builder derives it
mechanically from a baseline prompt so new cases can be rendered:

  * the `## Coga base prompt` layer becomes four layers: orientation
    (candidate/base.md), invocation facts (JSON), interactive session
    boundaries (candidate/interactive.md) and ticket editing
    (candidate/task-editing.md);
  * for authoring, the `## Ticket loop` layer becomes `## Authoring authority`
    (candidate/author.md);
  * a `## Workflow position (metadata)` layer precedes `## Current step`.

C1' (owner-confirmed 2026-11-14) differs from C1 in one place only: the
interactive-boundaries layer starts with the baseline base prompt's
`## Check the starting checkout` and `## Reconcile before publishing`
sections, verbatim, instead of C1's two compressed checkout/reconcile
paragraphs. C1's closing boundaries paragraph (coga.toml, nested launch) is
kept.

  c1prime.py verify          rebuild ticket 02's C1 from its baselines; must be byte-identical
  c1prime.py build IN OUT FACTS.json [--author] [--position POS.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
T02 = HERE.parent / "02-compare-current-and-candidate-prompt-assembly" / "approved"
FRAG = T02 / "candidate"
SEP = "\n\n---\n\n"


def frag(name: str) -> str:
    return (FRAG / name).read_text().rstrip("\n")


def baseline_sections(base_layer: str) -> tuple[str, str]:
    """Return the baseline's checkout and reconcile sections, verbatim."""
    a = base_layer.index("## Check the starting checkout")
    b = base_layer.index("## Reconcile before publishing")
    c = base_layer.index("## The ticket and blackboard")
    return base_layer[a:b].rstrip("\n"), base_layer[b:c].rstrip("\n")


def interactive_c1prime(base_layer: str) -> str:
    checkout, reconcile = baseline_sections(base_layer)
    paras = frag("interactive.md").split("\n\n")
    assert len(paras) == 3 and paras[2].startswith("Do not edit `coga.toml`"), paras
    # Baseline sections are level-2 headings inside the layer; demote to ###
    # so the layer keeps a single `##` title like every other C1 layer.
    body = "\n\n".join([checkout.replace("## ", "### ", 1),
                        reconcile.replace("## ", "### ", 1),
                        "### Boundaries\n\n" + paras[2]])
    return body


def build(baseline: str, facts: dict, *, author: bool, position: dict | None,
          prime: bool) -> str:
    layers = baseline.split(SEP)
    out: list[str] = []
    for layer in layers:
        if layer.startswith("## Coga base prompt\n"):
            inter = interactive_c1prime(layer) if prime else frag("interactive.md")
            out += ["## Coga orientation\n\n" + frag("base.md"),
                    "## Invocation facts\n\n" + json.dumps(facts, indent=2, ensure_ascii=False),
                    "## Interactive session boundaries\n\n" + inter]
            if facts.get("target_kind") == "task":  # stateless targets have no ticket to edit
                out.append("## Ticket editing and working state\n\n" + frag("task-editing.md"))
        elif author and layer.startswith("## Ticket loop\n"):
            out.append("## Authoring authority\n\n" + frag("author.md"))
        elif layer.startswith("## Current step") and position is not None:
            out += ["## Workflow position (metadata)\n\n" + json.dumps(position, indent=2),
                    layer]
        else:
            out.append(layer)
    return SEP.join(out)


def _json_layer(text: str, title: str) -> dict | None:
    for layer in text.split(SEP):
        if layer.startswith(f"## {title}\n"):
            return json.loads(layer.split("\n\n", 1)[1])
    return None


def verify() -> int:
    bad = 0
    for case_dir in sorted((T02 / "prompts").iterdir()):
        if case_dir.name.startswith("autofix"):
            continue  # analysis prompts use an independent builder; out of scope here
        base = (case_dir / "baseline.md").read_text()
        cand = (case_dir / "candidate.md").read_text()
        facts = _json_layer(cand, "Invocation facts")
        pos = _json_layer(cand, "Workflow position (metadata)")
        author = facts["operation"] == "author"
        got = build(base, facts, author=author, position=pos, prime=False)
        ok = got == cand
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {case_dir.name}")
        if not ok:
            import difflib
            sys.stdout.writelines(list(difflib.unified_diff(
                cand.splitlines(True), got.splitlines(True), "frozen", "built"))[:40])
    return bad


def main() -> None:
    if sys.argv[1:2] == ["verify"]:
        sys.exit(1 if verify() else 0)
    if sys.argv[1:2] == ["build"]:
        src, dst, facts_path = map(Path, sys.argv[2:5])
        rest = sys.argv[5:]
        pos = None
        if "--position" in rest:
            pos = json.loads(Path(rest[rest.index("--position") + 1]).read_text())
        text = build(src.read_text(), json.loads(facts_path.read_text()),
                     author="--author" in rest, position=pos, prime=True)
        dst.write_text(text)
        return
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
