The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap decisions (interview)

- **Path: (1) keep simple, make reliable.** Recent commit `9b4b7c2`
  intentionally simplified Slack to a single `post(cfg, message)`. This
  ticket finishes that simple shape rather than re-elaborating with
  threading / channel routing / bot tokens.
- **Workspace/channel:** single workspace, single channel.
- **Mention style:** keep channel-style mention (no on-call rotation).
- **Workflow:** `code/with-review`. **Assignee:** `claude1`.
- **Shared webhook:** add an env-var fallback so multiple apps on the
  same machine can post through one Slack app config (option (a) from
  the discussion). A relay-hosted webhook proxy (option (b)) is
  explicitly deferred to a separate ticket.

## Evaluator review

Critique:

**Clarity for cold start.** Mostly good — current state, scope, and out-of-scope are crisp. But the ticket points to `src/relay/config.py` for `slack_webhook` without confirming the validate command exists; an agent will need to grep `python -m relay.validate` themselves. Minor.

**Workflow fit.** `code/with-review` is fine — this is straightforward implementation + PR. No mismatch.

**Contexts.** Reasonable defaults loaded. Missing: nothing skill-specific (e.g. a `code/test` or `python` skill if one exists). `current-direction` and `project-stage` may be noise here. Not a blocker.

**Scope.** Four sub-features (validate, env-var fallback, structured failure log + status integration, retry) is on the upper edge but each is small and they share the module. Reasonable as one ticket.

**Assumptions worth challenging:**

- **Validation approach is wrong.** Slack incoming webhooks reject GET/HEAD (405) and reject empty POSTs with `invalid_payload` (400/HTTP-200-with-error-body depending). A "dry POST" that returns 4xx is indistinguishable from a revoked URL. The realistic options are: (a) POST a no-op payload like `{"text": ""}` and accept that this *will* be visible if the webhook is live (Slack returns `no_text` error — useful as a liveness probe without posting visible content), or (b) only validate URL shape (`https://hooks.slack.com/services/...`) and DNS resolution. The ticket should pick one and stop hand-waving "HEAD or dry POST."

- **Failure-log path under-specified.** `relay-os/.slack-failures.log` lives inside the relay-os tree; is it gitignored? Per-project or global? "Have `relay status` note when failures are present" sounds cheap but `relay status` currently summarizes tasks — adding a cross-cutting health signal is a small architectural decision (where does it read from? when is the log rotated/cleared?) that the ticket waves at with "or a new one-liner." Pick one before launch.

- **"Simulated network failure" is not testable as written.** The acceptance criterion needs to specify the mechanism: monkeypatch `requests.post` to raise `ConnectionError`, or use `responses`/`requests-mock`. Without that, "simulated" is vibes.

**Stale/contradictory.** AC line 86 says "4xx-on-empty-post" — that contradicts the looser "HEAD or dry POST" in scope item 1. Pick one. AC line 91 says "or equivalent surface" which lets the agent dodge the `relay status` decision; tighten before launch.
