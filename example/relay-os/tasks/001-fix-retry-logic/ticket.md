---
title: Fix retry logic
status: active
mode: interactive
owner: marc
assignee: claude1
watchers:
  - pierre
workflow:
  name: code/with-review
  steps:
    - name: implement
      skill: infra/testing-conventions
    - name: pr
    - name: approve
      skill: process/approve
    - name: merge
step: 1 (implement)
contexts:
  - email/payment-flow
---

## Description

Stripe webhook retries are silently failing after the third attempt.
The retry backoff logic doesn't account for rate-limit responses (429).
Fix the backoff to respect Retry-After headers and add observability
so we know when retries are exhausted.

## Context

The retry logic lives in `lib/webhooks/retry.ts`. Current backoff is
fixed 1s/5s/30s — no awareness of rate limit headers. The Stripe
dashboard shows ~40 exhausted retries/day, mostly on billing-update.
Don't touch the idempotency layer — that's a separate task.
