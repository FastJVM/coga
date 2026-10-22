---
name: coga-dev/internals/usage-pricing
description: Facts about Coga's usage records that any future dollar-cost price table must handle, verified while a cost proxy was scoped and set aside.
---

# Facts a future price table needs

Capture and the record schema are
[activity capture](../activity-capture/SKILL.md); the read contract is
[coga/usage](../../../coga/usage/SKILL.md).

No pricing is implemented. These facts about the records were verified while a
dollar-cost proxy was scoped and set aside; any price table must handle them
rather than rediscover them.

- **Claude cache writes mix two rates.** Claude transcripts carry
  `usage.cache_creation.{ephemeral_5m_input_tokens, ephemeral_1h_input_tokens}`,
  but `_parse_claude_session` keeps only the combined
  `cache_creation_input_tokens`, so a record cannot tell which write rate
  applied. Both TTLs occur in practice and the two rates differ, so no single
  rate is both exact and a guaranteed lower bound.
- **A Codex `cache_creation_input_tokens: null` means "no split exposed", not
  "no charge".** OpenAI charges cache writes on GPT-5.6-and-later models, and
  `_parse_codex_rollout` subtracts only cached-read tokens from input, so any
  writes stay inside the `input_tokens` bucket.
- **Context-length tiers are invisible.** Providers price long-context
  requests at higher tiers, and records do not say which tier applied.
- **A session's tokens go to its last model.** `_parse_claude_session` sums
  usage once per message but records only the last real model seen, so
  a session that switches models attributes all of its tokens to the final
  one.
