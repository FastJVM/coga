---
name: coga/recurring/verify
description: Fire a Coga recurring job for real inside a disposable clone — local bare remote, local Slack catcher, no vault, no internet — so a change to a template, its `ticket.py`, or the recurring wiring can be exercised before it merges. Covers building the sandbox, firing, what to check afterwards, the probes worth running, and what a sandbox firing does not prove.
---

# Verify a recurring job in a sandbox

The thing a reviewer wants to see run for a recurring change is a **firing**:
`coga recurring launch <name>` doing what the sweep would do. A real firing
posts to Slack, pushes state to the control branch, and records the serviced
period in `coga/log.md`, so it cannot be driven in the live checkout just to
prove an unmerged change works — on the control branch the template is still
the old one, so the launch does the old thing and burns the period.

"Sandbox" here is not a Coga feature. It is a throwaway clone this recipe
builds by hand, in which every side effect of a firing is aimed somewhere
harmless:

- **git** — `origin` is a local bare repo, so Coga's state pushes land on disk.
- **Slack** — both webhooks point at a local HTTP catcher that records each
  post to a file.
- **secrets** — every `op://` ref in the templates is rewritten to an `env:`
  ref with a placeholder value, so nothing reads the vault.
- **network** — a dead proxy, so any HTTP call that bypassed the catcher fails
  instead of reaching the internet.

Inside it the firing is genuine: the installed `coga`, the same admission and
lease checks, the same `ticket.py` copied into the period task, the same
`coga/log.md` lines and commits.

## What a sandbox firing proves — and what it does not

Read this before reporting a result. It is a manual procedure, not a test
suite: nothing runs it automatically, and the evidence is deleted at cleanup
unless you copy it into the PR.

It **does** exercise:

- admission, period-task creation, and the period lease;
- that a `ticket.py` is dispatched as a script and its exit code honoured;
- the shim's blackboard, history and `coga/log.md` writes;
- the period closing (or staying open on failure) and the commit/push of state;
- the exact text of every Slack post, captured in `posts.log`.

It does **not** exercise:

- **A job's happy path when it calls an external API.** The key is a
  placeholder and the network is dead, so the job's first real request fails.
  What you observe is the failure path. Cover the happy path by running the
  job's script against a recorded fixture, outside this sandbox.
- **Agent-backed templates** (no `ticket.py`). The launch opens an agent
  session, which cannot reach its model through the dead proxy.
- **The `secrets:` list itself.** The refs were rewritten; a changed ref is
  verified only against the real vault, with the token exported and the proxy
  dropped.
- **Delivery.** Nothing reaches Slack or GitHub; you see the payload and the
  local commits, not the post or the push.

A firing that did nothing can exit 0 in three ways described below — already
serviced, failed admission, an unpushed sandbox commit. Check the evidence
under *What to check after a firing*, never the exit code alone.

## Build the sandbox

Work from a scratch directory outside the repo. `$SRC` is the checkout
holding the change — the launch checkout on the feature branch, or a
sandbox clone.

**Commit in `$SRC` first.** `git clone --bare` carries committed history
only, so uncommitted work is absent from the sandbox — and the firing then
"passes" against the unchanged code.

```bash
S=/tmp/verify-sbx          # or the session scratchpad
SRC=/path/to/checkout-with-the-change
BRANCH=<branch>

rm -rf $S && mkdir -p $S
git clone -q --bare $SRC $S/remote.git
git -C $S/remote.git update-ref refs/heads/main refs/heads/$BRANCH
git clone -q $S/remote.git $S/repo
cd $S/repo && git checkout -q -B main origin/main
```

Two things matter here:

- **The remote is a local bare repo.** Coga syncs state on every launch and
  pushes it; pointing `origin` at a path keeps those pushes inside `$S`.
- **The branch is checked out as the control branch.** A recurring launch
  refuses to run from any branch but `[git].control_branch` (default `main`),
  and `--force` does not override it. Checking the branch out under that name
  is what gets past the gate. If the repo configures a different control
  branch, use that name in place of `main` throughout.

A fresh clone has no `coga/coga.local.toml` — it is gitignored. Write one that
carries your own operator name (the recurring `owner` gate compares it with
`owner` in `coga.toml`) and aims **both** webhooks at a local catcher:

```bash
# Pick a free port. Do not hardcode one: two sandboxes on one port collide.
PORT=$(python3 -c "import socket;s=socket.socket();s.bind(('127.0.0.1',0));print(s.getsockname()[1]);s.close()")
echo "PORT=$PORT" > $S/port.env          # re-read it in later shells

cat > $S/repo/coga/coga.local.toml <<EOF
$(grep -m1 '^user' $SRC/coga/coga.local.toml)
[notification.slack]
webhook = "http://127.0.0.1:$PORT/primary"
important_webhook = "http://127.0.0.1:$PORT/important"
EOF

cat > $S/catcher.py <<'EOF'
import http.server, sys
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get('content-length', 0))
        body = self.rfile.read(n).decode()
        with open(sys.argv[1], 'a') as f:
            f.write(f"=== POST {self.path}\n{body}\n")
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", int(sys.argv[2])), H).serve_forever()
EOF
nohup python3 $S/catcher.py $S/posts.log $PORT >/dev/null 2>&1 &
echo $! > $S/catcher.pid
sleep 1
ps -p "$(cat $S/catcher.pid)" >/dev/null \
  || { echo "catcher died on startup — is $PORT taken?"; exit 1; }
```

**Assert that the catcher is alive, as the last line above does.** A catcher
that loses the bind dies instantly, `echo $!` records the dead PID anyway, and
a smoke-test `curl` still answers `ok` — because the *other* process holding
the port answers it. The firing then posts into someone else's log and
`$S/posts.log` is simply missing.

Keep the PID. Do **not** clean up with `pkill -f catcher.py` — the pattern
matches the command line of the shell running it, so it kills its own caller.

The local file beats the committed config: `coga slack` re-reads config in
every child process, and `_resolve_notification_slack_important_webhook`
takes the local table over the shared one. So a script that posts through
`coga slack` reaches the catcher even when a real webhook sits in the
environment.

## Defuse the vault-backed ticket secrets

`build_launch_env` resolves a template's inline `secrets:` **before** the
status flip. Unsetting `OP_SERVICE_ACCOUNT_TOKEN` therefore does not make an
`op://`-backed firing safe — it makes it impossible: the launch fails in
preflight and nothing under test runs. Keeping the token is no better, since
`op read` then has to reach 1Password through the dead proxy.

Rewrite every `op://` ref in the clone to an `env:` ref instead.
`parse_inline_secrets` accepts `env:VAR` beside `op://`, and
`select_launch_secrets` fails loud on an unset var, so the preflight still runs
for real — it just resolves somewhere harmless. This writes `$S/sbx.env` with a
value for each: a secret whose name mentions `WEBHOOK` gets its own catcher
path, anything else a placeholder.

```bash
cd $S/repo
. $S/port.env
python3 - "$PORT" > $S/sbx.env <<'EOF'
import pathlib, re, sys
port = sys.argv[1]
ref = re.compile(r"^(\s*-?\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:\s*)op://\S+", re.M)
names = set()
for t in sorted(pathlib.Path("coga/recurring").glob("*/ticket.md")):
    text = t.read_text()
    new = ref.sub(lambda m: (names.add(m[2]), f"{m[1]}{m[2]}{m[3]}env:SBX_{m[2]}")[1], text)
    if new != text:
        t.write_text(new)
for n in sorted(names):
    v = f"http://127.0.0.1:{port}/secret/{n}" if "WEBHOOK" in n.upper() else "sandbox-not-a-real-key"
    print(f"SBX_{n}={v}")
EOF
cat $S/sbx.env
grep -nE '^\s*-?\s*[A-Za-z_][A-Za-z0-9_]*\s*:\s*op://' coga/recurring/*/ticket.md \
  && echo "op:// secret refs remain — fix before firing"
git commit -qam 'sandbox: point ticket secrets at local env'
git push -q origin main
```

**Commit and push — and push after every later sandbox commit.** Coga's state
sync sweeps a dirty tree into a commit of its own, and a local control branch
ahead of its own `origin` fails the `_same_period_lease` comparison at
admission. The launch then reports

```
recurring/<name> changed on the control branch during recurring admission; not launching.
```

and **exits 0**, leaving a `created (status=active)` line in `coga/log.md` and
no period task on disk. It reads like a no-op, not a refusal.

**Coga commits too, so push after a failed admission as well.** That refusal
leaves an unpushed coga-authored commit holding the log line, so the next
attempt fails identically and the sandbox looks wedged. Check that
`git rev-parse main origin/main` prints the same hash twice before every
launch. Not `--short`: since git 2.53 it takes a single revision, and the
two-revision form dies with `fatal: Needed a single revision`.

## Fire a job

**Clear this period first, or nothing fires.** A template whose period task is
already `done` prints `recurring/<name> is done; not launching.` and **exits
0** — a silent no-op that reads like a pass. On a repo whose sweep has run this
period, that is the normal state. Check with
`grep -m1 '^status:' coga/tasks/recurring/*/ticket.md`.

```bash
cd $S/repo
git rm -rq coga/tasks/recurring/<name> 2>/dev/null \
  && git commit -qm 'sandbox: drop serviced period' && git push -q origin main
```

`git rm` alone leaves the deletion staged, which is the admission-failure state
above, not a clean slate. Then fire:

```bash
cd $S/repo
. $S/port.env
env -u SLACK_WEBHOOK_URL -u IMPORTANT_WEBHOOK_URL -u OP_SERVICE_ACCOUNT_TOKEN \
    $(cat $S/sbx.env) \
    COGA_AUTOFIX=0 \
    HTTPS_PROXY=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9 \
    NO_PROXY=127.0.0.1,localhost \
  coga recurring launch <name>
```

Why each piece:

- **`-u SLACK_WEBHOOK_URL`, `-u IMPORTANT_WEBHOOK_URL`** — the local file
  already wins, but there is no reason to carry real webhooks into a run whose
  point is that it posts nowhere. Add any other webhook variable the repo's
  `coga.toml` reads through `env:`.
- **`-u OP_SERVICE_ACCOUNT_TOKEN`** — safe *only* after the rewrite above.
  With no `op://` ref left, nothing needs it, and its absence is the guarantee
  that no vault read happened.
- **`$(cat $S/sbx.env)`** — the values the rewritten refs resolve to.
- **`COGA_AUTOFIX=0`** — without it, the post-run autofix loop spawns an agent
  the dead proxy cannot reach and waits out `COGA_AUTOFIX_TIMEOUT` after every
  run. Drop it only when the autofix loop is itself under test.
- **the dead proxy** — a backstop, so any HTTP call that did not go through the
  catcher fails rather than reaching the internet. Keep `NO_PROXY` pointed at
  localhost or the catcher is unreachable too.

Derive which templates can fire headless rather than trusting a list:

```bash
for t in coga/recurring/[!_]*/; do
  [ -f "$t/ticket.py" ] && echo "script  $(basename $t)" || echo "agent   $(basename $t)"
done
```

## What to check after a firing

For a script-backed job:

- `coga/log.md` shows `launched as a script (ticket.py)` and
  `script exited with code 0`. The first line is what distinguishes a script
  firing from an agent session — if it is missing, the template was downgraded
  to an agent launch and a `ticket.py` change was never exercised.
- `git ls-files coga/tasks/recurring/<name>/ticket.py` is non-empty: the shim
  was copied into the period task and committed.
- The period task reached `status: done`, and `git status -s` is clean — Coga
  committed and pushed everything it wrote. A shim that exits 0 without
  advancing the step falls through to an agent phase (`run_script_chain` in
  `launch_script.py`), so a period left open after a zero exit is a finding.
- Any history or field write landed where the template says, and **only**
  there. For a job that keeps no history, diff against the branch tip and
  expect only the period task and `coga/log.md` to change.
- `$S/posts.log` holds the expected posts. It is usually the most useful
  capture for the PR — paste it, since cleanup deletes it.

## Probes worth running

- **Failure path.** Point `important_webhook` (or the job's API) at a dead port
  (`http://127.0.0.1:9/dead`), drop the period task, and fire again. Expect a
  non-zero exit, the period left open (`status: in_progress`), and a
  `script failed` post routed to the important webhook.
- **Retry.** Restore the webhook, **delete the period task**, and fire again.
  Expect a fresh create and a clean close. Deleting it is what makes this a
  retry of the *fixed* code: a period task owns a frozen copy of the shim, so a
  bare relaunch prints `already created for this period` and re-runs the copy
  under `coga/tasks/recurring/<name>/`, not the template you just edited.
- **The sweep continues past a failure.** Fire the whole sweep
  (`coga recurring`) with one template rigged to fail. A non-zero `ticket.py`
  is recorded and the remaining due templates still fire
  (`_launch_due_tasks` in `recurring_runner.py`); only
  `RETRY_WITHOUT_SWEEP_EXIT_CODE` (75) and codes >= 128 stop the run. Read the
  run report under `coga/.coga/recurring-runs/`.

## Rules that outlive the sandbox

- **Do not fire a job in the live repo to test a change that has not merged.**
- **Mutating `coga` commands run on the control branch,** never on a
  feature branch or in a sandbox clone. The sandbox is exempt because it is a disposable clone
  whose remote is a local path.
- **Commit hand edits before any mutating `coga` command** — state sync sweeps
  a dirty tree into its own commit.
- **Checkouts are LF.** If Coga reports "exact control ticket changed before
  guarded publication" or drops a task at admission, check
  `git ls-files --eol` for `w/crlf`.
- The real post-merge firing is a genuine post. Expect the duplicate post that
  re-running an already-serviced period produces.

## Cleanup

```bash
kill "$(cat $S/catcher.pid)"
rm -rf $S
```
