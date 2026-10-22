---
name: coga-dev/internals/recurring-autofix
description: Implementation constraints in `src/coga/recurring_autofix.py` — why the run record is built rather than tee-captured, how analyst output is parsed and its headings demoted, the analyst's stdin, and the subscription auth retry.
---

# Recurring autofix internals

The user contract (run record, analyst verdicts, autofix tickets, knobs) is in
[coga/recurring/autofix](../../../coga/recurring/autofix/SKILL.md). This page
holds what a change to `src/coga/recurring_autofix.py` must keep.

## The record is built, not scraped

Tee-ing fd 1 to capture the sweep's console would make `isatty` false and
break every agent launch. The run record (`RunRecord`, rendered by
`write_run_log`) is therefore assembled from launch outcomes
(`outcome_for_ref`) and period blackboards (`blackboard_for_ref`), the only
durable per-run channel.

## Parsing the analyst

`parse_analysis` reads `ok`, `duplicate` or `problem`; anything unparseable is
a problem carrying the raw text. A problem body passes through
`demote_headings`, which shifts headings so the shallowest is `###` and leaves
fenced code untouched, because the body becomes the ticket's `## Description`
and a `##` would end that section in every launch prompt.

## Spawning the analyst

`build_analyze_command` has built-in one-shot argv for `claude` and `codex`;
other types need `[agents.<name>].analyze`. The analyst's stdin is `/dev/null`
because `codex exec` appends piped stdin to the prompt. `_labelled_streams`
reports both `stdout:` and `stderr:` tails on a non-zero exit.
`COGA_AUTOFIX_TIMEOUT` is one deadline (`_analyze_deadline`) shared by the
first call, the auth probe and any retry.

## Subscription auth retry

`_claude_subscription_fallback_env`: if an ambient `ANTHROPIC_API_KEY` call
fails for authentication or billing, and `claude auth status` (with the key
removed) confirms a first-party Pro, Max, Team or Enterprise login permitted by
local policy, the analyst makes one announced retry without the key. It never
applies to a custom `analyze` argv, `ANTHROPIC_BASE_URL` or
`ANTHROPIC_CUSTOM_HEADERS`, other CLIs, or unrelated failures.
