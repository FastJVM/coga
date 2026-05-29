The blackboard is a notepad to be written to often as the human and agent works through a task.

## Purpose

This is a test of Relay's auto-relaunch chain (autoquit + supervisor respawn),
not a real feature. Writing `artifact.md` (one section per step) is just a
vehicle. The real deliverable is the **Relaunch test log** below: each step
records what the supervisor did at its boundary, and flags anything that
errored or looked wrong so Nick can pass it back later.

Workflow: `test/relaunch-chain` — a synthetic probe arranged
`draft (claude) → expand (claude) → peer-pass (codex) → human-check (human) →
finalize (claude)` so one run hits every boundary type once.

**RE-RUN on the NEW code (branch `feat/autorelaunch-across-agents`, commit
`0668b1a`).** The supervisor now auto-relaunches the next step's agent across
*agent rotations* too — `_harness_stop_reason` stops only on a **human
handoff** (assignee not a configured agent) or terminal state, and the launch
loop re-resolves the agent each step so it can spawn codex as a fresh PID.

Expected this run:

- draft → expand (claude → claude): **auto-relaunch**, fresh claude PID
- expand → peer-pass (claude → **codex**): **auto-relaunch**, fresh **codex** PID ← the new behavior, headline
- peer-pass → human-check (codex → human): **STOP** at the human gate (return to shell)
- (after the human bumps) finalize (claude): fresh launch → `relay mark done`

So one `relay launch test-autobump` should walk **claude → claude → codex on
its own** and only stop at `human-check`. Failure modes to catch: the
claude→codex hop NOT auto-relaunching (back to the old behavior); codex not
spawning as a fresh PID; or the chain failing to stop at the human step.

(The pre-fix run's entries are kept below under a divider — they document the
old stop-at-codex behavior for comparison.)

## Environment — RESOLVED during setup (2026-05-29)

The `relay` CLI was stale; it has been fixed. Details so it isn't re-litigated:

- **Which relay runs:** `which relay` → `~/.local/bin/relay` → symlink →
  `relay-os/.relay/bin/relay` → shebang `relay-os/.relay/.venv/bin/python3.12`.
  That venv now has relay installed **editable from this repo** (`pip install -e`
  from `/home/n/Code/relay`), so `import relay` resolves to
  `/home/n/Code/relay/src/relay` and future local edits are live. Works from
  conda `base` too (base has no relay module of its own; the shim uses the
  venv's 3.12 python). Conda `base` is Python 3.9, so `pip install` from base
  fails relay's `>=3.11` — irrelevant now, just don't install from base.
- **Two trees exist on this box (the "various installs"):**
  - `/home/n/Code/relay` **main** (HEAD `1631888`) — backs the PATH relay.
    Has autoquit **and** autorelaunch merged and refined: `#237` autorelaunch
    across same-assignee steps, `#238`, `#240`–`#242` (incl. the self-destruct
    fix). **This is the canonical, most-complete install — test with this.**
  - `/home/n/Code/claude/relay-autoquit-marker` branch
    `feat/autoquit-done-marker` (HEAD `eec88b6`) — backs the `relay-py312`
    conda env. A **local-only, unpushed, unmerged, older** feature branch
    missing `#240`–`#242`. Do **not** use it for this test.
- **Validation:** `relay validate` is clean for `other-agent` (the role set
  includes it in main). `test-autobump` shows only the benign
  `unfrozen-workflow` WARN (expected for a draft awaiting first launch).
- The `--version` banner reads a vendor pin (`read_pin`), not the running code,
  so its commit string is cosmetic — ignore it.

**Launch sequence (ordering matters — `relay mark active` freezes the workflow
snapshot, so do it only with the current CLI, which is now in place):**

1. `relay validate` — confirm clean (already is).
2. `relay mark active test-autobump` — a `draft` cannot be launched; this also
   freezes the snapshot and seeds `step: 1`.
3. `relay launch test-autobump` — from a **real TTY** (interactive auto-relaunch
   runs through the PTY watcher; headless/piped won't exercise teardown).

Also: `other-agent` needs **exactly two** `[agents.*]` configured or it raises
at *bump time* (the `expand → peer-pass` bump), one hop before codex would even
launch. Confirm both `[agents.claude]` and `[agents.codex]` exist and codex is
on PATH (`command -v codex`) — distinct from a missing-binary failure.

## Relaunch test log

_Each step appends a dated entry before it bumps. Record: which step/agent you
are; **whether you were auto-relaunched by the supervisor or hand-launched by a
human, and how you can tell** — quote the supervisor's own console lines
verbatim (its stop-reason e.g. `next step assignee changed: claude → codex`, or
its chain hint, and the `launched in <mode> mode` line in `log.md`); whether the
previous step tore down cleanly; whether `assignee:` resolved to the expected
agent; and any errors / surprises. Self-report of "was I relaunched" is the
least trustworthy datum — anchor on the console/log lines. (For `draft` the
"previous step teardown" question is N/A — it's first.)_

<!-- entries below -->

> ───────────────────────────────────────────────────────────────────────
> NEW-CODE RE-RUN entries go here (branch feat/autorelaunch-across-agents).
> Expect: draft→expand→peer-pass auto-relaunch (claude→claude→codex), stop
> at human-check. Append new dated entries above this line's run.
> ───────────────────────────────────────────────────────────────────────

### 2026-05-29 (14:33 run) — step 1: draft (claude) [NEW-CODE RE-RUN]

- **Code under test:** `feat/autorelaunch-across-agents` HEAD `0668b1a`
  ("launch: auto-relaunch across agent rotation, stop only at human handoffs").
  Confirmed via `git rev-parse --short HEAD` + `git branch --show-current` in
  `/home/n/Code/relay` (the canonical main tree backing the PATH `relay` shim).
- **Who:** I am the `draft` step, running as **claude** (ticket `step: 1
  (draft)`, `assignee: claude`, `agent: claude`; workflow step `draft` role
  `assignee: agent` → resolves to claude). First step in the chain.
- **Auto-relaunched or hand-launched?** Hand-launched by Nick — expected, since
  `draft` is the chain entry point with no predecessor to relaunch from. Ground
  truth, anchored not on self-report:
  - **Process tree (`ps`).** Exactly one `relay launch test-autobump` —
    PID **49155**, parent 4927 (a shell), alive ~48s. My REPL is
    `claude -n test autobump …` PID **49157**, **parent 49155** (the
    supervisor), alive ~47s. So the supervisor spawned me ~1s after it
    started — i.e. this is the supervisor's *first* loop iteration, the
    hand-launch, not an auto-relaunch (which would show the parent supervisor
    older than its child by a full prior-step lifetime, as the pre-fix
    `expand` entry below documents).
  - **`log.md` (verbatim), this run only:**
    - `2026-05-29 14:33 [human:nick] started (active → in_progress) via relay launch`
    - `2026-05-29 14:33 [human:nick] launched in interactive mode (assignee=claude, agent=claude)`
    The `started (active → in_progress) via relay launch` line fires only on
    the status transition (`launch.py:241`, gated on `status == "active"`),
    *outside* the chain loop — so it marks a fresh human invocation, not a
    loop iteration. Present here → fresh launch. (The `launched in … mode`
    line is hardcoded to `[human:nick]` on *every* loop iteration per
    `launch.py:323-325`, so it is NOT by itself evidence of a hand-launch —
    the `started …` line is the discriminator.)
- **Previous-step teardown:** N/A — `draft` is first. (The 11:30–11:34 lines
  above the `started 14:33` line belong to the **pre-fix run**, which was
  reset back to `active`/step 1 before this re-launch.)
- **Assignee resolution:** correct — `assignee: claude` for `draft`.
- **Preconditions verified for the whole chain (so a missing-codex failure
  later isn't conflated with a relaunch failure):** codex on PATH
  (`/home/n/.local/bin/codex`); **exactly two** `[agents.*]` configured —
  `[agents.claude]` (cli `claude`) and `[agents.codex]` (cli `codex`) in
  `relay-os/relay.toml` — so `other-agent` resolves cleanly to codex at the
  `expand→peer-pass` bump. `relay validate` clean per setup notes.
- **Errors / surprises:** none. Created `artifact.md` with the required
  `# Relay relaunch chain — test artifact` heading and `## 1. draft (claude)`
  section.
- **Watch next — THE HEADLINE (boundary 2→3 this run):** under the new code,
  `draft→expand` (claude→claude) auto-relaunches as before, but the *new*
  behavior is that `expand→peer-pass` (claude→**codex**, an assignee change)
  should ALSO **auto-relaunch** — spawning a fresh **codex** PID under the
  *same* supervisor (49155) with **no human launch** — and the chain should
  stop only at `peer-pass→human-check` (codex→nick, the human handoff). The
  `expand` and `peer-pass` entries must quote the supervisor's verbatim
  chain-hint / stop-reason lines as ground truth. Failure modes to flag:
  the claude→codex hop *stopping* (old behavior regressed in); codex not
  spawning as a fresh child PID of 49155; or the chain failing to stop at
  `human-check`.

### 2026-05-29 (14:33 run) — step 2: expand (claude) [NEW-CODE RE-RUN]

- **Who:** I am the `expand` step, running as **claude** (ticket `step: 2
  (expand)`, `assignee: claude`, `agent: claude`; workflow step `expand` role
  `assignee: agent` → resolves to claude). Second step in the chain.
- **Auto-relaunched or hand-launched? AUTO-RELAUNCHED by the supervisor —
  confirmed, and on the new code this is the same-assignee hop that was already
  expected to chain (the headline this run is the *next* hop, claude→codex).** I
  did not rely on self-report. Ground truth, strongest first:
  - **Process tree (decisive).** Live `ps` shows exactly **one** `relay launch
    test-autobump` — PID **49155** (parent 4927, a shell), alive **158s**. My
    expand REPL is `claude -n test autobump …` PID **49420**, **parent 49155**,
    alive only **30s**. So the *same* supervisor that ran `draft` spawned me
    ~128s into its life — that gap is draft's lifetime + bump + teardown. A
    hand-launch would have produced a *second* `relay launch test-autobump`
    process, or parented my REPL under a shell; neither exists. (The draft entry
    recorded the supervisor as 49155 with the draft REPL at 49157; the
    supervisor PID is unchanged, the child PID rotated 49157 → 49420.)
  - **`log.md` (verbatim), this run only:**
    - `2026-05-29 14:33 [human:nick] started (active → in_progress) via relay launch`
    - `2026-05-29 14:33 [human:nick] launched in interactive mode (assignee=claude, agent=claude)`
    - `2026-05-29 14:35 [agent:claude] advanced to step 2 (expand)`
    - `2026-05-29 14:35 [human:nick] launched in interactive mode (assignee=claude, agent=claude)`
  - **Interpretation, anchored to source.** The discriminator is the
    `started (active → in_progress) via relay launch` line (`launch.py:241`,
    gated on `status == "active"`, fired *outside* the chain loop). It appears
    exactly once — at 14:33, the human's draft launch — and is **absent** before
    my 14:35 launch line. So my launch was a supervisor loop iteration, not a
    fresh human invocation. The `launched in interactive mode … [human:nick]`
    line on the boundary is hardcoded to `human:<user>` on *every* iteration
    (`launch.py:323-325`), so it is NOT evidence of a hand-launch — exactly the
    trap the protocol warns about. Anchor on the `started` line, not that one.
- **Bump chain-hint at the 1→2 boundary.** Draft's bump log reads
  `advanced to step 2 (expand)` with **no `→ assigned to …` handoff suffix**.
  Per `bump.py`, that suffix is only written when the resolved next assignee
  differs from the current one; its absence is durable proof the resolved
  assignee stayed **claude → claude**, so `new_assignee is None` → the supervised
  bump treated it as a chain (not a handoff), and `_harness_stop_reason`
  (`launch.py:482`: `after.assignee != before.assignee` is false) returned None
  → the supervisor looped instead of stopping.
- **Previous-step (draft) teardown — clean.** `log.md` shows a single clean
  advance (one bump line 14:35, one launch line, no duplicate/missing transition
  post). No stray `claude -n test autobump` besides my own PID 49420 — draft's
  REPL (49157) is gone. `artifact.md` had exactly the `## 1. draft (claude)`
  section, no half-written/duplicated state. Draft must have exited 0 — a
  non-zero exit would have made the supervisor break the chain, so I wouldn't be
  running.
- **Assignee resolution:** correct — `assignee: claude` for `expand` (role
  `agent` under `agent: claude`).
- **Errors / surprises:** none. Behavior matched prediction exactly. (Other
  unrelated `relay launch` supervisors are live on this box —
  `xp1-sandbox-prep` PID 41587 — ignore them; only 49155 / its child 49420
  belong to this chain.)
- **Watch next — THE HEADLINE (boundary 2→3, `expand`→`peer-pass`,
  claude→codex):** on the NEW code this assignee change must ALSO
  **auto-relaunch** — spawning a fresh **codex** PID as a child of the *same*
  supervisor 49155, with no human launch. My bump line should this time carry a
  `→ assigned to codex` suffix (resolved assignee changes), but unlike the
  pre-fix run the supervisor should NOT stop — `_harness_stop_reason` now stops
  only on a human handoff (assignee not a configured agent) or terminal state.
  The `peer-pass` (codex) entry must quote the supervisor's verbatim
  chain-hint / stop-reason and confirm the fresh codex PID under 49155. Failure
  modes to flag: the claude→codex hop *stopping* (old behavior regressed in);
  codex not spawning as a fresh child PID of 49155; or the chain failing to stop
  later at `human-check`. Prerequisite reminder: `other-agent` needs exactly two
  `[agents.*]` or `resolve_other_agent` raises at *this* bump.

### 2026-05-29 (14:33 run) — step 3: peer-pass (codex) [NEW-CODE RE-RUN]

- **Who:** I am the `peer-pass` step, running as **codex** (ticket `step: 3
  (peer-pass)`, `assignee: codex`, `agent: claude`; workflow step `peer-pass`
  role `assignee: other-agent` → resolves to codex). Third step in the chain.
- **Auto-relaunched or hand-launched? AUTO-RELAUNCHED by the supervisor across
  the claude→codex agent rotation — this is the headline result for the new
  code, and it passed.** I did not rely on self-report. Ground truth:
  - **Process tree (decisive).** A host `ps` check showed the same supervisor
    from the prior entries still alive, and this codex process as its child:
    `49155    4927    01:04:48 SN+  relay` and
    `49785   49155    01:01:02 SNsl+ codex`. So codex PID **49785** was spawned
    under supervisor PID **49155**, not under a shell or a second
    `relay launch`. The child PID rotated across the run
    **49157 (draft claude) → 49420 (expand claude) → 49785 (peer-pass codex)**,
    while the supervisor stayed **49155**.
  - **Targeted process lookup.** `pgrep -af 'relay launch test-autobump'`
    showed exactly one actual Relay supervisor:
    `49155 /home/n/Code/relay/relay-os/.relay/.venv/bin/python3.12 /home/n/.local/bin/relay launch test-autobump`.
    `pgrep -af 'test autobump'` showed the current codex process PID **49785**
    and no live `claude -n test autobump` process for the previous step.
  - **`log.md` (verbatim), this run only:**
    - `2026-05-29 14:33 [human:nick] started (active → in_progress) via relay launch`
    - `2026-05-29 14:33 [human:nick] launched in interactive mode (assignee=claude, agent=claude)`
    - `2026-05-29 14:35 [agent:claude] advanced to step 2 (expand)`
    - `2026-05-29 14:35 [human:nick] launched in interactive mode (assignee=claude, agent=claude)`
    - `2026-05-29 14:37 [agent:claude] advanced to step 3 (peer-pass) → assigned to codex`
    - `2026-05-29 14:37 [human:nick] launched in interactive mode (assignee=codex, agent=codex)`
  - **Interpretation.** The 14:37 `launched in interactive mode
    (assignee=codex, agent=codex)` line proves the supervisor entered the codex
    step. Because a human can also launch an already-`in_progress` task without
    a new `started ... via relay launch` line, the log alone is not the
    discriminator here; the process tree is. The process tree shows the same
    supervisor 49155 spawned codex 49785, so this was auto-relaunch, not a
    human relaunch.
- **Bump chain-hint at the 2→3 boundary:** I cannot read the transient terminal
  scrollback from inside the relaunched codex process, so I cannot quote the
  actual console line printed during `expand`'s bump. Current source still has
  a stale hint condition in `src/relay/commands/bump.py`: it prints
  `Supervised launch: step done. Next step is a handoff — relay launch will stop and return to the caller.`
  whenever `new_assignee is not None`. For the new claude→codex behavior that
  hint is misleading if it appeared at 14:37: the durable process evidence
  shows the supervisor did **not** stop on the codex handoff. The supervisor
  logic in `src/relay/commands/launch.py` now stops only when the next assignee
  is not a configured agent.
- **Previous-step (expand) teardown — clean.** `log.md` shows a single clean
  advance at 14:37 and a single codex launch line, with no duplicate transition.
  `artifact.md` had exactly the `## 1. draft (claude)` and
  `## 2. expand (claude)` sections before I edited it. A search under
  `relay-os/.relay` found no `lock` / `test-autobump` files. The previous
  claude child is gone from the targeted process lookup, and codex 49785 is the
  only current test-autobump agent process I found.
- **Assignee resolution:** correct — `assignee: codex` for `peer-pass`
  (role `other-agent` under primary `agent: claude`, with exactly two agents
  configured).
- **Errors / surprises:** the headline behavior passed: the supervisor
  auto-relaunched across the claude→codex rotation. The surprise is the stale
  `bump.py` supervised hint described above; it still frames any resolved
  assignee change as a handoff even though the launch supervisor now chains
  configured-agent handoffs.
- **Watch next (boundary 3→4, `peer-pass`→`human-check`, codex→nick):** this
  should **STOP** at the human gate. My bump should advance to step 4 with a
  `→ assigned to nick` suffix, print the handoff hint, and the supervisor's stop
  reason should be `test-autobump: next step hands off to nick; returning to caller`.
  After bumping I should exit cleanly and not continue into `human-check`.

> ───────────────────────────────────────────────────────────────────────
>
> ▼▼▼ PRE-FIX RUN (old stop-at-codex behavior) — historical, for comparison ▼▼▼

### 2026-05-29 — step 1: draft (claude)

- **Who:** I am the `draft` step, running as **claude** (`assignee: claude`,
  `agent: claude`). First step in the chain.
- **Auto-relaunched or hand-launched?** Hand-launched by Nick — expected, since
  `draft` is the chain entry point with no predecessor to auto-relaunch from.
  Ground truth from `log.md` (verbatim):
  - `2026-05-29 11:30 [human:nick] started (active → in_progress) via relay launch`
  - `2026-05-29 11:30 [human:nick] launched in interactive mode (assignee=claude, agent=claude)`
  No supervisor stop-reason or chain-hint precedes me (nothing to stop from).
- **Previous-step teardown:** N/A — `draft` is first.
- **Assignee resolution:** `assignee: claude` resolved correctly to claude for
  this step (ticket frontmatter `step: 1 (draft)`, `assignee: claude`).
- **Environment sanity:** `which relay` → `~/.local/bin/relay` shim → main-tree
  editable venv (the canonical install per `## Environment`); `relay validate`
  is clean per setup notes. Ticket is `in_progress`.
- **Errors / surprises:** none in this step. Created `artifact.md` with the
  required heading and `## 1. draft (claude)` section.
- **Watch next (the headline):** boundary 1→2 (`draft`→`expand`, claude→claude,
  **same assignee**) must **auto-relaunch** `expand` with no human launch. After
  my `relay bump`, expect the supervisor's chain hint to say it will spawn a
  fresh agent session (not "will stop"). The `expand` step should record the
  supervisor's verbatim relaunch line as ground truth.

### 2026-05-29 — step 2: expand (claude)

- **Who:** I am the `expand` step, running as **claude** (frontmatter `step:
  2 (expand)`, `assignee: claude`, `agent: claude`; workflow step `expand`
  has role `assignee: agent` → resolves to claude).
- **Auto-relaunched or hand-launched? AUTO-RELAUNCHED by the supervisor —
  confirmed, this is the headline result and it PASSED.** I did *not* rely on
  self-report (the least-trustworthy datum). Ground truth, strongest first:
  - **Process tree (decisive).** A live `ps` at this step shows exactly one
    `relay launch test-autobump` process — PID **26586**, alive ~192s — and
    the expand REPL **`claude -n test autobump …` is PID 27147 whose parent
    is 26586**, alive ~138s. I am a child of the *same* supervisor process
    that ran `draft`; it spawned me ~54s after it started (draft's lifetime +
    bump + teardown). A hand-launch would have produced a *second*
    `relay launch test-autobump` process, or parented my REPL under a shell —
    neither exists. There is also no second `claude -n test autobump`, so no
    stray draft REPL.
  - **`log.md` (verbatim).** Exactly one chain-entry transition:
    - `2026-05-29 11:30 [human:nick] started (active → in_progress) via relay launch`
    Then the boundary:
    - `2026-05-29 11:31 [agent:claude] advanced to step 2 (expand)`
    - `2026-05-29 11:31 [human:nick] launched in interactive mode (assignee=claude, agent=claude)`
  - **Interpretation, anchored to source (don't be fooled by `[human:nick]`):**
    the `launched in interactive mode` line is attributed to `[human:nick]`
    **on every supervisor loop iteration**, because `launch.py:323-325`
    hardcodes the actor to `f"human:{cfg.current_user}"`. That attribution is
    therefore **NOT** evidence of a hand-launch — it is exactly the trap the
    evaluator review flagged. The real discriminator is the
    `started (active → in_progress) via relay launch` line, which fires only
    on the active→in_progress transition (`launch.py:241`, gated on
    `status == "active"`) — *outside* the `while True` chain loop, so once per
    chain. It appears once (line for draft) and is absent before my launch:
    consistent with a loop iteration, not a fresh invocation.
- **Bump chain-hint at the 1→2 boundary (source-confirmed).** `draft`'s bump
  log reads `advanced to step 2 (expand)` with **no `→ assigned to …`
  handoff suffix**. Per `bump.py:99-109`, that suffix appears only when the
  resolved next-step assignee differs from the current one; its absence is
  durable proof the resolved assignee stayed **claude → claude**, so
  `new_assignee is None` → `will_chain = True`, and the supervised bump
  printed (console, cyan; `bump.py:136-142`): *"Supervised launch: step done.
  relay launch will spawn a fresh agent session for the next step."* That, in
  turn, makes `_harness_stop_reason` return `None` at this boundary
  (`launch.py:482`: `after.assignee != before.assignee` is false), so the
  supervisor's loop chained instead of stopping.
- **Previous-step (draft) teardown — clean.** Single clean advance in `log.md`
  (one bump line, one launch line, no duplicate/missing Slack transition). No
  stray `claude -n test autobump` process besides me. No task lock file in
  `relay-os/.relay/` (the only `*lock*` hits are unrelated venv library
  source). `artifact.md` had exactly the `## 1. draft (claude)` section, no
  half-written/duplicated state. Draft must have exited code 0 — a non-zero
  exit would have made the supervisor `sys.exit` and break the chain
  (`launch.py:359-365`), so I wouldn't be running. The done-marker
  (`emit_done_marker`, `bump.py:154`) released draft's REPL cleanly.
- **Assignee resolution:** correct — `assignee: claude` for this step, as
  expected for the `expand` (role `agent`) step under `agent: claude`.
- **Errors / surprises:** none. Behavior matched the prediction exactly. Note
  for later steps: three *unrelated* `relay launch` supervisors are running
  concurrently on this box (`xp1-sandbox-prep`, `update-calendar-slack`) —
  ignore them; only PID 26586 / its child 27147 belong to this chain.
- **Watch next (boundary 2→3, `expand`→`peer-pass`, claude→codex):** this is
  an **assignee change** and must **STOP** — the supervised bump I'm about to
  run should print the *handoff* hint ("Next step is a handoff — relay launch
  will stop and return to the caller"), the bump log line should carry a
  `→ assigned to codex` suffix, and `_harness_stop_reason` should emit
  `test-autobump: next step assignee changed: claude → codex`. The supervisor
  (PID 26586) should then exit, and a human must `relay launch` codex.
  Prerequisite reminder: `other-agent` needs exactly two `[agents.*]` or it
  raises at *this* bump.

## Evaluator review

**Assessment of `test-autobump` (cold read)**

**First, a meta-finding: the blackboard's existing "Evaluator review" section is stale and describes a different setup.** It talks about `code/with-review`, an `implement` step, a no-op pytest vehicle, and contexts cited as `prompt.md:57-59` / `code/with-review.md:34-36`. None of that matches the files as they stand now (`test/relaunch-chain`, doc-writing vehicle, no pytest). The setup was substantially rewritten after that review was pasted in, and the rewrite fixed the central complaint that review raised (the old `code/with-review` had no same-assignee boundary and so couldn't test auto-relaunch at all). A cold agent reading the blackboard will hit a contradictory review that argues the design "can never exercise same-agent auto-relaunch" — which is false for the current workflow. That stale block should be deleted or clearly marked superseded, or it will actively mislead whoever picks this up. _[Resolved: the stale block was replaced by this review.]_

**Test design is sound and the boundary mapping is correct.** I traced the resolution against source. `_harness_stop_reason` (launch.py:482) compares `after.assignee != before.assignee`, and bump (commands/bump.py:106) only rewrites `assignee` when the *resolved nickname* differs from the current one — so the comparison is on resolved names, not role tokens. Resolution: `agent`→`claude` (ticket.agent), `other-agent`→`codex` (resolve_other_agent, the non-coder peer), `owner`→`nick`. So the actual resolved sequence is claude → claude → codex → nick → claude. That yields exactly: draft→expand same-name (chains), expand→peer-pass claude→codex (stops), peer-pass→human-check codex→nick (stops, also human-owned), human-check→finalize nick→claude (stops). One auto-relaunch, three stops, every boundary type once. The ticket's and workflow's "expected" columns match the code. A faithful agent grading observations against the workflow table will label correct behavior correctly — there is no built-in mislabel trap here (unlike the old version the stale review correctly flagged).

**The expectations are internally consistent and don't contradict the documented rule.** Both the ticket and the workflow body state the rule the same way the code implements it ("auto-relaunch only when resolved assignee unchanged; stop on change, human-owned, done/paused, panic/non-zero"). The skill-less-chains nuance is also correct against launch.py:478-485 (skills are no longer a stop condition). Good.

**The single biggest gap: the first launch will hard-fail, and the preconditions don't mention it.** The ticket is `status: draft`. launch.py:173 refuses to launch a draft outright: "Task is draft. Run `relay mark active` first." `relay mark active` is also what freezes the workflow snapshot and seeds `step: 1` (mark.py:103). The blackboard's "READ BEFORE LAUNCHING" section covers re-vendoring but never says to activate first. A human following the preconditions literally will run `relay launch` and immediately bounce. Add `relay mark active test-autobump` as an explicit precondition between re-vendoring and the first launch. (Also note: activation freezes the workflow into the ticket's snapshot, so re-vendoring must happen *before* activate, not just before launch — otherwise a stale snapshot could be frozen in. The ordering should be: re-vendor → `relay validate` → `relay mark active` → `relay launch`.) _[Resolved: preconditions section now orders re-vendor → validate → mark active → launch.]_

**Re-vendoring is the right call, and the reasoning is accurate.** I confirmed the working tree (`workflow.py:26-27`) includes `other-agent` in `VALID_ASSIGNEE_ROLES` and validate.py imports it from there, so a CLI vendored before #242 would indeed flag `peer-pass` as bad-shape and would also lack the autoquit/self-destruct fix this test exists to exercise. Launching against the stale CLI would test the wrong code. The instruction to re-vendor, re-run `relay validate`, and confirm the `other-agent` error clears is correct and sufficient on that axis.

**Other preconditions the setup misses or under-specifies:**
- **`relay mark active`** (above) — the hard blocker.
- **Exactly two `[agents.*]` and codex on PATH** is flagged in both ticket and blackboard, which is good. But note the failure shape is sharper than the ticket implies: `other-agent` needs *exactly two* agent types or `resolve_other_agent` raises at **bump time** (the `expand`→`peer-pass` bump), not at codex-launch time. So a misconfig there fails the chain one hop earlier than "codex missing." Worth a one-line distinction; the current text lumps both into "missing-codex." Also: `command -v codex` proves the binary exists but not that `[agents.codex]` is configured with a working `auto`/interactive invocation — the agent should also confirm the config, not just PATH.
- **Mode.** The ticket is `mode: interactive`. Auto-relaunch under a supervisor only does its thing through the PTY watcher / done-marker path in interactive mode (launch.py:339+). That's fine and is presumably intended, but the run must be driven from a real TTY; running it headless/piped will not exercise the same teardown path. Not stated anywhere. Worth a note since the whole point is observing teardown.

**Logging protocol is good — strong enough to diagnose each boundary.** It asks for the five right data points (which step/agent, auto- vs human-launched and *how you can tell*, prior-step teardown cleanliness, assignee-flip-as-expected, surprises), enumerates concrete not-ok shapes, and mandates `relay panic` with a reason rather than silent stop. The "how you can tell" requirement is the key one and it's present. One improvement: tell each step to record the supervisor's own console line. The supervisor emits an explicit stop reason (e.g. `next step assignee changed: claude → codex`) and bump emits the supervised hint ("Next step is a handoff — relay launch will stop" vs "will spawn a fresh agent session"). Those strings are ground truth for what the supervisor decided; capturing them verbatim in the log would let a human diagnose a boundary even if the agent's prose interpretation is wrong. Right now the protocol relies on the agent's inference of "was I auto-relaunched," which is exactly the thing under test and therefore the least trustworthy thing to rely on self-report for. Also, the auto-relaunched `expand` step writes its log entry *after* it's already running, so it can't directly observe whether a human typed `relay launch` between draft and itself — the only durable evidence is the launch log lines appended by launch.py:323 (`launched in ... mode`) and the supervisor's chain hint. Point `expand` at the task's `log.md` / console scrollback as the authority, not its own memory.

**Synthetic workflow shape is well-formed.** Five steps, each with a valid `assignee` role token from `VALID_ASSIGNEE_ROLES` (`agent`, `other-agent`, `owner` — no literal nicknames, which the validator rejects). Every agent step has an inline body section (`## draft`, `## expand`, `## peer-pass`, `## finalize`) supplying instructions, so the skill-less steps are not under-specified — that's the correct construction for the "skill-less steps still chain" path. The `human-check` step also has a body. No malformed step shape, no missing assignee, no duplicate names. The frontmatter `name: test/relaunch-chain` matches the ticket's `workflow:` ref. This is launch-ready structurally.

**First-step (`draft`) clarity for a cold agent: adequate once activated.** Exact filename (`artifact.md` in the task dir), exact headings, "throwaway prose, any neutral content," and a pointer to the logging protocol. The one ambiguity: the agent is told to log "before it bumps" but the protocol asks "did the *previous* step tear down cleanly" — for `draft` there is no previous step, so that question is N/A; the workflow doesn't say so. Minor, but a literal-minded agent may waste a beat. Scope overall is reasonable and appropriately minimal — no gold-plating, the deliverable is correctly framed as the observations, not the doc.

**Net:** The design is correct and the boundary logic checks out against source — this is a genuinely good probe of the relaunch chain, and a clear improvement over whatever the stale review was looking at. Three things to fix before launch, in priority order: (1) delete/supersede the stale "Evaluator review" block so it doesn't contradict the current design; (2) add `relay mark active test-autobump` as an explicit precondition, ordered after re-vendor/validate and before launch; (3) have each step capture the supervisor's verbatim stop-reason / chain-hint console lines rather than relying on self-reported "was I auto-relaunched." Secondary: note the interactive-TTY requirement, sharpen the `other-agent` failure-at-bump-time vs codex-missing distinction, and tell `draft` the prior-teardown question is N/A.
