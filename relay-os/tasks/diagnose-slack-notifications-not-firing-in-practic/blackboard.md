# Diagnosis

## TL;DR

The Slack code path is healthy. Notifications "don't fire in practice"
because **agents skip the `relay bump` (and `relay slack`/`relay panic`)
calls that are what actually post to Slack**. The base prompt does
mention these commands but frames them as soft list items — easy for an
agent finishing code work to overlook.

It is **not** a webhook, env-var, network, channel, or `slack.py`
HTTP-error problem.

## Evidence the code path works

- `$SLACK_WEBHOOK_URL` is set in nick's env.
- `relay.local.toml` has only `user = "nick"` — no `[slack]` table → enabled by default.
- Direct `curl -X POST $SLACK_WEBHOOK_URL` returns `HTTP 200` body `ok`.
- Calling `relay.slack.post(cfg, "...")` from a fresh Python invocation
  returned cleanly; nick confirmed the test message landed in Slack.
- `bump.py` calls `post()` after every code path. So when `bump` runs,
  Slack fires.

So when the path is exercised, it works. The miss is upstream: the path
isn't being exercised because agents don't call `bump`/`slack`/`panic`.

## Why agents skip it

In `src/relay/resources/prompt.md` (which `compose.py:37` loads into
every launched session):

- The Step transitions section presents `relay bump` as bullet 2 in a
  list ("1. Make sure the blackboard reflects... 2. Call `relay bump`").
- "Call `relay bump`" reads as advice, not as a non-optional ritual.
- The closing "What you don't do" list mentions things not to do, but
  doesn't explicitly call out "don't end the step without bumping."

For an agent deep in a task — pushing PR, replying to the human — it's
plausible to satisfy the user-facing work and stop without bumping. The
prompt doesn't make `bump` the unmistakable last step.

## Earlier wrong turn (kept for posterity)

Initially diagnosed a stale vendored `prompt.md` mentioning `relay slack`
and `bump --message` against a working tree that lacked them. That was
a stale-working-tree artifact: working tree was on the
`status-show-all-tasks` branch, which predated PR #67 (rename `feed` →
`slack`, add `bump --message`). After fast-forwarding main, vendored
copy and source match. Vendored install is **not** stale.

## Fix in this PR

Per nick: option (b). Reword `src/relay/resources/prompt.md` so:

1. The "Step transitions" section becomes "Finishing a step" with an
   explicit "step is not done until you have run `relay bump`" framing
   plus a Definition of Done.
2. The "What you don't do" list adds "Don't end the step without
   running `relay bump`. If blocked, `relay panic`."

## PR

https://github.com/FastJVM/relay/pull/69 — "Frame `relay bump` as a
required end-of-step ritual". Reviewer: nick.

## Out of scope — follow-up tickets to file

- **Fail-loud on Slack 4xx in `slack.py:post`.** `requests.post`
  doesn't raise on non-2xx; check `response.status_code` and treat
  non-2xx like `RequestException` (stderr + log + `typer.Exit(1)`).
  `validate.probe_slack` already classifies this correctly — same
  pattern would slot in cleanly. Defense in depth; not biting today
  but real.
- **A stop-hook / settings hook that nags Claude when it ends without
  bumping.** Behavior question; bigger than a prompt edit.

## Retro

status: processed
skill: retro/done-ticket
result: no-new-durable-knowledge
title: No new durable knowledge for diagnose-slack-notifications-not-firing-in-practic
