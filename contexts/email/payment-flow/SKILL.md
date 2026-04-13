---
name: email/payment-flow
description: Domain knowledge about how the email-tool handles Stripe webhooks, retries, idempotency, and rate-limit edge cases. Attach to tickets that touch billing or webhook processing.
---

# Payment flow — domain context

The email-tool processes Stripe webhooks for subscription events.
This document covers behavior that is NOT derivable from the code.

## Retry behavior

- Stripe itself retries webhooks with exponential backoff for up to 3
  days. Our handler must be idempotent.
- We deduplicate by `event.id` in the `processed_events` table. First
  hit wins; subsequent hits return 200 with no side effects.
- If our handler returns non-2xx, Stripe retries. If we return 2xx
  and silently drop the event, we never see it again. **Never return
  2xx on failure.**

## Rate limits

- Stripe's API returns 429 with a `Retry-After` header during bursts.
  Our retry layer in `lib/webhooks/retry.ts` does NOT currently respect
  `Retry-After` — it uses a fixed 1s/5s/30s backoff. This has caused
  exhausted-retry cascades around month-end billing events. Fixing
  this is Ticket 003.

## Fraudster timing patterns

- Fraud signups cluster on Sunday evenings (UTC). Payment retries for
  fraud-flagged accounts should NOT use exponential backoff because
  the pattern is bursty and the backoff hides the signal.
- The `fraud_hold` flag short-circuits retries — do not remove it
  without also updating the observability dashboard.

## What NOT to touch

- The `processed_events` idempotency layer. It works. Touching it
  risks double-processing.
- The webhook signature verification. Compliance-sensitive.
