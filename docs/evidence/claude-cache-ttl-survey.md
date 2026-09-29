# Claude cache-write TTL survey (2026-09-13)

Point-in-time evidence behind the cache-write fact in
[`coga/usage`](../contexts/coga/usage/SKILL.md#facts-a-future-price-table-needs).
It is one machine's measurement and can change with Claude Code releases or
workloads; re-measure before relying on the ratio.

## Method

Scanned the owner's machine's `~/.claude/projects/*/*.jsonl` Claude Code
transcripts on 2026-09-13 and counted assistant lines whose
`usage.cache_creation` carried a positive `ephemeral_1h_input_tokens` or a
positive `ephemeral_5m_input_tokens`. Recorded during the canceled
`define-the-api-equivalent-cost-proxy-and-price-tab` ticket.

## Result

- 70,171 assistant lines with a positive 1h cache-write count.
- 120 assistant lines with a positive 5m cache-write count.
- Pricing every write in this repository's usage records at the 1h rate
  instead of the 5m rate moved the estimated total from about $3,357 to about
  $3,655 (roughly 9%), at the list prices confirmed that day.

Claude Code wrote mostly with the 1h TTL on this machine, but 5m writes
occurred.
