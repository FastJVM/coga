# Migrating from Relay to Coga

Relay was renamed to **Coga**. The change is mechanical but breaking — package,
command, on-disk dirs, and config file all change:

| Before | After |
|---|---|
| `relay` command / `relay-os` package | `coga` command / `coga` package |
| `relay-os/` workspace dir | `coga/` |
| `relay.toml` / `relay.local.toml` | `coga.toml` / `coga.local.toml` |
| `src/relay/` | `src/coga/` |
| `contexts/relay/*`, `skills/relay/*` | `contexts/coga/*`, `skills/coga/*` |
| `<!-- relay:blackboard -->` fence | `<!-- coga:blackboard -->` |
| `RELAY_REPO_URL` | `COGA_REPO_URL` |
| `github.com/FastJVM/relay` | `github.com/FastJVM/coga` |

There are **two independent migrations**: cut the **CLI** over on each machine,
and migrate each **host repo's** on-disk layout. Do the CLI cutover first.

---

## 1. CLI cutover (once per machine)

The old `relay` command breaks the moment its checkout is on the renamed `main`
(`src/relay` is gone, so it `ImportError`s). Get `coga` working before deleting
the old one.

```sh
cd <your coga checkout>

# 1. Get the renamed main
git remote set-url origin https://github.com/FastJVM/coga.git
git checkout main && git pull

# 2. Reinstall so the `coga` command exists.
#    In a venv:
.venv/bin/pip uninstall -y relay-os
.venv/bin/pip install -e .
#    (or a plain editable/pipx install, however you run the CLI today)

# 3. Make `coga` global (if you used a ~/.local/bin shim before)
ln -sf "$PWD/.venv/bin/coga" ~/.local/bin/coga
rm -f ~/.local/bin/relay              # retire the old shim
#    also delete any `relay()` function / `alias relay=` in your shell profile

# 4. Verify, then delete the stale workspace leftover
coga --version && coga validate && coga status
rm -rf relay-os/                       # old vendored CLI + symlinks; regenerated as coga/
```

> **Order matters.** Don't `relay launch`/`bump` after the merge with a
> pre-rename `relay` — it writes to `relay-os/` and resurrects a stray dir on the
> fresh `coga` main. Cut every host over before anyone runs the CLI again.

---

## 2. Host-repo migration (once per repo still on the old layout)

There is no migration script. For each repo that still has a `relay-os/` +
`relay.toml`, migrate the tracked layout by hand from a clean working tree and
review the diff before committing:

```sh
git status --short
git mv relay-os coga
git mv relay.toml coga.toml
mv relay.local.toml coga.local.toml       # if present; usually ignored
```

Then inspect and update the remaining local files:

- Rename local override namespaces if they exist:
  `coga/contexts/relay/` → `coga/contexts/coga/` and
  `coga/skills/relay/` → `coga/skills/coga/`.
- Replace task blackboard fences:
  `<!-- relay:blackboard -->` → `<!-- coga:blackboard -->`.
- In ticket YAML frontmatter only, replace context/skill refs such as
  `relay/<name>` with `coga/<name>`.
- In config and `.gitignore`, replace structural tokens such as
  `RELAY_REPO_URL`, `relay.local.toml`, and `relay-os` with the Coga spellings.
- Remove regenerated Relay-era support dirs if present:
  `coga/.relay/` and `coga/.agent-skills/`.

Do not rewrite prose, historical PR URLs, or source-path references in task
bodies just because they contain `relay`; GitHub redirects old repository URLs.
After the file moves and targeted edits:

```sh
pip install -e .        # (or pipx install --force .) — reinstall the CLI
coga validate && coga status
git add -A && git commit -m "Migrate relay -> coga"   # review the diff first
```

---

## Verification checklist

- [ ] `coga --version` works; `relay` is gone.
- [ ] `git ls-files | grep -c '^relay-os/'` returns `0`.
- [ ] `coga validate` is clean (bar pre-existing, unrelated findings).
- [ ] `python -m pytest` is green (with `coga` installed).
- [ ] No stray `relay-os/` reappears after the next launch/bump.

## Rollback

Everything is git. The old refs live in `git reflog` (~90 days) and the
pre-rename history is on `main`. To undo a host-repo migration before committing:
`git checkout -- . && git clean -fd` (or `git stash`).
