# Fixture materialization for ticket 02

These are data inputs and two small ticket-owned script fixtures, not a trial
runner. Nothing here was launched while preparing ticket 01. The package
captures Coga production source revision in `../sources.json`; check out/install
that revision separately for trials. Keep this reviewed package available
outside the resettable trial tree. Verify its artifact hashes before use.

## Initial state and resets

Use an independent checkout at the exact absolute `render_root` from the
manifest, `/tmp/coga-prompt-trial-667707cc`, or rerender **both** forms at the
same alternative root and get approval of the changed hashes. Preparation may
have left a scratch rendering tree there; preserve/inspect it and create a
fresh isolated trial checkout rather than treating it as a ready trial repo.

Copy `common/` into the trial root, then a single case's `coga/` overlay. Copy
`configuration.toml` to the isolated root's `coga/coga.toml`; it is never copied
onto this source repository's configuration. The offline rendering used a
`Config` with the same root, user, agents and resource defaults, without loading
or changing either live config file. Disable telemetry in the isolated config
before the initial snapshot, and use no ambient production notification/secret
configuration. Record the effective config hash with each run.

Initialize a new local bare origin and a clean `main` with these exact fixture
files. Use fixed author identity/date when constructing the initial commit;
record its full OID. Create `trial/assist` at the same OID. No PR, merged work,
remote divergence or entry dirt exists in this fixture. Keep a separate pristine
snapshot **per case**; reset both local files/index and local-origin refs from
it for each arm/repetition, with no prior outputs, audit lines, sentinels or
agent memory. A different absolute prompt-file name is allowed transport
metadata and must be logged; the prompt bytes stay frozen.

The initial ticket is already `in_progress` at step 1 except `author-paused`
(`paused`) and `owner-assist` (step 2, owner-held). This is the agent entry
state for prompt trials, not a request to activate tickets in the real repo.
Test-side step admission/supervisor identity must be established identically
for both arms; merely invoking lifecycle CLI without its actual launch witness
would test an unrelated refusal. No test capability can grant lifecycle
authority to authoring or analysis. A disposable adapter, if needed for prompt
injection and trace capture, needs its scope reviewed in ticket 02.

`workflow-inline` and `input-attended` have a caller-supplied notice of clean
main; all work is routine state within Coga roots. `owner-assist` runs on the
prepared `trial/assist` branch and returns under launcher ownership. Other
interactive cases have no supplied checkout preparation; the agent must read
and follow the manual start checks. Fixture branches are setup facts, not
inferences the proposed assembler makes from workflow or procedure names.

For `script-handoff`, the ordinary case overlay is the **pre-script** state.
Run the real script phase once. `post-script/` is an expected composition-state
snapshot, not an extra overlay to copy before dispatch. Compare its ticket and
`prepared.txt` with the actual script result before injecting the prompt. The
script leaves the same step open; the agent must not rerun it. For the
deterministic control use its overlay and an isolated configuration with **no
agents**, trap any composition/CLI-lookup/skill-refresh call, and compare the
stdout/exit/trace under both nominal assembly selections. It has no prompt.

## External surfaces and prompt delivery

Route notifications to an isolated local receiver with a synthetic webhook,
configured only in the trial checkout. The default fixture disables Slack;
enable the local receiver for the stateless-completion case before taking its
pristine snapshot, without changing any prompt inputs. Require the real Slack
command to return success and the supervisor's completion signal to fire. Do
not post trial roll-ups or lifecycle notifications to a human channel. Ordinary
state publication uses the local bare origin. The fixtures need no credentials
or real PR. Do not bypass real completion checks with a mock that simply says
the task succeeded.

Interactive baseline/candidate files contain the full delivered prompt with a
fixed illustrative marker. At actual spawn replace only that UUID with a fresh
one in both arms and log delivered hashes/size; all UUIDs have equal length.
Do not append another marker or duplicate launch arguments. Authoring uses
discussion-template transport and the separate kickoff from `dialogues.json`;
other interactive forms use the same positional/template transport as their
baseline caller. `stateless-recurring` contains the actual JSON argument
suffix, including a spaced argument and a newline-bearing argument. Assert
their decoded values and boundaries are retained.

For autofix, `analysis-input.json` supplies the exact record/open-ticket list
for `build_prompt`. Prepare the listed open ticket under `coga/tasks/autofix/`
for the duplicate case so `open_autofix_tickets` yields that tuple; no other
open finding exists. Feed C1 bytes through a narrow prompt substitution at
`analyze_record`, keeping `build_analyze_command`, DEVNULL stdin, timeout,
stdout parsing and the real catch path. Record any caller record trimming;
these small records fit existing limits and should be untrimmed. The analyst
has no human script. Use the exact isolated tree as cwd for both forms and
detect writes as well as emitted commands.

The installed pinned package supplies the normal user-topic fallback library.
Resolved prompt resources, attached files and specifically cited behavior
topics have snapshots in `../sources/`; `sources.json` distinguishes original
Git paths from snapshot paths. No agent should read the reviewer-only expected
outcomes or the other arm's prompt during a run. Baseline sees the same source
tree as C1, but neither gets the label key or protocol's answer key.

After owner approval record executable/model/settings pins, package publication
revision and artifact-tree hash in the decision record. Record each run's
initial fixture commit and effective configuration hash alongside that package
revision. The protocol's tables and per-case `expected` fields are the outcome
oracle, fixed before any model sees its input.
