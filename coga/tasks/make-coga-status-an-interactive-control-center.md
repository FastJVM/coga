---
title: Make coga status an interactive control center
status: draft
owner: nicktoper
workflow: null
---

## Description

Turn `coga status` into an interactive control center for background work,
in the spirit of Claude Code's "agent view" (the screen you get by pressing
← in a session, which lists sessions as needs-input / working / completed).
Instead of agent view's flat session list, the screen shows the `coga status`
layout (tickets grouped by status, owner, agent, current step, age), and the
sessions Coga started appear next to the tickets they belong to.

**Why.** Today starting and tracking parallel work means running `coga ticket`
/ `coga launch` in separate terminals and checking `coga status` again and
again. Agent view showed how much easier this gets when one screen lists
everything and tells you which session needs you.

**What the operator should be able to do.** Items 1–4 are the v1 core. The
command bar (5) is welcome but optional: the rest is a real upgrade even if it
can't run from inside the control center.

1. **Browse.** Up/down arrows move a highlight across tickets. Enter on a
   draft/active ticket opens its `coga show` view (the full ticket), and from
   there the operator can launch it or run `coga ticket` on it. ← returns to
   the control center.
2. **Launch in the background.** `coga launch <slug>` and `coga ticket <slug>`
   start as background sessions. A launched ticket moves into a
   "Working"/"Launched" section. The operator can enter any session, interact
   (for example go through the whole `coga ticket` design interview until the
   ticket is launchable), and press ← to return.
3. **Attention bell.** Show both signals, marked differently: (a) live: a
   running session is waiting for the operator's input (bell next to it);
   (b) stored: a ticket is `blocked` in its file.
4. **Work a blocked ticket from the control center.** Enter on a `blocked`
   ticket shows its open blocker(s), and the operator can either (a) create a
   new ticket that resolves the block, or (b) enter a session and unblock it
   right there with the resolution (`coga unblock <slug> --answer "…"`). Both
   paths are needed.
5. **Command bar (optional).** A prompt line at the bottom where the operator
   types `coga create "<title>"`, `coga ticket <slug>`, `coga launch <slug>`;
   new tickets appear on the board live.

**Lifecycle (decided).** Sessions keep running when the operator quits the
control center or closes the terminal. Reopening `coga status` reattaches to
them and shows their live state.

**Known constraint.** Interactive commands (`coga ticket`, `coga launch`, the
`megalaunch --pick` picker) need a real terminal. A Claude background session
that tried to run megalaunch failed with "it needs a real terminal". So the
control center can't run these commands inside its own process or agent: each
one must get its own real session.

**Open questions for Nico.**

1. **Host the sessions ourselves, or use Claude's agent view?**
   (A) Coga hosts the sessions: each `claude`/`codex` session runs inside its
   own pseudo-terminal (`src/coga/repl_supervisor.py` already runs agent
   sessions this way). Claude Code hooks write a "needs input" marker into
   `.coga/` run records. Works with both agents and the state stays in visible
   files, but this partly rebuilds tmux/agent view.
   (B) Use agent view: `coga launch` starts each ticket as a named Claude
   background session, so the bell, enter and ← come for free, and Coga only
   puts its status layout inside agent view. Much less code, but Claude-only,
   and it's unverified whether agent view lets an outside tool show its own
   pane. Check that before choosing.
2. **Agent-led or a plain command line?** Should the command bar take literal
   `coga …` commands, or be an agent session that turns plain requests into
   commands? All the operator's examples are literal commands.
3. **Where it lives in the code.** Under `coga/extension-model`, a UI that
   consumes only stable CLI/filesystem interfaces (`coga status --json`, task
   files, `.coga/` run records) is normally an edge feature, not core. Decide
   whether it stays at the edge (e.g. `src/coga_edge/`) or earns a core home,
   and which contracts it needs (for example a machine-readable "session
   waiting for input" state).
4. **The live "needs input" signal.** How is it detected per agent (Claude
   Code Notification/Stop hooks, codex equivalent), and where is it recorded
   so it survives the control center quitting?
5. **v1 cut.** Confirm v1 = items 1–4, with the command bar (5) as a
   follow-up if it turns out hard.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
