# Coga

Today’s AI coding tools turn programmers into full-time supervisors: prompt,
wait, review, repeat.

**Coga makes the machine work for you.** Decide what needs to be done, give
agents a batch of tasks, and return only when a decision needs your judgment.
Context, progress, and handoffs persist in Markdown and Git, so the work remains
inspectable, resumable, and yours.

## OpenAI Build Week

**95-second demo**

https://github.com/user-attachments/assets/b310bb0f-2312-4e19-98d4-cc65548b01c1

**[Watch on YouTube →](https://www.youtube.com/watch?v=iwnewxJvRPc)**

```text
You choose a batch
  → Coga gives each task its committed context and workflow
  → Codex and GPT-5.6 execute, test, and record progress
  → blockers and review gates wait for human judgment
  → you return when you are ready
```

### How we used Codex

Codex is both a first-class execution backend for Coga and a development partner
for the project. The committed [agent configuration](coga/coga.toml) teaches
Coga how to launch the local Codex CLI and deliver composed discussion prompts
as developer instructions. A task can name Codex as its agent, or an operator
can choose it for one launch:

```sh
coga launch <task> --agent codex
```

During Build Week, Codex was used through Coga to design, implement, test,
peer-review, and document changes. It worked from the same version-controlled
tickets, contexts, skills, workflows, and blackboards that Coga provides to any
supported coding agent.

### How we used GPT-5.6

GPT-5.6 was the reasoning and coding model inside those Codex sessions. The
Build Week runs used `gpt-5.6-sol` to understand large composed prompts, inspect
the repository, make changes, run tests, review other agents' work, and explain
decisions.

Coga does not depend on hidden conversational memory to ground the model. Each
launch reconstructs GPT-5.6's instructions from the files in the repository,
and Coga's append-only [task log](coga/log.md) records the task, agent, provider,
model, session, usage, and outcome. That makes GPT-5.6's inputs, sessions, and
results traceable and inspectable rather than a one-off chat.

## Install

Coga is published on PyPI as `coga` and requires Python 3.11+. The cleanest
install is an isolated CLI with [`uv`](https://docs.astral.sh/uv/):

```sh
uv tool install coga
```

No `uv`? Use a virtualenv:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install coga
```

If you explicitly want Coga in the current Python environment instead — no
virtualenv, no isolation — opt out with:

```sh
python3 -m pip install coga    # or: uv pip install --system coga
```

To develop Coga or test a branch from source, use a virtualenv there too:

```sh
git clone https://github.com/FastJVM/coga
cd coga
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

<details>
<summary>Installation fails because pip requires hashes?</summary>

If a `pip` command above aborts with `Hashes are required in --require-hashes
mode` — or, for the editable install, `there is no single file to hash` — your
machine enables pip's hash-checking mode globally (`PIP_REQUIRE_HASHES=1` or
`require-hashes` in the pip config, common on managed work machines). Two escape
hatches:

- `uv tool install coga` — uv doesn't read pip's config, so it's unaffected.
- Disable hash checking for the one command by prefixing it, e.g.
  `PIP_REQUIRE_HASHES=0 pip install coga` or
  `PIP_REQUIRE_HASHES=0 pip install -e .`

</details>

Then run:

```sh
coga --help
```

## Getting Started

Coga is adopted into an existing project, not set up in a separate workspace.
Install Git first; `coga init` requires it. The GitHub CLI
([`gh`](https://cli.github.com), then `gh auth login`) is recommended but not
required at init — PR workflows, the merged-ticket autoclose sweep, and managed
skill installs need it and will tell you when it's missing. You'll also need an
agent CLI — [Claude Code](https://claude.com/claude-code) or
[Codex](https://github.com/openai/codex) — installed and authenticated before
anything that launches an agent (`coga build`, `coga launch`, `coga ticket`)
can run; init itself works without one. Run init from the root of the Git
repository you want Coga to manage:

```sh
cd /path/to/your/project
coga init --user <your-name>
coga --help
```

Full install options, prerequisites, and a first-task walkthrough are in
**[docs/getting-started.md](docs/getting-started.md)**.

## Full docs →

Documentation lives under **[`docs/`](docs/README.md)**:

- **[Getting started](docs/getting-started.md)** — install, adopt Coga into a
  repo, and take a first task to a merged PR.
- **[Concepts](docs/concepts.md)** — tickets, blackboards, contexts vs. skills,
  workflows, the two state machines, agents vs. scripts.
- **[Command reference](docs/reference.md)** — every `coga` command and flag.
- **[Operations](docs/operations.md)** — notifications, recurring maintenance
  (Dream/REM), the digest, and secrets.
- **[Development](docs/development.md)** — working on Coga itself.

For the deeper "why," read **[docs/vision.md](docs/vision.md)**. For the
operating contract Coga agents actually load, read
[`coga/contexts/coga/principles/SKILL.md`](coga/contexts/coga/principles/SKILL.md).

## Key Values

**You own the system.** Coga is markdown, Python, Git, and the shell. No hosted
state, no hidden database, no plugin fence around the rules.

**Corrections compound.** When an agent gets something wrong, you edit the
context or workflow it used and commit the diff. The next run starts from the
corrected version.

**Agents do; humans think.** Coga routes mechanizable work to agents or scripts
so human attention stays on judgment: what matters, what changed, what was
wrong, what rule should exist next.

**Everything is inspectable.** Tasks keep blackboards. Contexts and skills are
files. Workflow changes are diffs. A missing or broken reference fails loud
instead of silently producing the wrong answer.

**No lock-in.** Coga coordinates the CLI agents you already use. Claude Code and
Codex work today, and the substrate is plain enough to swap vendors without
rewriting your company memory.
