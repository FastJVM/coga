---
title: Fix the Google skills' dead helper invocation paths
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 2 (peer-review)
agent: claude
launch_generation: fdf5c2e3-de06-46b3-a770-0b95c4a5ddaf
---

## Description

Give the three packaged Google skills (`coga/google-calendar`, `coga/gmail`,
`coga/calendar-reminder`) a working way to find their helper scripts, and lock
it with a test. Commit `9c918e06c` (on main since 2026-11-18) already replaced
the dead `$COGA_COGA_OS_ROOT/skills/coga/<skill>/...` paths with a
`/resolved/coga/<skill>/...` placeholder. But the skills only say the
placeholder resolves "as in `coga/checkouts/sandbox-clone`". None of them gives
a command that turns it into a real path, so a caller still has to work it out.

Done means two things. First, there is one concrete, copy-pasteable way to
resolve the helper directory, written in one place. Check for the local
override first (`<coga-dir>/skills/coga/<skill>/`, where `<coga-dir>` is
`$COGA_COGA_OS_ROOT` inside a launch, or the checkout's `coga/` dir outside
one). Fall back to the `coga.paths.packaged_template_path(...)` one-liner. The
same text says where `pip install -r requirements.txt` runs. `coga/google-calendar`
owns this text. `coga/gmail` either restates it in one line for its own skill
or links to it. `coga/calendar-reminder` links to `coga/google-calendar` and
keeps only its call shapes, including its pip line (currently "from the
`coga/google-calendar` skill's dir"). This follows the one-owner rule in
`coga/knowledge`. Second, a test in `tests/test_packaging.py` fails if any
`/resolved/<ref>/<file>` placeholder in packaged resources points at a file the
package does not ship.

## Context

### Current state (verified 2026-11-20 against origin/main)

- The packaged definitions live under
  `src/coga/resources/templates/coga/bootstrap/skills/coga/{google-calendar,gmail,calendar-reminder}/`.
  `google-calendar` ships `gcal.py` and `requirements.txt`. `gmail` ships
  `gmail.py` and `requirements.txt`. `calendar-reminder` is SKILL.md only; it
  shells to `google-calendar`'s `gcal.py`.
- Every call shape already uses the `/resolved/coga/<skill>/<script>.py`
  placeholder, followed by a paragraph defining it as local override else
  installed bundled skill. `google-calendar` also notes that
  `$COGA_COGA_OS_ROOT/skills/coga/google-calendar/` exists only for a local
  override. That note is accurate: `task_env` sets `COGA_COGA_OS_ROOT` to the
  workspace `coga/` dir, and bundled skills are not copied there. Keep it or
  fold it into the new resolution text.
- The stopgap framing and legacy event table that Dream flagged in
  calendar-reminder were already removed by `9c918e06c`. Do not redo them.
- The credential source (env/`secrets:`) was settled by
  `decide-where-the-google-helper-skills-read-their-c` (done). It is out of
  scope here.

### The resolution recipe to reuse (cited, not attached)

`coga/checkouts/sandbox-clone`
(`src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/sandbox-clone/SKILL.md`,
section "What a fresh checkout lacks") is cited, not attached. Its
`seed_local_config.py` example is the existing pattern: resolve the attachment
from the repo's local skills, else the package, via
`python -c 'from coga.paths import packaged_template_path; print(packaged_template_path("bootstrap", "skills", "code", "implement"))'`
under an interpreter that imports `coga`. Mirror that shape for
`("bootstrap", "skills", "coga", "google-calendar")` and `(..., "gmail")`.
`coga.paths.packaged_template_path` joins package-resource parts. Use it in
the one-liner. Don't use `paths.bootstrap_skill_dir`: it takes a `Config`
argument it ignores, which makes it awkward in a `-c` one-liner.

The examples may stay POSIX-shaped: Windows checks happen only at release.
Still, add a short note that `python -c '...'` with single quotes fails in
cmd.exe and needs double quotes there.

Caveat the text must handle: the interpreter that imports `coga` (for example
a `uv tool` venv) may not be the one that has the Google client libs. The
helpers are self-contained scripts, so state which Python runs them and which
one `pip install -r requirements.txt` targets: the same Python that runs the
script, as the files already say.

### Test

Add the check to `tests/test_packaging.py`, which owns "packaged references
point at shipped files" (`tests/test_google_helpers.py` covers credentials
only). Scan every text file under `src/coga/resources/` for
`/resolved/<ref>/<file>`. Today these appear in the three Google SKILL.md
files, the `gcal.py`/`gmail.py` docstrings, `code/implement/SKILL.md`, the
`coga/checkouts/sandbox-clone` context and `workflows/docs/with-review.md`.
Assert that each `<file>` exists under the packaged
`bootstrap/skills/<ref>/` dir. The `.../<file>` shorthand lines need no
check, because their full form appears earlier in the same file. Run
`python -m pytest`.

### Out of scope

- Shipping `gcal`/`gmail` as `coga_edge` entry points (considered and declined
  for this ticket; it would change the package layout and optional deps).
- Dream findings ks-28/ks-29 in `coga/tasks/recurring/dream/ticket.md` are
  partly stale (they predate `9c918e06c`). Don't edit the Dream ticket. Mention
  in the PR body that this change resolves them.
- If behavior docs change, update the owning topic in the same PR
  (AGENTS.md). Here the SKILL.md files are the owners.

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

## Dev

branch: fix-google-skills-helper-paths

## Implement handoff

Commit `1c1a09136` on `fix-google-skills-helper-paths` (pushed; base `b9c94016e`, current origin/main).

- `coga/google-calendar` has a new "Resolving the helper directory" section that owns the recipe. Line 1 sets `dir` to `${COGA_COGA_OS_ROOT:-$(git rev-parse --show-toplevel)/coga}/skills/coga/google-calendar`. Line 2 is the `packaged_template_path` one-liner if `gcal.py` is absent there. It is followed by `pip install -r "$dir/requirements.txt"` and a call. Bullets cover override vs fallback, which `python` imports coga (uv/pipx tool venv), the cmd.exe double-quote form, and that the helper never imports coga, so pip targets the Python that runs it, by absolute path, from any cwd. This replaces the old "as in sandbox-clone" paragraph and folds in the `$COGA_COGA_OS_ROOT` override-only note. The Dependencies section points at it.
- `coga/gmail` restates the two resolution lines for `gmail` and links the owner for the interpreter/cmd.exe details. Its pip line uses `"$dir/requirements.txt"`.
- `coga/calendar-reminder` links the owner and keeps its call shapes. Its pip line is now `pip install -r /resolved/coga/google-calendar/requirements.txt` with the same Python as `gcal.py`.
- `tests/test_packaging.py` adds `RESOLVED_PLACEHOLDER`, `_resolved_placeholder_refs`/`_problems`, a real-tree test (asserting gcal/gmail/seed_local_config refs are found), and a tmp fixture test showing a dangling ref is reported while the dir form and `.../` shorthand are ignored.
- The snippet was smoke-run with the repo .venv: it resolved the packaged google-calendar dir, `gcal.py --help` ran, and the gmail fallback worked with a bogus `COGA_COGA_OS_ROOT`.
- The gcal.py/gmail.py docstrings were left unchanged. They already use the placeholder, and the test now guards them.
- For the open-pr step, the PR body should say this resolves Dream findings ks-28/ks-29 (do not edit the Dream ticket).
- Checkout note: this session started on the done ticket `refresh-v1-microkernel-readmes-after-retro` branch. It had no unique commits, and all dirt was already on origin/main (verified per path). I ran the manual return (restore + switch main) before branching.
- Code review: not run yet. `peer-review` is next.

## PR

```yaml
title: Give the Google skills a concrete helper-path resolution recipe
author: claude
author_evidence: >-
  Implement session ran as Claude (claude-opus-5-5) under coga megalaunch
  7300fd41-afa6-4de1-9acf-12b79f0b3049.
head: 1c1a091364182bd6290cdf4589ff7581fd6c1774
base: b9c94016e211bd261842edf614c6a97b18868913
depth: skim
rationale: >-
  Docs-only change to three packaged SKILL.md files plus one self-contained
  packaging test; read the google-calendar resolution section for the recipe
  and interpreter wording.
implementation: >-
  coga/google-calendar owns a copy-pasteable local-override-then-package
  resolution recipe with interpreter, pip-target and cmd.exe guidance;
  coga/gmail restates it in two lines and links the owner;
  coga/calendar-reminder links the owner. A packaging test fails when any
  /resolved/<ref>/<file> placeholder in packaged resources names an unshipped
  file.
deviations: >-
  gmail restates the two resolution lines (allowed by the ticket) rather than
  a single sentence, so its own skill name stays copy-pasteable.
limitations: >-
  Examples remain POSIX-shaped; only a cmd.exe quoting note is given. No
  Windows execution check (release-only tier).
files:
  src/coga/resources/templates/coga/bootstrap/skills/coga/google-calendar/SKILL.md: >-
    Owner of the helper-directory resolution recipe and pip/interpreter rules.
  src/coga/resources/templates/coga/bootstrap/skills/coga/gmail/SKILL.md: >-
    Restates the recipe for gmail and links the owner; pip line by absolute path.
  src/coga/resources/templates/coga/bootstrap/skills/coga/calendar-reminder/SKILL.md: >-
    Links the owner; keeps call shapes and a concrete pip line.
  tests/test_packaging.py: >-
    Locks every /resolved/<ref>/<file> placeholder to a shipped package file.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: >-
    Implement step; independent peer-review is the next workflow step.
checks:
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: 1c1a091364182bd6290cdf4589ff7581fd6c1774
    base: b9c94016e211bd261842edf614c6a97b18868913
    detail: >-
      5181 passed, 33 skipped. Ran on the working tree that was then committed
      unchanged (git diff --quiet HEAD verified).
  - command: .venv/bin/python -m pytest -q tests/test_packaging.py -k resolved
    status: passed
    head: 1c1a091364182bd6290cdf4589ff7581fd6c1774
    base: b9c94016e211bd261842edf614c6a97b18868913
    detail: 2 passed.
  - command: coga validate --json
    status: not-run
    detail: No validation, config, workflow or task-model behavior changed.
```
