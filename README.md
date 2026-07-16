# Coga

Most tools say: don't think. Delegate the work, trust the platform, move on.
Coga says the opposite: don't don't think. Think better.

Coga is a small CLI and a markdown operating system for teams that run work with
coding agents. Tickets, context, workflows, skills, blackboards, and corrections
all live as plain files in your repo, versioned by Git and readable by the same
humans and agents. The agent does the mechanizable work; you keep judgment,
authority, and the right to change the machine directly.

## Install

Coga is published on PyPI as `coga` and requires Python 3.11+. Install the
isolated CLI with `uv`:

```sh
uv tool install coga
```

That puts `coga` on your `PATH`, in a virtualenv of its own, without touching
your system Python.

No `uv`? Create a virtualenv and install into it:

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

If a `pip` command above aborts with `Hashes are required in --require-hashes
mode` — or, for the editable install, `there is no single file to hash` — your
machine enables pip's hash-checking mode globally (`PIP_REQUIRE_HASHES=1` or
`require-hashes` in the pip config, common on managed work machines). Two
escape hatches:

- `uv tool install coga` — uv doesn't read pip's config, so it's unaffected.
- Disable hash checking for the one command by prefixing it, e.g.
  `PIP_REQUIRE_HASHES=0 pip install coga` or
  `PIP_REQUIRE_HASHES=0 pip install -e .`

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
```

This adds Coga's markdown OS under `coga/` in that same repository.

If you tried `coga init` in a separate empty directory, leave that directory
and run the commands above from your actual project's Git root instead. If the
empty directory is the start of a brand-new project, initialize Git there
before running Coga:

```sh
git init
coga init --user <your-name>
```

For command help, start with `coga --help`. For the deeper "why", read
[`docs/vision.md`](docs/vision.md). For the operating contract that Coga agents
actually load, read
[`coga/contexts/coga/principles/SKILL.md`](coga/contexts/coga/principles/SKILL.md).

### Joining an existing Coga repo

`coga init` is only for repos that don't have a `coga/` yet. If you cloned a
repo that already uses Coga, the shared config (`coga.toml`) came with the
clone, but `coga.local.toml` — the machine-local file holding your name — is
gitignored, so every clone creates its own. Read-only commands (`coga status`,
`coga show`, `coga validate`, `--help`) work without it; anything that creates
or moves work needs it. Create it next to `coga.toml`:

```sh
echo 'user = "<your-name>"' > coga/coga.local.toml
```

Coga never guesses your name (from git or `$USER`) — tickets reference people
by these names, and a guessed one that doesn't match fails silently.
`coga validate` will remind you with a warning until it's set.

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
