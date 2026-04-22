---
name: email/payment-flow
description: How payment-related tasks interact with Stripe webhooks, retries, and idempotency.
---

# Payment flow

## Retry behavior

- Stripe webhooks retry with exponential backoff: 1s, 5s, 30s, 5m, 30m, 2h.
- On 429, respect `Retry-After`. Do not add your own backoff on top.
- After six failed deliveries, Stripe stops retrying.

## Idempotency

- Every webhook handler must be idempotent — Stripe may deliver twice.
- Use `idempotency_key` on outgoing API calls (live in `lib/stripe/idempotent.py`).

## Edge cases

- Test clock events fire *immediately*; production clock events are queued.
- Fraudster chargebacks often arrive 45-60 days after the original charge.
