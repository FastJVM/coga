---
title: GitHub auth preflight and setup docs
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/principles
- relay/codebase
- relay/sync
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
step: 3 (open-pr)
---

## Description

V1 launch needs a narrow Git/GitHub auth readiness check so a new operator can
tell whether Relay's PR and git-sync paths will work on their machine. This is
not a Relay account system and not a token store.

Relay should keep the standard-tool boundary:

- git transport uses the user's configured remote (`cfg.git_remote`) through
  normal `git`, `ssh-agent`, and git credential helpers.
- GitHub PR/API paths use the `gh` CLI and the user's `gh auth login` state.
- Relay does not read `GITHUB_TOKEN`, store a GitHub PAT in `[secrets]`, or
  reimplement GitHub auth.

The existing `relay-forces-https` and `remote-default-origin` tickets cover
transport assumptions. This ticket covers the explicit setup/preflight surface
and docs so failures produce actionable setup hints instead of surprising an
agent at PR time.

## Acceptance Criteria

- [ ] Add an explicit GitHub readiness check, preferably
  `relay validate --check-github` to mirror `--check-slack`, or a similarly
  small setup/check helper if that fits the code better.
- [ ] The check is opt-in only. Normal read-only `relay validate`, `relay
  status`, and `relay show` must not hit the network or mutate state.
- [ ] The check uses `cfg.git_remote`; it does not hardcode `origin`.
- [ ] It verifies the configured remote exists with
  `git remote get-url <cfg.git_remote>` and reports a direct "set/fix your git
  remote" hint when missing.
- [ ] It performs a standard git reachability/auth probe only on the explicit
  check path and reports actionable SSH / credential-helper / HTTPS guidance
  without requiring a specific transport.
- [ ] It verifies `gh` is installed and authenticated with `gh auth status`;
  where useful, add a cheap PR/API probe that produces "run `gh auth login`"
  instead of a raw `gh` failure.
- [ ] README/setup docs list the required `git` and `gh` state, including
  `gh auth login`, non-`origin` remotes, SSH vs HTTPS expectations, and the new
  preflight command.
- [ ] Update the `code/open-pr` and `code/implement-and-pr` skills so agents
  probe `gh` before the PR step and write a clear blackboard blocker instead
  of improvising around missing auth.
- [ ] Tests mock subprocess calls for missing remote, missing `gh`, unauth'd
  `gh`, and success. Tests also prove the default validate path does not run
  the GitHub probe.
- [ ] No Relay-managed GitHub PAT store, `GITHUB_TOKEN` dependency, OAuth flow,
  or hosted account state is introduced.

## Proposed Shape

- Prefer a small helper in `src/relay/` that owns the subprocess probes and
  returns structured check results. Keep the Typer command thin.
- If implemented under `relay validate`, follow the existing `--check-slack`
  pattern: opt-in flag in `src/relay/commands/validate.py`, report issues in
  `src/relay/validate.py`, JSON-compatible issue output, and no network call
  unless the flag is set.
- Treat "not online" as a failed explicit check with a useful message, not as
  a reason to mutate config or cache credentials.
- Keep docs and skills transport-neutral: "use the remote configured in
  `[git].remote` / default `origin`; authenticate that remote through normal
  git/SSH/credential-helper setup."


## Context

Split from `authentication-system` during review. The umbrella decision was
that GitHub auth readiness is v1-blocking but should not be folded into the
already-active transport tickets, because those tickets are scoped to
hardcoded HTTPS / `origin` assumptions.
