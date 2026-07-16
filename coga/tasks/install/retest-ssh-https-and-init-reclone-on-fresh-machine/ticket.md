---
slug: install/retest-ssh-https-and-init-reclone-on-fresh-machine
title: Retest SSH/HTTPS clone + init re-clone on a fresh work machine
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
---

## Description

The SSH-vs-HTTPS fix (`relay-forces-https`) and configurable remote name
(`remote-default-origin`) both merged as done, yet Greg — an external user whose
machine clones GitHub over SSH — still hit HTTPS friction and was surprised that
`relay init` attempts to clone again (he set `RELAY_REPO_URL` to his local
checkout to get past it). Retest the full SSH-default onboarding path on a clean
work machine to confirm the merged fixes actually cover his case, and file
follow-ups for whatever still breaks — notably the init re-clone surprise.

## Context

Reported by Greg (#4). This is a verification ticket, not a re-implementation:
the relevant behavior already shipped via `relay-forces-https` (done) and
`remote-default-origin` (done), so the open question is whether those fixes hold
on a real SSH-default machine. Touchpoints to exercise: `RELAY_REPO_URL` /
`clone_upstream` in `src/relay/commands/update.py`, and source normalization in
`src/relay/skill_manager.py`. Sibling onboarding issues live in this `install/`
group.

**Retest 2026-07-08 (fresh-container, HTTPS path):** `COGA_REPO_URL` override
verified working (including a local-path value — Greg's workaround is a
sanctioned path now); code prefers an SSH coga remote when one exists; failed
clone rolls back atomically. Still open here: (a) the real SSH-default-machine
run this ticket asks for, and (b) the re-clone surprise itself, which
escalated — the clone vendors *main HEAD*, not the installed version, and is
slated for removal in `install/vendor-cli-from-installed-package-not-git-clone`.
If that ticket lands first, only the SSH-machine verification remains.

**Added 2026-07-15 (nick, launch prep):** while on the fresh machine, also
time the full path from `pip install` to first felt success (init → build →
first ticket → something visibly works). If it exceeds ~10 minutes or ends
at "installed, now what?", that's a launch blocker — file it against the
launch gates, not here. One measurement, no new scope.

<!-- coga:blackboard -->

## Plan (2026-07-16, implement step)

Verification ticket — expect no code change, so likely no branch/PR; if the
retest passes, close via the no-diff path with evidence below. Follow-ups for
anything that breaks get filed as new `install/` tickets, not fixed here.

Environment reality checks done up front:

- `FastJVM/coga` is now **public** — anonymous HTTPS clone works, so the
  remaining SSH question is machines that *rewrite* GitHub HTTPS→SSH
  (`url.insteadOf`), i.e. Greg's setup.
- This host has **no GitHub SSH key** (`Permission denied (publickey)`), so a
  positive real-GitHub SSH clone can't run from here without touching Nick's
  GitHub account (won't do unattended). Instead: fresh Docker container with a
  local git-over-SSH server (sshd + bare mirror of this repo) and the classic
  `url."<ssh>".insteadOf "https://github.com/FastJVM/coga"` rewrite — exercises
  the identical git transport path end-to-end.
- PyPI still only has **coga 0.0.1** (stale — `install/cut-release-to-realign-
  pypi-with-main` already tracks it), so the container installs from local main
  HEAD; timing measurement notes this caveat.
- `coga init` needs `--user` (scriptable), has no hard gh preflight, and every
  managed skill in the manifest is optional → init should survive a gh-less box
  with warnings.
- `install/vendor-cli-from-installed-package-not-git-clone` is still
  in_progress → the init re-clone still exists; verify its behavior but the fix
  belongs to that ticket.

Container scenarios:

- A. SSH-default machine where SSH works (Greg's case): insteadOf rewrite to
  local SSH mirror → `coga init` must succeed, clone must go over SSH
  (verified via sshd auth log).
- B. SSH-default machine where SSH auth fails: rewrite to real
  `git@github.com` with no key → init must fail loud, roll back atomically
  (no partial `coga/`), exit 2; judge message actionability (does it point at
  `COGA_REPO_URL`?).
- C. Greg's workaround: `COGA_REPO_URL=<local checkout path>` → init succeeds.
- D. Repo with an SSH `origin` pointing at FastJVM/coga → resolver prefers the
  SSH remote (output shows the SSH URL being cloned).
- E. Timing: `pip install` → `coga init` → first ticket → visible status; flag
  if >~10 min or dead-ends at "installed, now what?" (report against launch
  gates, per nick's 2026-07-15 note).

## Findings (2026-07-16, fresh python:3.12-slim container)

Test harness: scratchpad `ssh-retest/test.sh`; logs `run1–runN.log` there.

1. **`coga init` hard-fails on a machine without `gh`** — before any clone
   logic runs. `gh` is `required_at_init=True` in `src/coga/dependencies.py`
   (deliberate; the open question is `install/decide-whether-gh-stays-required-
   at-init`, so no new ticket). Message is clear and actionable ("install from
   https://cli.github.com"), and init leaves nothing behind. On a *truly* fresh
   dev box this is the first wall a new user hits — relevant input for the
   decide ticket and the launch gates.

With gh installed (unauthenticated — realistic fresh box), run3:

2. **Scenario A PASS — SSH-default machine, working SSH.** `coga init` in a
   fresh repo with the classic `url.<ssh>.insteadOf https://github.com/FastJVM/coga`
   rewrite: init exit 0 in 16s; sshd auth log shows the vendoring clone went
   over SSH; COGA_PIN sha == the SSH mirror's HEAD. coga hands git a plain
   HTTPS URL and git-level rewrites apply cleanly — Greg's machine shape works.
3. **Scenario B PASS — SSH-default machine, broken SSH auth.** Clone fails
   ("Host key verification failed"), exit 2, atomic rollback (no partial
   coga/), re-run possible. Gap: the error is raw git stderr with no
   `COGA_REPO_URL` escape-hatch hint — NOT filing a ticket since the clone
   itself is slated for removal (`install/vendor-cli-from-installed-package-
   not-git-clone`, in_progress); if that ticket is descoped, revisit the hint.
4. **Scenario C PASS — Greg's workaround.** `COGA_REPO_URL=<own local
   checkout>` init succeeds; pin records the local path + sha. Re-confirms the
   2026-07-08 result on this fresh box.
5. **Scenario E — timing well under the ~10-min gate.** venv + `pip install`
   (local main, warm network) 8s; `coga init` 16s (includes clone + vendored
   venv + skill deps); `coga create` + `coga status` <1s. Total pip→visible
   status ≈ 24s. Init ends with concrete next steps (PATH, coga.toml, `coga
   build`), not "now what?". Caveats: install was from local source because
   PyPI is stale at 0.0.1 (`install/cut-release-to-realign-pypi-with-main`),
   and `coga build`'s agent-CLI requirement is the known gap
   (`install/init-next-steps-should-mention-agent-cli-requireme`). No new
   launch-gate filing needed.
6. **NEW ISSUE (follow-up to file): loud raw git errors on every state change
   in a no-remote repo.** The exact repo init produces (`git init` → `coga
   init`, "push when ready") has no `origin`; `coga create` then prints
   `[git] sync failed: \`git push origin main\` failed: fatal: 'origin' does
   not appear to be a git repository…` twice per command. Non-fatal by design
   (`src/coga/git.py` GitError handler), but `git.py` already prints calm
   one-liners for "git disabled" and "not a repo" — "no remote named origin"
   deserves the same short notice instead of a scary fatal dump on a new
   user's first ticket.
7. **Scenario D PASS — SSH remote preference (clean rerun, run4).** Run3's D
   was a harness artifact: `git remote get-url` reports URLs *after* insteadOf
   rewriting, so the test's own rewrite hid the GitHub remote (plus a
   `| head -3` SIGPIPE → exit 141). Clean rerun: with `origin =
   git@github.com:FastJVM/coga.git`, init prints "Cloning
   git@github.com:FastJVM/coga.git (shallow)…" — resolver prefers the SSH
   remote — then fails on (expected, keyless) auth with clean rollback.
   Control: HTTPS `origin` → anonymous clone succeeds end-to-end, exit 0.
8. **Re-clone surprise confirmed live, with version-skew evidence.** Run4's
   HTTPS init pinned upstream `bec8660017ad` (GitHub main HEAD) while the
   installed CLI was built from local main `8664ab33cc74` — the vendored copy
   is *not* the version that ran init, exactly the escalation
   `install/vendor-cli-from-installed-package-not-git-clone` (in_progress) is
   fixing. Nothing new to file; that ticket's premise is re-confirmed.

## Already satisfied

Verification ticket — the work was the retest itself; it ran in this session
and produced no code change, so there is no branch, diff, or PR (per
code/implement's no-diff close path). Per-ask evidence:

- **"Retest the full SSH-default onboarding path on a clean work machine"** —
  done in a fresh `python:3.12-slim` container (harness + logs in scratchpad
  `ssh-retest/`, transcript excerpts in Findings 2–5 and 7): HTTPS→SSH
  `insteadOf` rewrite works (A), SSH remote preferred (D), `COGA_REPO_URL`
  local-path escape hatch works (C), failed clone rolls back atomically (B).
  Caveat recorded in Verdict: GitHub's own SSH key acceptance was stood in for
  by a local git-over-SSH server (no GitHub key on this host) — that link is
  user-side, not coga code.
- **"File follow-ups for whatever still breaks"** — filed
  `install/short-notice-instead-of-raw-git-error-when-sync-ha` (finding 6).
  The init re-clone surprise itself is already owned by
  `install/vendor-cli-from-installed-package-not-git-clone` (in_progress),
  now with fresh version-skew evidence (finding 8); gh-at-init observations
  (finding 1) feed the existing
  `install/decide-whether-gh-stays-required-at-init`.
- **Timing measurement (nick, 2026-07-15)** — pip→init→first ticket→visible
  status ≈ 24s, far under the ~10-min gate; no launch-gate filing (finding 5,
  with the PyPI-staleness and agent-CLI caveats already ticketed).

## Verdict

Greg's SSH-default onboarding path works on a fresh machine with the merged
fixes: git-level HTTPS→SSH rewrites apply (A), an SSH coga remote is preferred
(D), `COGA_REPO_URL` including a local path is a sanctioned escape hatch (C),
and a failed clone rolls back atomically with exit 2 (B). Residual caveat: the
run used a local git-over-SSH server as the GitHub stand-in because this host
has no GitHub SSH key; the only untested link is GitHub's own key acceptance,
which is user-side, not coga code. Timing gate: pip→init→first ticket→status
≈ 24s, no launch blocker. One follow-up filed (no-origin sync noise, finding
6); gh-at-init (finding 1) feeds the existing decide ticket.
