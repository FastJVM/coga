# Coga
Coga is a tool built to amplify your thinking and learning.

It is a work system for humans and AI agents. It helps you focus on the parts of a problem that are still unclear, while agents automate the known parts. As you learn, you update the work. Coga carries those changes into the next agent sessions.

## One piece of work

An illustrative walkthrough; the file names are the ones Coga uses with its
default layout.

1. **Start from an incomplete idea.**
   `coga ticket "Weekly summary of failed payments"` opens a guided
   conversation. The AI asks what counts as failed, who reads the summary, and
   what done means, then writes the answers into a ticket,
   `coga/tasks/weekly-summary-of-failed-payments.md`: a Description, the
   knowledge it should use (say, the `payments/stripe` context), and a
   workflow of steps with an owner review.
2. **Direct the execution.** `coga launch weekly-summary-of-failed-payments`
   builds the prompt from that ticket, its attached contexts, the current
   step's instructions and the ticket's blackboard, then starts Claude Code or
   Codex. The agent does the step, notes its plan and findings on the
   blackboard in the same file, and hands off at your review.
   `coga launch <ticket> --prompt-report` shows what was assembled before
   anything runs.
3. **Inspect and correct.** You notice the summary counts charges that failed
   once and then succeeded on retry. You fix this week's result on the ticket,
   and you fix the reason: one line in
   `coga/contexts/payments/stripe/SKILL.md` — "a charge that succeeds on
   retry is not a failure" — committed like any other change.
4. **Carry it forward.** The next ticket that attaches `payments/stripe`
   is composed from the corrected file. Nothing was learned invisibly: the
   ticket, its blackboard, the context diff and the entries in `coga/log.md`
   are ordinary files you can read, review and revert.

Conversation, planning and execution are all part of this. Tickets, contexts,
skills, workflows, markdown and Git are how it works; the
[documentation](docs/README.md) explains each.

## Install and start

Coga needs Python 3.11+, Git, and an authenticated
[Claude Code](https://claude.com/claude-code) or
[Codex](https://github.com/openai/codex) CLI.

```sh
uv tool install coga            # or: python -m pip install coga
cd <your git repository>
coga init --user <your-name>
coga ticket "<what you want done>"
coga launch <ticket>
```

[Install](docs/contexts/coga/install/SKILL.md) covers setup, joining a
repository that already uses Coga, and troubleshooting.
[First task](docs/contexts/coga/first-task/SKILL.md) walks one ticket from
draft to reviewed result. A [95-second demo](https://www.youtube.com/watch?v=iwnewxJvRPc)
was recorded in July 2026; some command names may have changed since.

## Who it is for, and its limits

Coga is for small technical teams who already use CLI agents, are comfortable
with Git and the shell, and want to understand and correct the material their
agents work from. It fits when writing down how work should be done costs less
than supervising the same work indefinitely.

It is local, self-hosted and self-supported: no managed service, SLA, hosted
dashboard or zero-setup path. Workflows are linear sequences of steps; dynamic
orchestration belongs in an agent framework. Coga does not replace judgment: it
makes the points where you decide and correct explicit.

This is a field report. Coga runs the work that builds Coga at FastJVM, a
two-person company, and we build it around a thesis — that a two-person
technical team can produce the output of a ten-person team when agents do the
mechanizable work and humans specify, evaluate and correct — which is
[a bet, not a measured result](docs/contexts/product/vision/SKILL.md). One
dated observation: in the week ending 2026-07-05 the repository recorded
31 distinct agent-operated workstreams, counted per week rather than as
simultaneous processes ([method and limits](docs/evidence/velocity.md)).
Human time per shipped task has not been measured.

Managing prompts and instructions as files has close precedents. For dated
comparisons with other tools, see the [evidence pages](docs/evidence/) and the
[market landscape](docs/archive/market-landscape.md) record.

## Learn more

- [Documentation index](docs/README.md): start, understand, operate and
  develop.
- [Principles](docs/contexts/coga/principles/SKILL.md): the design
  constraints.
- [Contributing](CONTRIBUTING.md).

Coga is free software licensed under
[AGPL-3.0-or-later](LICENSE).

## Weekly telemetry

By default, operator recurring sweeps attempt a weekly aggregate usage snapshot
(counts, movement, bounded version/platform fields) to FastJVM’s US PostHog
project, shared with Multiply. This measures repos with active sweeps, not
installs: Coga installs no scheduler, and download/init send nothing. An opaque
repo ID is committed and shared by synced clones. No task content is sent.
The network peer sees source IP; project settings discard it and disable GeoIP.
Editable/source installations do not report.

Set `[telemetry] enabled = false` in shared or local config to stop sending and
its Slack receipt. Disabling stops sending; movement from the gap may appear in
the first count after re-enabling. See the [contract](docs/contexts/coga/telemetry/SKILL.md)
and [operator runbook](docs/contexts/coga/telemetry/operations/SKILL.md) for the boundary, verification and deletion.
