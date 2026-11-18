---
title: Warn when coga delete or coga retire leaves a live link to the deleted ticket
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
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
step: 2 (evaluate-design)
agent: claude
---

## Description

Follow-up from `make-retro-check-inbound-doc-links-before-deleting`. That
ticket made Retro (`retro/done-ticket`) search tracked files for a source
task's path before deleting it, and repoint live-tree references
(`blob/<control-branch>/` URLs, relative Markdown links, bare paths) to a
commit permalink. Two delete paths still skip that check:

- **`coga retire` on a `done` ticket** deletes it deterministically, with no
  Retro run.
- **An ordinary human `coga delete <task>`** has the same gap.

Either one can break navigation on main. That already happened once: a README
link to the deleted `document-the-remedy-for-a-bloated-blackboard-sibli`
ticket broke and had to be fixed in PR #1214.

The design step must decide, with reasons:

1. **Where the check lives.** It can run inside the shared `run_delete_task`
   or only in the command-level callers (`commands/delete.delete` and the
   retire `ticket.py`'s `_delete_done_task`). Check the microkernel rule,
   because `run_delete_task` has more consumers than these two paths (see
   Context).
2. **Warn or refuse.** Choose between a warning or a refusal, and add an
   override flag if refusal is chosen.
3. **Whether `coga retire` repoints links itself.** It can rewrite the links
   to a permalink, or only warn and point the operator at the fix.

The design must also say how every other caller of `run_delete_task` is
treated: either unchanged or covered by the check (see the Code map in
Context). It must also say what the check does when Git is disabled or
unavailable.

Done means:

- `coga delete` and the done-ticket path of `coga retire` both detect tracked
  live-tree references to the task before deleting it, and warn or refuse as
  the approved design says.
- Tests cover a referenced and an unreferenced task on both paths. They also
  cover the false-positive cases the design decides on: an existing commit
  permalink, a longer slug that shares the prefix, a test-fixture path, and a
  short leaf collision.
- Unattended deletions do not become blocked. This covers recurring
  replacement, Dream/Retro deleting period tickets, and Retro's direct
  `coga delete`.
- The owning docs describe the new behavior in the same PR.

### Decisions (with reasons)

1. **Where the check lives: a new shared core helper, called by the
   command-level callers. `run_delete_task` is unchanged.** The new module
   `src/coga/inbound_refs.py` has three real consumers: `commands/delete.delete`,
   the retire `ticket.py` `_delete_done_task`, and the `coga recurring promote`
   head. That passes the microkernel two-consumer bar. A retire `ticket.py`
   importing shared core infra is the sanctioned edge shape. Putting the scan
   inside `run_delete_task` would change recurring replacement, the
   `delete-task` recipe, and promote's library call all at once. Recurring
   replacement deletes and recreates the task at the same path, so the scan
   there would only produce noise.
2. **Warn, never refuse. No override flag.** A deterministic filter cannot
   reproduce Retro's per-hit judgment. Retro's direct `coga delete` and Dream's
   `coga delete recurring/<name>` both run unattended. A refusal would need an
   opt-out flag that every unattended caller passes, and the human path would
   be the only one left checked. Deletion is recoverable with `git restore`, and
   a broken link is cheap to fix once someone is told about it. The warning
   lists every live hit so the operator can repoint it.
3. **`coga retire` does not repoint links itself.** It warns and points to the
   fix, the same as `coga delete`. Repointing edits docs, and Retro sends that
   kind of edit through a reviewable PR. `coga retire` publishes only the task
   and the log (`git.publish` with `[ref.path, log_path(cfg)]`). Auto-repoint
   would need a new review path. It can be a follow-up ticket if the warning
   proves insufficient.
4. **Other callers of `run_delete_task`:**
   - Recurring replacement (`recurring.py`, the `replace_done` branch that
     calls `run_delete_task(cfg, existing)`) is **unchanged**. It recreates the
     task at the same path.
   - The `delete-task` recipe (`delete_task.run_delete_task_recipe`) is
     **unchanged**. It is a bare working-tree removal with a fixed
     argv/stdout/exit contract. Its one shipped automated user, Dream's
     cleanup-orphan-markers, works inside a reviewable PR.
   - `coga recurring promote` is **covered**. The task leaves its path
     permanently, so links to it break just as they do for a delete. The check
     runs in the command head (`commands/recurring.py` `promote`), not inside
     `recurring.promote_task`. The library call stays scan-free.
   - Period tasks (`ref.slug` starts with `recurring/`) are **skipped** by the
     helper itself. Every caller, including Dream's `coga delete
     recurring/<name>`, therefore gets no scan and no output for them. Their
     path is recreated every period, so a reference to it is not a broken
     link.
5. **When Git is disabled or unavailable, the check is skipped and the
   deletion proceeds.**
   - `cfg.git_enabled` false: skip silently. This is a deliberate opt-out, and
     it matches retire's `_cleanup_checkout`.
   - No work tree (`git.toplevel` returns `None`), `git` missing, or
     `git grep` fails (`GitError`): print one stderr line,
     `<prefix>: reference check skipped (<reason>)`, then continue. The check
     is advisory and must never stop a delete.

### Acceptance criteria

- [ ] `src/coga/inbound_refs.py` exports `find_live_references(cfg, ref)`. It
      returns a result holding either a list of hits (`path`, `line_no`,
      `line_text`) or a `skipped` reason. It never raises on Git failure, and
      it never mutates anything.
- [ ] `coga delete <task>` scans before calling `run_delete_task`. When there
      are live hits, it prints a yellow warning to stderr after the
      `deleted ...` line. The warning gives the hit count, one
      `  <path>:<line>: <trimmed line>` row per hit, and a one-line remedy.
      Exit code, deletion, and publication are unchanged (exit 0 when the
      delete succeeds). With no hits, output is byte-for-byte what it is today.
- [ ] `coga retire <done-task>` does the same in `_delete_done_task`, after
      the kept-checkout refusal check and before `run_delete_task`, with the
      prefix `Retire:`.
- [ ] `coga recurring promote <task>` does the same in its command head,
      scanning before `promote_task`.
- [ ] Classification rules. These are the false-positive policy, and each has
      a test:
  - The search set is tracked files, via `git grep -n -I -F -e <tasks-rel>/<slug>
    -e <leaf> -- . ':!<tasks-rel>' ':!<log-rel>'`. It runs from the Git root.
    `<tasks-rel>` is `paths.tasks_dir(cfg)` relative to the root, and
    `<log-rel>` is `paths.log_path(cfg)` relative to the root. Exit 1 (no
    match) means no hits and is not a failure.
  - Each hit line is tokenised into path-like runs. A token is **live** if
    either of these holds:
    - (a) after stripping any `#fragment`, it starts with `<tasks-rel>/<slug>`
      followed by a boundary (end, `/`, `.`, `#`, or any character outside
      `[A-Za-z0-9_-]`); or
    - (b) it contains `/`, and resolving it against the referring file's
      directory (`posixpath.normpath`) gives the task path (`<tasks-rel>/<slug>.md`
      for file form, `<tasks-rel>/<slug>` or anything under it for directory
      form).
  - A URL token is live only if its path segment after `/blob/<ref>/` or
    `/tree/<ref>/` meets (a) and `<ref>` is **not** a hex OID of 7 to 40
    characters. An OID ref is an existing commit permalink, which is safe.
    That applies to `blob/<control-branch>/` URLs and to any other branch
    name.
  - Not a reference:
    - a longer slug that shares the prefix (`<slug>-v2`), which fails the
      boundary check;
    - the same path inside another tree (`tests/fixtures/seeded-repo/coga/tasks/<slug>.md`
      does not start with `<tasks-rel>`, and resolving it relatively does not
      give the task path);
    - a bare leaf word, or a `/<leaf>` component of some other path (short leaf
      collision, for example a `recurring/<leaf>/ticket.md` hit when deleting a
      task whose leaf is `<leaf>`).
  - Excluded entirely: the tasks root (so links from other live tickets, and
    the task itself, are out of scope) and the log.
- [ ] Tests in `tests/test_commands.py` (delete) and `tests/test_retire.py`
      (done path):
  - Referenced, warning names the hit: the task is still deleted and the
    command exits 0.
  - Unreferenced, no warning: output is unchanged.
  - For delete, one test each for an OID permalink, a longer prefix slug, a
    fixture path, and a short leaf collision. Each produces no warning.
  - A `recurring/<name>` delete with a referencing doc produces no warning and
    no scan.
  - With Git disabled, the delete still succeeds and prints no warning.
  - Unit tests in a new `tests/test_inbound_refs.py` for the classifier.
    Prefer these for the matrix, and keep the CLI tests thin.
  - One promote test: referenced, with a warning.
  - Existing recurring-replacement and recipe tests pass unchanged.
- [ ] Docs updated in the same PR (see Proposed shape, step 5).
- [ ] `python -m pytest` and `coga validate --json` pass.

### Proposed shape

1. **`src/coga/inbound_refs.py`** (new, core).
   - `@dataclass(frozen=True) class InboundHit: path: str; line_no: int; text: str`
   - `@dataclass(frozen=True) class InboundScan: hits: tuple[InboundHit, ...]; skipped: str | None`
   - `find_live_references(cfg: Config, ref: TaskRef) -> InboundScan`:
     - Return an empty scan if `ref.slug.startswith("recurring/")` or
       `not cfg.git_enabled`.
     - Otherwise `git.toplevel(ref.ticket_path)` gives the root. If it is
       `None`, return `skipped="not a git work tree"`.
     - Compute the task's root-relative path (`ref.path` relative to the root,
       POSIX form).
     - Run `git.run_git(root, "grep", ...)`. Treat a `GitError` from exit 1 as
       no hits. `run_git` raises on any non-zero exit, so either inspect the
       exit through `git._run` or add a small `allow_exit` path. Choose the
       smaller change, and keep `git.py` edits minimal. Any other `GitError`
       becomes a `skipped` reason.
     - Classify each hit line with the rules above, using a pure function
       `classify_line(line, referrer, task_rel, tasks_rel, slug) -> bool` so
       the matrix is unit-testable without Git.
   - `format_warning(prefix: str, scan: InboundScan) -> str | None` renders
     the stderr text. All three heads share it.
     - Hits: the count line, the hit rows, then the remedy line: "Repoint each
       to a commit permalink of a commit that still contains the task; see
       coga/tickets/discovery to find it."
     - Skip: the single skip line.
2. **`src/coga/commands/delete.py`, `delete`**: call `find_live_references`
   after `resolve_task` and before `run_delete_task`. After echoing `output`,
   `typer.secho(..., fg=YELLOW, err=True)` the warning if there is one. Keep
   the head thin.
3. **Retire `ticket.py`, `_delete_done_task`**: the same, placed after the
   `refusal` bail and before `run_delete_task`, with the prefix `Retire:`.
   Update the `retire` docstring paragraph on done tickets.
4. **`src/coga/commands/recurring.py`, `promote`**: scan before calling
   `promote_task`, and print the warning after the success line.
5. **Docs** (one owner per fact, per `coga/knowledge`):
   - `coga/checkout-cleanup` "`coga delete <slug>`" section. This is the
     owner of delete's behaviour, which the `coga/cli` table routes there.
     State the advisory warning, its skip cases, and that the recipe does not
     scan.
   - `bootstrap/retire/ticket.md` step 5 ("Done: delete."). Add the same
     warning by reference to `coga/checkout-cleanup`, without restating the
     rules.
   - `coga/knowledge` "The same retirement breaks links" paragraph. It
     currently says `coga delete` removes a ticket without repairing inbound
     references. Correct it to "warns but does not repair".
   - `coga/tickets/discovery`, retired-task recovery. Make it the target the
     remedy line points to, and check that it already explains how to find a
     commit that still contains the task. If it does not, add one sentence.
   - The `retro/done-ticket` "Inbound references" section stays the owner of
     Retro's judgment rules. Add one sentence: `coga delete`'s deterministic
     warning may still list hits Retro judged to be non-references, and that
     is expected. Do not move Retro's rules into the helper's docs.
   - `bootstrap/delete-task` skill: no change, because the recipe behaviour is
     unchanged.
   - Update the `coga recurring promote` docs wherever its behaviour is owned
     (find the owner with `rg "recurring promote"`).
6. Order of work: write the helper and its unit tests first, then wire the
   three heads with their CLI tests, then the docs.

### Out of scope

- Refusing deletion, and any override flag.
- Automatic repointing by `coga retire` or `coga delete`. Leave it to a
  follow-up if warnings prove insufficient.
- Scanning inside `run_delete_task`, the `delete-task` recipe, or recurring
  replacement.
- Retro's own repoint flow and its judgment rules.
- Links from other live tickets (everything under the tasks root).
- The canceled-ticket path of `coga retire`.
- Computing and printing the exact permalink OID. The remedy points to the
  documented recovery recipe instead, because the right OID depends on
  publication, which happens after the scan.
- Repo-configurable search restrictions (see Open Questions).

## Context

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

### Code map (cite by symbol; verify against current tree)

- `delete_task.run_delete_task(cfg, ref)` is the single implementation of
  task removal. It takes `git.state_lock`, removes the directory form or the
  file form, and returns a report line. It raises only `DeleteTaskError`. It
  does no Git publication: callers own that.
- Its consumers, all of which must keep working:
  - `commands/delete.delete`, the Typer head. It calls `run_delete_task` and
    then `git.publish` with `"Ticket: <id-slug> — deleted"`. The
    `--keep-control-checkout` flag is Retro's isolated direct delete.
  - `delete_task.run_delete_task_recipe`, the `coga run delete-task`
    registered recipe. It does a bare working-tree removal with no publish.
  - `coga retire`, which is an edge `ticket.py`. The done path is
    `_delete_done_task` in
    `src/coga/resources/templates/coga/bootstrap/retire/ticket.py`. It calls
    `run_delete_task` and then publishes `"Ticket: <id-slug> — deleted
    (retire)"`. `src/coga/resources/retire.md` is only the body of the
    canceled-ticket Retro task. Canceled retire goes through Retro, which
    already handles inbound references, so it is out of scope.
  - Recurring replacement in `recurring.py`. It deletes and recreates a
    period task **at the same path** and runs unattended. A reference check
    inside `run_delete_task` would fire on every replacement, either as noise
    or as a blocked recurring job. That is the main argument against putting
    the check in the shared function without a caller opt-in.
  - `recurring.promote_task` (`coga recurring promote`). It copies a task into
    a recurring template and then removes it **permanently**, so it is a third
    path that can break links. The design must decide whether it gets the
    check.
  - Dream's Retro deletes recurring period tickets with
    `coga delete recurring/<name>`, unattended. See
    `src/coga/resources/templates/coga/recurring/dream/ticket.md`, which
    describes the period-ticket deletion. `tasks/recurring/` paths already get
    many tracked hits, but those paths are recreated every period, so they are
    not broken links. A naive check in `coga delete` would fire on nearly every
    period delete, and a refusal there would block Dream.
  - `coga run delete-task` is also used by Dream's cleanup-orphan-markers
    task.
  - Retro calls `coga delete` for a no-durable-knowledge source only after
    its agent has judged that no inbound references exist. Otherwise it routes
    the source through a reference-pin PR. That judgment drops cases that a
    plain `git grep` will still match:
    - longer slugs that share the prefix
    - fixture paths
    - existing commit permalinks, which contain the path
    - excluded trees
    - links from other live tickets

    So a deterministic refusal **would** block Retro's direct delete. The
    design must pick one of:
    - apply the same filters Retro applies
    - add a caller opt-out flag that Retro's documented `coga delete` calls
      pass
    - warn only

### Search rule to reuse (copied from `retro/done-ticket`, section "Inbound references")

Package skill:
`src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md`.
Search tracked files for both the task path relative to the Git root and its
final slug component. The leaf search catches relative links such as
`../tasks/<leaf>.md`. Exclude the task root and the log:

```bash
git grep -n -F -e '<tasks-root>/<slug>' -e '<task-leaf>' -- . ':!<tasks-root>' ':!<coga-os>/log.md'
```

When reading the hits:

- Honor search restrictions (for example `':!docs/archive'`).
- A longer slug that shares the prefix is not a reference, and neither is the
  same relative path inside a test fixture.
- Existing commit permalinks are already safe.
- Links from other live tickets are out of scope.

A deterministic check cannot "inspect each hit" the way Retro's agent does.
The design has to choose the false-positive policy. One option is to report
the hits and leave the judgment to the operator.

If links are repointed, the target is a commit permalink of the control-branch
tip that still contains the task (full OID). Retro sends repoints through a
reviewable PR, because `coga delete` publishes only the task and the log. If
`coga retire` repoints, the design must say how those doc edits get reviewed or
published.

### Microkernel rule (cited, not attached: `coga-dev/microkernel`, `docs/contexts/coga-dev/microkernel/SKILL.md`)

Read "The kernel tier and its edges" and "Open command placements".

- Core code needs at least 2 real consumers, or a reviewed co-versioned
  contract.
- `delete` is a kernel head because it is a thin head over the fixed
  `delete-task` recipe.
- Logic with one consumer belongs at the edge, for example in the retire
  `ticket.py`.
- A shared helper (such as a "find live references to a path" function called
  by both `coga delete` and retire) passes the two-consumer bar. Placing that
  logic inside `run_delete_task` changes every consumer listed above.

### Git disabled or unavailable

`git grep` needs Git. The design must say what happens when Git is disabled in
config, when there is no repo root, or when `git` is missing. Retire's
`_cleanup_checkout` already soft-skips in these cases. For publication and
soft-skip semantics, see `coga/state-publication` (cited, not attached).

### Docs to update in the same PR

- `coga/cli`, for `delete` and `retire` behavior.
- `bootstrap/delete-task` skill contract, if recipe behavior changes.
- `coga/tickets/discovery`, which covers retired-task recovery.
- The `retro/done-ticket` "Inbound references" section, if the shared helper
  becomes the canonical search.

Follow `coga/knowledge`: one owner per fact.

### Out of scope

- Changing Retro's own repoint flow.
- Links from other live tickets.
- The canceled-ticket path of `coga retire`, which Retro already covers.
- If the design picks warn-only, `coga retire` repointing links itself can go
  to a follow-up ticket instead of this one.
- Rewriting history: existing broken links are already fixed (PR #1214).

<!-- coga:blackboard -->

## Design (2026-11-17)

The spec lives under `## Description`. In short: the check is a warning only,
in a new `coga/inbound_refs.py` helper. Three heads call it: `delete`, retire's
done path, and `recurring promote`. `run_delete_task`, the recipe, and
recurring replacement are untouched. `recurring/*` period tasks are skipped.
When Git is disabled the check is skipped silently. When Git is unavailable it
prints one skip line, and the delete always proceeds.

Investigation notes:
- `git.run_git` raises `GitError` on any non-zero exit, and `git grep` exits 1
  when nothing matches. The implementer must handle that case. `git._run`
  returns a `CompletedProcess`.
- The `coga/cli` table routes `delete` to `coga/checkout-cleanup`, so that
  section owns delete's behaviour, not `coga/cli`. It routes `retire` to
  `bootstrap/retire/ticket.md`.
- `coga/knowledge` currently states "Retro and `coga delete` remove a ticket
  without repairing inbound references". That stays true, but it needs
  "warns" added.

## Open Questions

1. **Archive hits.** Should the scan exclude `docs/archive` or any other
   restricted tree? This repo's AGENTS.md keeps agents out of the archive, and
   Retro adds `':!docs/archive'`. The deterministic command has no config for
   search restrictions. The proposal does not exclude anything: archive links
   break too, and the output is only `path:line` rows. Excluding the archive
   would need either a hard-coded exclusion or a new config key, and a new
   key is out of scope here.
2. **Promote coverage.** The spec includes `coga recurring promote`, a third
   path that removes a task permanently. Confirm, or defer it to a
   follow-up.
3. **Warn-only vs. an interactive confirm.** A human-at-TTY `coga delete`
   could prompt before deleting when it finds hits. The proposal rejects that
   to keep one behaviour for every caller and to avoid any risk of an
   unattended hang. Confirm.
