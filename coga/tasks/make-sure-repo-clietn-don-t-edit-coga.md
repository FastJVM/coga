---
slug: make-sure-repo-clietn-don-t-edit-coga
title: make sure repo clietn don't edit coga
status: in_progress
owner: nicktoper
human: nick
agent: claude
assignee: codex
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 2 (evaluate-design)
launch_generation: a687d924-aab8-4e49-a9f2-2fad0a5c906c
---

## Description

When Dream runs in a client repo — one that has Coga installed but is not the
Coga source repo (multiply, magicator) — it treats the installed Coga OS files
as part of its own corpus and reports findings about Coga infrastructure. Those
findings are noise in the client repo: Phase 6 routes them to proposal PRs
against a repo that does not own the code they describe, and the client's real
backlog gets diluted. Worse, a client-repo shard spends its 150 KB budget
auditing prose it cannot verify — every claim the shipped `coga/recurring/*/ticket.md`
templates make about `src/coga/*.py` is uncheckable there, because `src/coga/`
does not exist in a client checkout.

Teach Dream to recognise it is not running in the Coga source repo and to keep
Coga-owned files out of its scan corpus. What it still notices about Coga is not
discarded — it appends to a dedicated upstream file in the client repo, and a
new recurring job in the Coga repo sweeps configured client checkouts, reads
those files, and files real tickets here.

### Acceptance criteria

**Repo identity**

- [ ] `scan-protocol/SKILL.md` gains one `## Repo identity` section stating the
      single test — a checkout is the **Coga source repo** when
      `<checkout-root>/src/coga/resources/templates/coga/` is a directory, and a
      **client repo** otherwise — and stating that Dream evaluates it once per
      run and records the verdict in the scan directory's `index.md`; shards
      read the verdict and never re-derive it.
- [ ] `knowledge-scan/SKILL.md` and `contract-audit/SKILL.md` reference that
      section rather than restating the test.

**Exclusion (Rule A — path ownership)**

- [ ] `scan-protocol/SKILL.md` carries the owned-path derivation as a runnable
      block: every repo-relative path the *installed* package owns, derived from
      `templates/coga` with both of `test_packaging.py`'s counterpart mappings
      (`templates/coga/<rel>` → `coga/<rel>`, and
      `templates/coga/bootstrap/<contexts|skills|workflows>/<rel>` →
      `coga/<contexts|skills|workflows>/<rel>`).
- [ ] The block names its carve-outs — packaged seeds a client owns after
      install: `coga/coga.toml`, `coga/log.md`, `coga/context.md`,
      `coga/.gitignore`, `coga/.gitattributes`, `coga/contexts/.gitignore`,
      `coga/recurring/digest/spool.md`, and everything under `coga/tasks/`.
- [ ] The rule is stated as **per file, not per directory**: excluding
      `coga/skills/direct/body/SKILL.md` must not exclude a client's own sibling
      under `coga/skills/direct/`.
- [ ] In a client repo Dream applies Rule A **while building `index.md`**, so
      the exclusion happens in exactly one place and no shard needs a filter.
      `index.md` records the count excluded so the decision is auditable.
- [ ] In the Coga source repo Rule A is not applied and `index.md` is unchanged.

**Exclusion (Rule B — source-of-truth ownership)**

- [ ] `contract-audit/SKILL.md`'s "code reality" bullet is qualified: in a
      client repo `src/coga/` does not exist, so code reality means the client's
      own code, and a claim whose only source of truth is Coga's implementation
      (a `src/coga/` symbol, a CLI flag/exit contract, a packaged template) is
      **not checkable and not a local finding**.
- [ ] `scan-protocol/SKILL.md`'s finding block gains an optional
      `owner: <local | coga>` field, default `local`. A shard that reaches a
      Coga-owned conclusion from an in-corpus client file writes `owner: coga`.
- [ ] Both scan skills state that `owner: coga` findings never propose a local
      edit.

**Upstream capture**

- [ ] `coga/recurring/dream/ticket.md` Phase 6 gains a route for `owner: coga`
      findings: append to `<checkout-root>/coga/upstream-coga.md`, creating the
      file with its documented header when missing. They are **not** routed to
      proposal PRs or draft tickets.
- [ ] The entry shape is specified in Phase 6 and is stable enough to parse:
      an `## <title>` heading, then `- id:`, `- repo:`, `- date:`, `- class:`,
      `- target:`, `- evidence:` lines, then one prose paragraph. `id` is
      `<YYYY-MM-DD>-<slug-of-title>`, suffixed `-2`, `-3`… on collision within
      the file.
- [ ] The file is documented as **append-only**: entries are appended in order
      and never reordered, rewritten, or removed.
- [ ] The run summary vocabulary gains `upstream-captured`, and the summary
      reports how many entries were appended.
- [ ] In the Coga source repo Phase 6 is unchanged — no `owner: coga` findings
      arise, since every Coga-owned file is in this repo's own corpus.
- [ ] The live and packaged copies of `coga/recurring/dream/ticket.md` are
      edited together (`tests/test_packaging.py` enforces it).

**Config key**

- [ ] `coga.local.toml` accepts `[upstream] checkouts = ["/abs/path", …]`:
      `"upstream"` added to `_ALLOWED_LOCAL_SECTIONS`, a
      `_ALLOWED_UPSTREAM_KEYS = frozenset({"checkouts"})` check wired into
      `_reject_unknown_sections`, a `_parse_upstream` parser, and a
      `upstream_checkouts: tuple[Path, ...] = ()` field on `Config`.
- [ ] It is local-only: `[upstream]` in `coga.toml` is rejected by the existing
      shared-section check (paths are machine-specific).
- [ ] The parser validates **shape only** — a list of strings, `~` expanded,
      resolved absolute. A path that does not exist on disk is accepted, because
      hard-failing config load would brick every `coga` command on this machine
      the moment a client repo is moved.
- [ ] Config tests cover: absent section → `()`; a valid list; a non-list value;
      a non-string element; an unknown key inside `[upstream]`; `[upstream]` in
      `coga.toml` rejected.

**Upstream processor**

- [ ] A new recurring task `coga/recurring/upstream-coga/` exists with
      `ticket.md` (cron `schedule:`, `workflow: upstream-coga/run`) and the
      reserved sibling `ticket.py`, plus a one-step workflow
      `coga/workflows/upstream-coga/run.md`.
- [ ] It is **not** packaged under `src/coga/resources/templates/coga/recurring/`
      — it only makes sense in this repo. Because twins are derived from the
      packaged tree, an unpackaged live file is simply not a pair, so no
      `INTENTIONALLY_DIVERGENT_TWINS` entry is needed or wanted.
- [ ] `ticket.py` is deterministic, imports only shared core infra
      (`coga.config`, `coga.create`, `coga.taskfile`, `coga.blackboard`,
      `coga.git`), and adds nothing to `src/coga/`.
- [ ] For each configured checkout it reads `<checkout>/coga/upstream-coga.md`,
      skips entries at or before that checkout's cursor, and calls `create_task`
      once per new entry with the entry's title, a body carrying `repo`, `date`,
      `class`, `target`, `evidence` and the prose, and
      `created_by="recurring/upstream-coga"`.
- [ ] The cursor is one `- <checkout-name>: <last-processed-id>` line per
      checkout under a `## Upstream cursors` section on the **template's**
      blackboard (`coga/recurring/upstream-coga/ticket.md`), written with
      `coga.taskfile` / `coga.blackboard` helpers so frontmatter is never
      hand-edited, and synced through git.
- [ ] A missing checkout path, or a checkout with no `coga/upstream-coga.md`,
      is skipped with a printed note — never an error.
- [ ] If a checkout's recorded cursor id is **no longer present** in that file,
      the processor stops for that checkout and reports it instead of
      re-ticketing every entry. (Truncation is the one case where the
      append-only contract was broken; silently re-filing the whole file is the
      worse failure.)
- [ ] `coga validate --json` passes with the new recurring task and workflow.

**Verification beyond the suite**

- [ ] A Dream run in `/home/n/Code/multiply` produces an `index.md` whose corpus
      is non-empty and contains **zero** Coga-owned paths, and `## Findings`
      names none.
- [ ] A Dream run in this repo produces the same corpus it does today.
- [ ] A hand-written `coga/upstream-coga.md` with two entries yields two
      tickets on the first processor run and zero on a second run.

### Proposed shape

Five pieces, in this order. Pieces 1–3 are prose-only; 4–5 are code.

**1. Repo identity, stated once**
`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/scan-protocol/SKILL.md`
gains a `## Repo identity` section directly after `## The scan directory`. The
test is a filesystem fact, not config: a checkout is the Coga source repo when
`<checkout-root>/src/coga/resources/templates/coga/` is a directory. A fork or
vendored copy of the Coga source genuinely *is* a Coga source repo for this
purpose, so classifying it as one is correct rather than a false positive. This
also generalises the existing narrower hedge at `contract-audit/SKILL.md:76`
("In a downstream repo with no packaged source tree…"), which should then point
at the new section instead of restating it.

Dream evaluates the test once per run and writes one line at the top of each
phase's `index.md`:

```
repo-identity: client | coga-source
```

Shards read that line. Nothing re-derives it.

**2. Rule A — the owned-path set, applied at index time**
The same section carries the derivation as a runnable block. It is the
`test_packaging.py` twin derivation pointed at the *installed* package instead
of this repo's source tree — the same two counterpart mappings, so the rule and
the packaging test cannot drift apart in principle:

```sh
python - <<'PY'
from pathlib import Path
from importlib.resources import files
root = Path(files("coga.resources").joinpath("templates", "coga"))
BUNDLED = {"contexts", "skills", "workflows"}
SKIP = {".coga", ".venv", ".agent-skills", ".claude", ".codex", "__pycache__"}
CARVE_OUTS = {
    "coga/coga.toml", "coga/log.md", "coga/context.md", "coga/.gitignore",
    "coga/.gitattributes", "coga/contexts/.gitignore",
    "coga/recurring/digest/spool.md",
}
owned = set()
for path in sorted(root.rglob("*")):
    if not path.is_file():
        continue
    rel = path.relative_to(root)
    parts = rel.parts
    if set(parts) & SKIP or parts[0] == "tasks":
        continue
    owned.add(("coga" / rel).as_posix())
    if len(parts) > 2 and parts[0] == "bootstrap" and parts[1] in BUNDLED:
        owned.add(Path("coga").joinpath(*parts[1:]).as_posix())
for entry in sorted(owned - CARVE_OUTS):
    print(entry)
PY
```

It is pure Python, so it is portable — the protocol's "no GNU-only `find
-printf`" rule is satisfied. Verified against the installed 0.x package: 155
owned paths, of which the ones that actually collide with a real client tree are
`coga/recurring/*/ticket.{md,py}` (all seven shipped jobs), the shipped
`coga/workflows/*` files, `coga/skills/direct/body/SKILL.md`,
`coga/contexts/browser/*`, `coga/contexts/dev/code/SKILL.md`, and — on repos
installed before `bootstrap/` stopped being copied — `coga/contexts/coga/**`.

When `repo-identity: client`, Dream subtracts that set from the corpus **as it
writes `index.md`**, and appends `excluded-coga-owned: <N>` beneath the identity
line. Doing it once at index time rather than as a filter in three skills is the
whole point: one place to get right, one place to audit. Shards need no new
rule, and Rule A therefore produces no findings at all — it is purely a
noise-and-budget win.

**3. Rule B — source-of-truth ownership, and the upstream file**
Rule A cannot catch everything, because a client-owned file can still make a
claim about Coga. `contract-audit/SKILL.md`'s "code reality" bullet gets
qualified for the client case, and `scan-protocol/SKILL.md`'s finding block
gains `owner: <local | coga>` (default `local`). That is the sole capture path.

`coga/recurring/dream/ticket.md` Phase 6 gains the route — **edit the packaged
twin in the same commit**:

(shown indented by two spaces so the example heading cannot terminate this
`## Description` section — `compose._SECTION_HEADING_RE` is a plain `^##`
regex and does not skip code fences; write the real entry flush left)

```markdown
  ## <title>

  - id: 2026-09-09-phase-6-names-a-dead-recipe
  - repo: multiply
  - date: 2026-09-09
  - class: drift
  - target: coga/recurring/dream/ticket.md
  - evidence: coga/contexts/multiply/developer-flow/SKILL.md:44

  <one paragraph>
```

`coga/upstream-coga.md` sits at the client checkout's coga root, is git-tracked,
and is append-only. Phase 6 creates it with a short header explaining what it is
and that the Coga repo sweeps it.

**4. `[upstream] checkouts` in `coga.local.toml`**
In `src/coga/config.py`: add `"upstream"` to `_ALLOWED_LOCAL_SECTIONS`; add
`_ALLOWED_UPSTREAM_KEYS = frozenset({"checkouts"})` and one
`_reject_unknown_keys(local.get("upstream"), …, "[upstream] in coga.local.toml")`
call in `_reject_unknown_sections`; add `_parse_upstream(local) -> tuple[Path, ...]`
next to `_parse_layout`; add `upstream_checkouts: tuple[Path, ...] = ()` to
`Config` after `contexts_dir`. Shape validation only — existence is the
processor's business, not config load's.

**5. The processor**
`coga/workflows/upstream-coga/run.md` — a one-step workflow modelled line for
line on `coga/workflows/blocker-reminders/run.md`.

`coga/recurring/upstream-coga/ticket.md` — cron `schedule:` (daily is enough),
`workflow: upstream-coga/run`, a `## Description` explaining the pull direction,
and a blackboard seeded with an empty `## Upstream cursors` section.

`coga/recurring/upstream-coga/ticket.py` — same skeleton as
`coga/recurring/branch-sweep/ticket.py` (do the work, then `subprocess` `coga
bump "$COGA_TASK_SLUG"` through the CLI):

- `load_config()`; for each `cfg.upstream_checkouts`, read
  `<checkout>/coga/upstream-coga.md`; skip missing with a note.
- `parse_entries(text) -> list[Entry]` — split on `^## `, pull the `- key:`
  lines and the trailing paragraph. A malformed block is reported and skipped,
  not fatal.
- Cursor: read `## Upstream cursors` from
  `recurring_dir(cfg) / "upstream-coga" / "ticket.md"` via `read_blackboard`.
  Entries up to and including the cursor id are already filed. A recorded cursor
  id absent from the file means truncation — report and skip that checkout.
- `create_task(cfg=…, title=entry.title, workflow_name=None, …,
  description=<provenance + prose>, created_by="recurring/upstream-coga")` per
  new entry. Draft status (the repo default) is deliberate: a human triages
  before a workflow is assigned.
- Write the new cursor back with `upsert_blackboard` / `append_to_section`, then
  sync through git.

**Order of work.** 4 → 5 → 1 → 2 → 3. The config key and processor are testable
in this repo alone and give the client-side prose a real destination to describe;
doing the prose first leaves the acceptance criteria unverifiable.

### Out of scope

- Changing what Dream considers a finding *within* the client's own product.
- Any transport requiring the client repo to reach into this one. The direction
  is deliberately Coga-repo-pulls: a client repo needs no credentials for this
  repo and no knowledge of where it lives. The accepted cost is that the sweep
  only works on a machine holding every client checkout, and that the checkout
  list is maintained by hand.
- Retrofitting upstream files for Dream runs that already happened.
- Deduplicating upstream entries *across* client repos — two repos noticing the
  same Coga issue file two tickets. Cheap to merge by hand; not worth machinery
  until it happens.
- Shipping the processor downstream. It stays unpackaged.
- Auto-assigning a workflow to an upstream-derived ticket.

## Context

### Where the current behavior comes from

The Dream scan skills are written from inside the Coga source repo and never
distinguish Coga-owned files from the client's own:

- `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/scan-protocol/SKILL.md:8-9`
  calls both decide-half scans "read-only sweeps over **Coga's own** corpus".
- `.../scan/contract-audit/SKILL.md:55-74` audits `coga/` against
  `src/coga/resources/templates/coga/` — a pairing that only exists here.
  Line 76 already hedges for downstream repos, but only for that one shard group.
- `.../scan/knowledge-scan/SKILL.md:47-53` defines the corpus as the configured
  contexts dir, `coga/skills/**`, and `coga/workflows/**`, with no notion of
  which tree owns them.

None of the three has a live counterpart under `coga/skills/` — they are bundled
batteries, so the packaged copy is the only one to edit. `coga/.agent-skills/` is
a generated, gitignored symlink view of them (`coga/.gitignore:13`).

### What a client repo actually contains — measured, not assumed

An earlier draft of this ticket said `coga init` installs the OS contexts at
`coga/contexts/coga/**`. **On a current install it does not.**
`copy_fresh_templates` (`src/coga/commands/update.py:58`) copies the packaged
tree with `skip_top={"bootstrap"}`, and the bundled contexts, skills, and
workflows resolve straight from the installed package
(`paths.bootstrap_context_path` → `packaged_template_path("bootstrap", …)`),
never from the client's tree.

Checked against `/home/n/Code/multiply`:

- `coga/contexts/` — **100% client-authored** (`multiply/*`, `dev/branch-drift`)
  plus the two shipped `browser/*` contexts. No `coga/` namespace at all.
- `coga/skills/` — client's own (`design`, `tickets`) + the already-excluded
  managed `google-agents-cli-*` trees + the shipped `direct/body`.
- `coga/workflows/` — **mixed**: client-authored (`cleanup/`, `design/`, `code/`,
  `deploy/`) alongside shipped `autoclose-merged/sweep.md`,
  `blocker-reminders/run.md`, `branch-sweep/sweep.md`, `skill-update/run.md`,
  `direct/body.md`, `brief-for-human.md`, `draft-for-human.md`.
- `coga/recurring/` — all seven shipped jobs, every one Coga-owned.
- `coga/tasks/`, `coga/log.md`, `coga/context.md`, `coga/coga.toml` — client's own.

So the ticket's core warning still holds and is the thing to keep hold of:
**excluding `coga/` wholesale would empty Dream's corpus**, because in a client
repo `coga/` is also where the client's own knowledge lives. The Coga-owned part
is a per-file subset, and `coga/recurring/*/ticket.md` is the largest and
noisiest slice of it — those templates make dozens of claims about `src/coga/`
symbols that a client checkout cannot verify at all.

### Precedent to generalise from

`knowledge-scan/SKILL.md:55-59` already solves this shape for installer-managed
skills — "**The manifest's `ref` list in `src/coga/resources/managed-skills.toml`
is the whole test.**" Coga-installed OS files are the same category. The
difference is that no hand-maintained manifest is needed here: the installed
package's own `templates/coga` tree already *is* the manifest, and deriving from
it means the exclusion updates itself whenever Coga ships a new template.

### Recurring-task facts the processor needs

Inlined rather than attaching the 52.6 KiB `coga/recurring` context.

- A recurring task is `coga/recurring/<name>/ticket.md` with a cron `schedule:`
  in frontmatter; the directory name must not start with an underscore.
- The reserved sibling `ticket.py` is the deterministic half. `coga launch` runs
  it as `[sys.executable, "<task>/ticket.py"]` with no operands, copied into each
  period task and run headlessly before any agent phase. It ends by
  `subprocess`-ing `coga bump "$COGA_TASK_SLUG"` — calling the Typer function
  in-process would pass `OptionInfo` sentinels.
- **Durable state lives in the template directory, not the period task.**
  `coga/recurring/digest/spool.md` is the precedent: `digest_spool_path`
  (`src/coga/notification/__init__.py:166`) resolves it as
  `recurring_dir(cfg) / "digest" / "spool.md"`. The template's blackboard
  persists the same way. `blocker-reminders` deliberately does the opposite —
  its watermark rides the *blocked task* — so both patterns are live; pick per
  payload. Here the payload is one line per checkout, so the blackboard is
  enough and keeps the state where a human reading the job sees it.
- A template may name any resolvable workflow; there is no recurring registry to
  register in. Authoring path: create the directory, then `coga validate --json`.

`coga/recurring/blocker-reminders/` is the closest model — one-step workflow plus
a `ticket.py` that scans, watermarks, and syncs through git.

### Constraints

- **The config key needs a core change, and that is expected here.**
  `src/coga/config.py:440` defines `_ALLOWED_LOCAL_SECTIONS = frozenset({"user",
  "agents", "notification", "git"})`, and `_reject_unknown_sections` (line 497)
  hard-fails on anything else — an unrecognised top-level key in
  `coga.local.toml` makes *every* coga command exit. Config parsing is shared
  infra with many consumers, so this does not breach the microkernel rule.
  `[layout]`'s comment at line 476 is the model for documenting why a section is
  local-only or shared-only.
- Agents may not edit `coga.toml` or `coga.local.toml`
  (`src/coga/resources/prompt.md:117`). Implement the key and its parser, then
  ask the human to fill in the checkout paths. **The processor cannot be
  verified end-to-end until they do** — a launch prerequisite, not an implement-
  time surprise. A temporary `COGA_LOCAL_CONFIG`-style override is not available;
  the implement step should test `_parse_upstream` directly and test the
  processor with a config built in a pytest tmp repo.
- The processor's deterministic half goes in its sibling `ticket.py`, not
  `src/coga/`. Adding a recurring job is not by itself a reason to put code in
  core (`CLAUDE.md`, microkernel rule).
- **Packaging twins.** Twins are *derived* from the packaged tree
  (`tests/test_packaging.py:170-205`), so a live file with no packaged copy is
  simply not a pair — leaving `coga/recurring/upstream-coga/` and
  `coga/workflows/upstream-coga/` unpackaged needs no test change and no
  `INTENTIONALLY_DIVERGENT_TWINS` entry. `coga/recurring/dream/ticket.md` **is**
  an enforced twin; edit both copies together.
- Keep green: `tests/test_dream_skill_scripts.py`,
  `tests/test_dream_worker_templates.py`, `tests/test_dream_validate_drift.py`,
  `tests/test_packaging.py`, and the config tests.
  `tests/test_dream_worker_templates.py` asserts against SKILL.md prose
  substrings — that is the existing pattern for the new prose assertions.

### Related

`coga/tasks/dream-shouldn-t-touch-coga-in-coga-enabled-repo.md` is the same idea,
filed empty; canceled in favour of this ticket.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Open Questions

1. **Repo identity: filesystem test or explicit config marker?** The spec picks
   the filesystem test (`<checkout>/src/coga/resources/templates/coga/` is a
   directory) because it needs no config in any repo and cannot get out of sync.
   It classifies a fork or vendored Coga source as a source repo, which I argue
   is correct rather than a false positive — such a checkout really does own the
   files. If the owner would rather have an explicit opt-in
   (`[extensions.coga] source_repo = true`, which needs no config-schema change
   at all since `[extensions]` is free-form), that is a one-line swap in the
   `## Repo identity` section. Not blocking.

2. **Should an upstream-derived ticket get a workflow?** The spec creates plain
   drafts so a human triages. Phase 6's `gap` route instead uses
   `--workflow code/with-review`. If the owner wants these to arrive
   ready-to-launch, that is a one-argument change in `ticket.py`.

3. **Cadence for the processor.** The spec says "daily is enough" without
   picking a cron line. Client-repo Dream runs weekly (`0 9 * * 1`), so anything
   from daily to weekly works; a weekly run offset from Dream's would keep the
   backlog quieter.

4. **Does `coga/upstream-coga.md` need a size ceiling?** It is append-only and
   never pruned, so it grows forever in a long-lived client repo. The processor
   only reads past its cursor, so the cost is disk and diff noise, not runtime.
   No pruning is specified; a later ticket can add an archive rule if it becomes
   real.

## Notes from the design step

- **Corrected a premise in the ticket.** It stated that `coga init` installs the
  OS contexts at `coga/contexts/coga/**` in a client repo. It does not on a
  current install — `copy_fresh_templates` skips `bootstrap/`, and bundled
  contexts/skills/workflows resolve from the installed package. Verified against
  `/home/n/Code/multiply`, whose `coga/contexts/` is entirely client-authored
  apart from the two shipped `browser/*` contexts. The exclusion still matters,
  but its real mass is `coga/recurring/*/ticket.md` and the shipped
  `coga/workflows/*` files, not contexts. Older installs may still carry
  `coga/contexts/coga/**` on disk; the derived owned-path set covers them via the
  bundled-area mapping without special-casing.

- **The owned-path derivation was run, not guessed.** Against the installed
  package it yields 155 paths. Confirmed it produces `coga/contexts/coga/**`
  through the same bundled-area mapping `test_packaging._live_counterparts`
  uses, which is why the spec reuses that mapping verbatim: the exclusion rule
  and the packaging test then cannot diverge in principle.

- **Rule A produces no findings.** Excluding Coga-owned paths from the corpus
  means a client-repo shard never reads them, so all upstream capture comes from
  Rule B (a client-owned file making a claim only Coga's code can settle). This
  is deliberate — a client repo should not spend shard budget auditing Coga's
  prose; that is this repo's Dream's job.

- **Not packaging the processor resolves the twin question cleanly.** Twins are
  derived from the packaged tree, so an unpackaged live file is not a pair. No
  `INTENTIONALLY_DIVERGENT_TWINS` entry, no test edit.

- **Pre-existing test-env failure, not ours.**
  `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries` fails on
  this machine before any change: `.venv` has no `pip`, so the test's
  `python -m pip wheel` shells out to nothing. Reproduced against a clean stash.
  `python -m pip install -e ".[test]"` into `.venv` fixes it. Do not treat it as
  a regression at implement time; the other 20 packaging/dream template tests
  pass.

- **Size check: this is one PR, not two.** The prose edits are three skills plus
  the dream twin; the code is one config section, one `ticket.py`, one workflow,
  one recurring template. No split recommended.
