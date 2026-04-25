---
# `relay create` writes most of this for you. This file shows what a
# ticket looks like once it's been scaffolded — useful as a reference
# when hand-editing or recovering.
title: Fix retry logic
status: active                # design | ready | active | paused | done | canceled | failed
mode: interactive             # interactive | auto | script
owner: marc                   # human accountable; stable for the task's life
assignee: claude1             # who's currently doing the work — human name or agent nickname
watchers:                     # optional — additional Slack @mentions
  - pierre
workflow:                     # frozen snapshot, written by `relay create --workflow <name>`
  name: code/with-review
  steps:
    - name: implement
      skill: infra/testing-conventions
    - name: pr
    - name: approve
    - name: merge
step: 1 (implement)           # only when `workflow:` is set
contexts:                     # domain knowledge attached to the ticket
  - email/payment-flow
---

## Description

Stripe webhook retries are silently failing after the third attempt.
The retry backoff logic doesn't account for rate-limit responses (429).
Fix the backoff to respect Retry-After headers and add observability so
we know when retries are exhausted.

## Context

The retry logic lives in `lib/webhooks/retry.ts`. Current backoff is
fixed 1s/5s/30s — no awareness of rate limit headers. The Stripe
dashboard shows ~40 exhausted retries/day, mostly on billing-update.
Don't touch the idempotency layer — that's a separate task.
