---
title: Add browser skill for automating tasks (click, test scenarios)
status: draft
mode: interactive
owner: zach
human: zach
agent: zach
assignee: zach
skill: bootstrap/ticket
---

## Description

Add a browser-automation skill so agents can drive a real browser to
complete tasks: click buttons, fill forms, run end-to-end test
scenarios, scrape rendered content, and verify UI flows.

This is process knowledge (a `SKILL.md` under `relay-os/skills/`),
not domain context. The skill teaches agents *how* to drive the
browser — which tool to call, what selectors to prefer, when to
wait, how to capture screenshots/state for the blackboard.

## Open questions

- **Backend.** Playwright is the obvious pick (multi-browser,
  mature, headless + headed, good Python and Node bindings).
  Puppeteer and Selenium are alternatives. Default: Playwright.
- **Process model.** Does the skill assume a long-lived browser
  session per task, or one-shot scripts? Long-lived gives
  agents a REPL feel; one-shot is simpler and more reproducible.
- **Where the skill lives.** `relay-os/skills/browser/automate/`
  feels right. Could also have sibling skills for narrower jobs
  (e.g. `browser/run-e2e-scenario`, `browser/scrape-rendered-page`).
- **Auth.** Many real flows need a logged-in session (Brex,
  GitHub, internal apps). Pairs with the secrets-scoping ticket
  (`pass-secrets-to-skills-with-per-skill-scope`) — a browser
  skill needs cookies / API tokens / 2FA seeds for the target
  service.
- **Artifacts.** Screenshots, video, DOM snapshots, console logs
  on failure. Where do they live? Probably the task directory
  (`relay-os/tasks/<slug>/artifacts/`) so the human reviewing
  can see what happened.
- **Headless on agent machines vs headed for debugging.** Both
  modes; default headless.

## Context

- Skills format: `SKILL.md` with frontmatter `name` +
  `description`, body is markdown. Same format Claude Code and
  Codex use.
- Existing skills live in `relay-os/skills/`. Browser would be a
  new top-level area there.
- Pairs with: `pass-secrets-to-skills-with-per-skill-scope`
  (auth into the browser session must not leak across skills).
