<!-- Attachment of the `marketing/phase-0-audit` task. Not a ticket; moved out of
the blackboard on 2026-09-03 so composed launch prompts stay small. -->

## Narrative candidates

**Owner ruling (step 2, 2026-09-02): none of the candidates below are
publishable.** magicator, xpllm, and admin are confidential; the literal
text, slugs, and block reasons must not be quoted. Kept here as evidence of
the practice only. Post 1 has to draw its quotable examples from this repo
(`coga/log.md`: sweeps 2026-08-26 21:29 and 2026-09-02 13:44, plus the
blocker history here) or paraphrase shapes without repo detail.

Collected 2026-09-03 from the non-Coga repos (read-only). Log format is
`[slug] [agent:X] blocked: <reason>`; human tags vary (`nick`, `nicktoper`,
`zach`).


### 1. 2026-07-20, magicator, queued question (judgment) answered same day
`~/Code/magicator/coga/log.md` lines 350, 355, 365, 367.

```
2026-07-20 11:38 [staticization/capture-and-correlate-generated-classes] [agent:claude] blocked: Peer review: capture is incomplete and fails silently. Measured on the branch's own flags against -Xlog:class+load, a trivial probe generated 32 classes at runtime and definitions.tsv recorded 3 — no capture.failure, exit 0. Three misses are structural to caller-site instrumentation, not fixable by patching: [...] Your 2026-07-19 22:14 resolution made native JVMTI the fallback 'only if a definition path has no instrumentable Java caller' — three such paths are now proven, so I need your call: move interception to JVMTI ClassFileLoadHook, or accept a documented completeness caveat that weakens the closed-world proof. [...] Branch left green and unmodified at 5425220a4.

2026-07-20 14:11 [staticization/capture-and-correlate-generated-classes] [human:nick] unblocked (asks resolved, still in_progress): Decision: pivot the current ticket to exhaustive raw JVM definition capture through a startup native JVMTI ClassFileLoadHook; do not accept a completeness caveat. This ticket will prove that every in-scope class definition is captured, regardless of whether it can yet be classified, correlated, or rewritten. [...] The current caller-site instrumentation is not a capture authority and the existing branch is not mergeable as-is.

2026-07-20 15:08 [staticization/capture-and-correlate-generated-classes] [agent:codex] blocked: Stock HotSpot JDK 21/25 does not emit JVMTI ClassFileLoadHook for hidden classes even with the required all-class and early-class capabilities [...] Need Nick to choose platform-specific JVM_LookupDefineClass interception, a patched HotSpot hook, or explicitly narrow the hidden-class guarantee (the last conflicts with the prior no-caveat decision).

2026-07-20 15:56 [staticization/capture-and-correlate-generated-classes] [human:nick] unblocked (blocked → active): Décision humaine : conserver une JVM HotSpot standard et élargir l'autorité de capture au niveau natif. ClassFileLoadHook reste la source primaire pour les définitions qu'il observe; un proxy JVMTI NativeMethodBind du point terminal ClassLoader.defineClass0/JVM_LookupDefineClass capture les octets des hidden classes avant d'appeler l'implémentation originale. Aucun patch HotSpot ni retour à l'instrumentation de call sites Java. [...]
```

Why: the agent cites the human's own prior ruling, shows its condition is now met, asks a binary product question, and leaves the branch untouched. Four decisions in one day, all in the log, one of them in French.

### 2. 2026-07-18/19, magicator, queued question with a terse answer then launch
`~/Code/magicator/coga/log.md` lines 245, 286, 288, 289, 290.

```
2026-07-18 15:46 [staticization/dynamic-class-identity-key] [agent:codex] blocked: Shape-input proposal ready for review — see '## Proposal — shape inputs' on the blackboard. Derived from JDK 21 source [...]; empirical byte-diffing was impossible because -Djdk.internal.lambda.dumpProxyClasses is a no-op on JDK 21/22/25. Four decisions needed before code: (1) classData is non-null for ORDINARY lambdas (useImplMethodHandle), so 'reject non-null classData' would abort legitimate lambdas — proposal is to instrument LambdaMetafactory above ClassDefiner and reject only unattributed hidden definitions; (2) proxy bytes embed a JVM-global $ProxyN counter so identical inputs give different bytes across runs, which false-positives the same-key/different-artifact integrity check — proposal is a name-only normalization of the proxy's own name, which is a sliver of the rejected canonicalizer and so needs your explicit approval, vs exempting proxies from byte-equality; (3) confirm the per-mechanism field lists in the proposal table; (4) CDS can substitute an archived lambda class — proposal is to pin CDS off for capture runs and assert it. Also FYI, a live defect on main: lambda names have no counter [...] so #804's name-keyed CapturedClassStore collides and silently overwrites.

2026-07-19 12:43 [bootstrap/orient] [human:nick] launched (assignee=claude, agent=claude)
2026-07-19 12:47 [staticization/dynamic-class-identity-key] [human:nick] unblocked (blocked → active): 1) ok but you need to test it extensibley 2) we could canonicalize and link name to class would that fix it? 3) show it to me 4) this didn't really work check the POC result
2026-07-19 12:49 [staticization/dynamic-class-identity-key] [human:nick] started (active → in_progress) via coga launch
2026-07-19 12:49 [staticization/dynamic-class-identity-key] [human:nick] launched (assignee=codex, agent=codex)
```

Why: the agent asks approval for "a sliver of the rejected canonicalizer" rather than assuming. The human orients at 12:43, answers four numbered points with typos at 12:47, launches at 12:49. Answer, review, launch in six minutes.

### 3. 2026-07-30, xpllm, morning sequence with a megalaunch tail
`~/Code/xpllm/coga/log.md` lines 1113 to 1141 (preceding block at line 1107).

```
2026-07-29 17:55 [sliceworldpoc/03-test-luindex-large-slice] [agent:codex] blocked: Manifest-pinned perfo-isolated/home4 is continuously owned by an external multi-cell bench10 campaign (currently bench10-xalan-codeonly-a3n-oc-gpt56-5m); zero Luindex attempts were consumed. Retry after .xp1-runner.lock remains free for at least 20 seconds without changing the frozen home or payload.

2026-07-30 07:50 [sliceworldpoc/04-test-spark-catalyst-codegen-slice] [human:nick] task done — Recorded the Spark Catalyst codegen-slice n=1 outcome.
2026-07-30 07:50 [sliceworldpoc/05-test-sunflow-engine-slice] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-30 09:16 [sliceworldpoc/05-test-sunflow-engine-slice] [human:nick] task done — Banked the Sunflow V1/V2/V3 n=1 screen.
2026-07-30 09:16 [sliceworldpoc/06-synthesize-the-n-1-results] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-30 09:17 [sliceworldpoc/06-synthesize-the-n-1-results] [agent:codex] blocked: Waiting on sliceworldpoc/03-test-luindex-large-slice: it remains blocked with zero paid cells consumed and no research/sliceworldpoc/luindex/results-n1.json; complete that workload to a terminal recorded outcome before four-result synthesis.
2026-07-30 10:04 [sliceworldpoc/03-test-luindex-large-slice] [human:nick] unblocked (blocked → active): fixed!
2026-07-30 10:04 [sliceworldpoc/03-test-luindex-large-slice] [human:nick] launched (assignee=codex, agent=codex)
2026-07-30 10:07 [recurring/autoclose-merged] [human:nick] launched (assignee=claude, agent=claude)
2026-07-30 10:08 [recurring/digest] [human:nick] launched (assignee=claude, agent=claude)
2026-07-30 12:19 [sliceworldpoc/03-test-luindex-large-slice] [human:nick] task done — Banked the Luindex V1/V2/V3 n=1 screen.
2026-07-30 12:27 [sliceworldpoc/06-synthesize-the-n-1-results] [human:nick] unblocked (blocked → active): Dependency satisfied: sliceworldpoc/03-test-luindex-large-slice reached a terminal 'done' outcome and research/sliceworldpoc/luindex/results-n1.json now exists. All four workloads have recorded results-n1.json files (xalan, luindex, spark-catalyst, sunflow). Spark Catalyst's is a recorded scorer-casualty outcome with null scores — synthesize it as an invalid/unmeasured cell, do not rerun it.
2026-07-30 15:03 [sliceworldpoc/06-synthesize-the-n-1-results] [human:nick] task done — Synthesized the sliceworldpoc n=1 results and n=5 recommendation.
```

Why: a real morning. The previous afternoon's sweep rolls into 07:50, the synthesis agent refuses to synthesize three of four results, the human writes "fixed!" at 10:04 and relaunches, runs the recurring jobs, and the chain is unblocked by lunch and done by 15:03.

### 4. 2026-07-24, magicator, queued question that refuses to design unattended
`~/Code/magicator/coga/log.md` line 635 (siblings at 628 to 643).

```
2026-07-24 21:30 [magicator/observation-loop-framework] [agent:claude] blocked: Do not launch the agent design step. Owner is designing this loop with the agent in conversation, not via an unattended design run: the open decisions are the probe contract, the typed observation shape replacing the stringly-typed map, convergence semantics, run-loop ownership, and unification of the bytecode and native collector channels. Those are owner architecture calls. Unblock only when the joint design is done and the ticket list is being written.

2026-07-24 21:29 [staticization/replay-named-generated-definitions] [agent:claude] blocked: Blocked behind staticization/inject-and-rewire, which is itself blocked on magicator/observation-loop-framework. This ticket reuses the injector's materializer and layout writer and cannot start before they exist. Do not fork them.
```

Why: the cleanest statement of the thesis. The agent lists five architecture decisions and says they are not its to make. Six sibling tickets self-blocked within four minutes (21:29 to 21:34), one ending "Do not fork them."

### 5. 2026-07-05, xpllm, queued question with a stated default
`~/Code/xpllm/coga/log.md` line 265.

```
2026-07-05 17:33 [benchmark/run-the-benchmark-baseline] [agent:claude] blocked: zxing baseline complete as the reference workload (committed 4da725a: selftest correct ~1.0x, preflight clean, A/A floor n=3 [0.985/0.990/1.011], JFR decode-dominant 100% app-code). Before replicating to the other 4 DaCapo workloads, need 2 decisions (large 4-5x rework cost each; details on blackboard): (1) SHAPE: zxing isolates the decode hot path via a pre-encoded pool because the faithful round-trip profiled ENCODE-dominant — keep 'isolate the profiled hot path' for the rest, or build faithful whole-workload round-trips? (2) SOURCING: I vendored CURRENT upstream zxing 3.5.3, not DaCapo's old bundled version — use current maintained upstream for all 5 (avrora/sunflow are Java-1.4-era & build-hostile in DaCapo form), or must each match DaCapo's exact version for report fidelity? Default if unanswered: current-upstream + isolate-hot-path.
```

Why: research-design judgment with the rework cost and a default named. Answered in an agent-mode session at 19:59 ("launched in agent mode"); ticket done at 21:48 the same night with all five workloads banked.

### 6. 2026-07-16, xpllm, queued question that stops a paid experiment
`~/Code/xpllm/coga/log.md` lines 633 and 648.

```
2026-07-16 17:30 [magicator-llvm/06-run-the-a2-a3-gate-on-llvm-emitted-slices] [agent:claude] blocked: Current LLVM artifact retains 155/157 instructions (98.7%), all user functions, and all globals, so A3 would test whole-program IR prompting rather than useful slicing. Redesign the slicing criterion/semantic summary or use a larger haystack subject that yields material reduction before launching paid Opus/Fable A3 cells.

2026-07-16 18:46 [magicator-llvm/06-run-the-a2-a3-gate-on-llvm-emitted-slices] [human:nick] unblocked (blocked → active): Owner resolved: stop this gate as inconclusive, publish the neutral result, and move the next attempt to a larger program with a material-reduction admission gate.
```

Why: the agent noticed the experiment would be meaningless and declined to spend money. Answered in 76 minutes.

### 7. 2026-07-29, magicator, morning triage where agents queue themselves
`~/Code/magicator/coga/log.md` lines 779 to 800; unblock at 868.

```
2026-07-29 11:20 [observation-loop/rebuild/1-remove-the-legacy-instrumentation-pipeline] [human:nick] created (status=draft)
  (five more rebuild tickets created at 11:20)
2026-07-29 11:31 [observation-loop/1-site-identity-and-the-site-table] [human:nick] canceled (in_progress → canceled): Superseded after closing PR #831; replaced by the ordered observation-loop/rebuild ticket sequence.
2026-07-29 11:33 [observation-loop/2-generic-site-rules] [human:nick] canceled (blocked → canceled): Superseded by observation-loop/rebuild; this ticket depends on the legacy Instrumentor architecture that the rebuild intentionally removes.
  (tickets 3, 4, 5, 6 canceled at 11:35, 11:36, 11:37, 11:39)
2026-07-29 11:41 [observation-loop/rebuild/2-emit-compiler-source-translation-metadata] [human:nick] activated (draft → active) — Queued behind removal of the legacy instrumentation pipeline.
2026-07-29 11:41 [observation-loop/rebuild/2-emit-compiler-source-translation-metadata] [agent:claude] blocked: Sequencing: blocked behind observation-loop/rebuild/1-remove-the-legacy-instrumentation-pipeline.
2026-07-29 11:41 [observation-loop/rebuild/3-build-the-observation-loop-from-scratch] [agent:claude] blocked: Sequencing: blocked behind observation-loop/rebuild/2-emit-compiler-source-translation-metadata.
2026-07-29 11:41 [observation-loop/rebuild/4-add-site-ids-for-instrumented-instructions] [agent:claude] blocked: Sequencing: blocked behind observation-loop/rebuild/3-build-the-observation-loop-from-scratch.
2026-07-29 11:42 [observation-loop/rebuild/5-final-observation-loop-cleanup] [agent:claude] blocked: Sequencing: blocked behind observation-loop/rebuild/4-add-site-ids-for-instrumented-instructions.

2026-07-30 11:58 [observation-loop/rebuild/3-build-the-observation-loop-from-scratch] [human:nick] unblocked (blocked → active): observation-loop/rebuild/2-emit-compiler-source-translation-metadata is done — merged as ed67a63a2 (PR #835) on 2026-07-30 — so the sequencing dependency is satisfied.
```

Why: 22 minutes of human triage (six created, six canceled, four activated), then each activated ticket blocks itself with a one-line reason instead of starting work it cannot do. Unblocks come over the following days, each citing the merged PR.

### 8. 2026-07-22, magicator, megalaunch sweep
`~/Code/magicator/coga/log.md` lines 486 to 521; counterpoint at 1420 to 1422.

```
2026-07-22 21:45 [docs-migration/cluster-b-migrate-slicing-and-heap-soundness-docs] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-07-22 21:45 [docs-migration/cluster-c-migrate-loop-optimization-docs-to-a-new] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-07-22 21:45 [docs-migration/cluster-d-migrate-system-slice-cache-docs-to-a-new] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-07-22 21:45 [docs-migration/cluster-e-migrate-operating-model-docs-into-runboo] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-07-22 21:45 [docs-migration/cluster-f-migrate-benchmark-and-sota-docs-into-ben] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-07-22 21:45 [docs-migration/cluster-g-re-audit-the-source-only-magicator-conte] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-07-22 21:45 [docs-migration/cluster-b-migrate-slicing-and-heap-soundness-docs] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-22 21:45 [docs-migration/cluster-b-migrate-slicing-and-heap-soundness-docs] [megalaunch] launched via coga megalaunch
2026-07-22 21:52 [docs-migration/cluster-c-migrate-loop-optimization-docs-to-a-new] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-22 22:00 [docs-migration/cluster-d-migrate-system-slice-cache-docs-to-a-new] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-22 22:17 [docs-migration/cluster-e-migrate-operating-model-docs-into-runboo] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-22 22:27 [docs-migration/cluster-f-migrate-benchmark-and-sota-docs-into-ben] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-22 22:50 [docs-migration/cluster-g-re-audit-the-source-only-magicator-conte] [megalaunch] started (active → in_progress) via coga megalaunch

2026-08-26 11:40 [coga/give-recipe-run-recurring-tasks-a-durable-run-hist] [megalaunch] started (active → in_progress) via coga megalaunch
2026-08-26 11:43 [coga/give-recipe-run-recurring-tasks-a-durable-run-hist] [agent:claude] blocked: Owner-decision ticket on a code workflow: pick option 1-4 under '## Options' on the blackboard. Investigation changed the premise — coga #705 (df1d0602) deleted the recipe-direct dispatch, so no template fires without an agent any more [...] Decision needed: (a) do nothing [...]; (b) new coga/contexts/repo/recurring-runs stating 'log, not blackboard' [...]; (c) standardize a bounded '## Last run' block, which needs upstream coga work this repo cannot do; (d) land the ticket.py shims first and re-ask. Recommend (b) or (d). Also: re-route this ticket to decide/with-owner.
```

Why: six tickets picked in one minute, executed serially over 65 minutes with no human line in between. The 2026-08-26 counterpoint shows a megalaunched ticket blocking three minutes in with a four-option owner question and a recommendation.

### 9. 2026-08-27 and 2026-09-01, admin, megalaunch sweeps. CONFIDENTIALITY: check before publishing
`~/Code/admin/coga/log.md` lines 1278 to 1304 and 1512 to 1642.

```
2026-08-27 09:19 [doc-updates/count-repo-wide-refs-by-matching-both-yaml-frontma] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-08-27 09:20 [admin/decide-whether-the-vendored-browser-and-google-age] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-08-27 09:20 [admin/stop-shipping-one-off-tickets-as-contextless-stubs] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-08-27 09:20 [make/refresh-the-four-inventory-tables-against-shipped] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-08-27 09:20 [doc-updates/count-repo-wide-refs-by-matching-both-yaml-frontma] [megalaunch] started (active → in_progress) via coga megalaunch
2026-08-27 09:33 [doc-updates/count-repo-wide-refs-by-matching-both-yaml-frontma] [agent:claude] advanced to step 2 (peer-review) → assigned to codex — implement done on branch generate-ref-c
2026-08-27 09:42 [doc-updates/count-repo-wide-refs-by-matching-both-yaml-frontma] [agent:codex] advanced to step 3 (open-pr) → assigned to claude
2026-08-27 09:42 [doc-updates/count-repo-wide-refs-by-matching-both-yaml-frontma] [agent:claude] advanced to step 4 (review) → assigned to zach — PR opened: https://github.com/FastJVM/admin/p[...]
2026-08-27 09:42 [admin/decide-whether-the-vendored-browser-and-google-age] [megalaunch] started (active → in_progress) via coga megalaunch
2026-08-27 09:49 [admin/decide-whether-the-vendored-browser-and-google-age] [agent:claude] advanced to step 2 (peer-review) → assigned to codex
2026-08-27 09:58 [admin/decide-whether-the-vendored-browser-and-google-age] [agent:codex] advanced to step 3 (open-pr) → assigned to claude
2026-08-27 09:59 [admin/decide-whether-the-vendored-browser-and-google-age] [agent:claude] advanced to step 4 (review) → assigned to zach — PR opened: https://github.com/FastJVM/admin/pull/16
2026-08-27 09:59 [admin/stop-shipping-one-off-tickets-as-contextless-stubs] [megalaunch] started (active → in_progress) via coga megalaunch
```

The 2026-09-01 11:26 sweep (lines 1512 to 1523) activated twelve tickets in one minute; the human then ran seven recurring jobs by hand between 11:28 and 11:35 (repo-guards, tm-action-reminder, autoclose-merged, digest, monthly-one-off-review-reminder, supplier-payment-reminder, xero-reconcile) while the first megalaunched ticket went implement (11:26) to peer-review (11:38) to open-pr (11:47) to human review (11:49).

Why: two PRs reach human review in 40 minutes, with implement, peer-review, and open-pr handed agent-to-agent and no human line in between.

Sensitive: this is the company admin repo and the human is `zach`, not the essay's narrator. The 2026-09-01 window sits next to Slack posts naming a trademark office action serial number ("FASTJVM (sn99766075) was served August 28, 2026"), a Xero monthly reconcile, and supplier renewals ("fastjvm.com on February..."). The ticket slugs and step-advance lines quoted above look safe; the Slack lines are not.

### 10. 2026-08-19/20, admin, queued questions where the human overrules the recommendation. CONFIDENTIALITY: check before publishing
`~/Code/admin/coga/log.md` lines 887, 890, 1110, 1125.

```
2026-08-19 14:30 [make/quarterly-password-rotation] [agent:codex] blocked: admin/security-review must settle or explicitly approve the human-login rotation scope before this live reminder can ship; Zach must also confirm or change the proposed 0 9 20 1,4,7,10 * schedule.
2026-08-19 15:01 [make/quarterly-password-rotation] [human:zach] unblocked (blocked → active): Both asks resolved by Zach 2026-08-19 (bootstrap/orient session).

2026-08-20 14:49 [attach-the-four-orphaned-contexts-to-the-tickets-a] [agent:codex] blocked: Implementation already landed directly on origin/main at 7ea9876, and the freshly rebased feature branch has zero commits/diff, so the required open-pr step cannot run. Owner decision needed: close or skip the PR step, and delete accounting/transition (recommended) or retain it unattached.
2026-08-20 15:07 [attach-the-four-orphaned-contexts-to-the-tickets-a] [human:zach] unblocked (blocked → active): Owner decision (zach, 2026-08-20): skip the open-pr step. The change already landed on origin/main at 7ea9876 and the rebased branch is empty, so there is no diff to open a PR from; peer review was completed against the landed commit instead. Keep accounting/transition — do NOT delete it; retained deliberately for now, unattached.
```

Why: "delete (recommended)" answered with "do NOT delete" is exactly why the question was queued instead of guessed. Both answered within 31 and 18 minutes.

Sensitive: password-rotation policy and a security-review ticket name; the nearby Brex block at line 1019 (2026-08-19 16:16) names a Brex integration ID, API endpoints, and month-by-month missing-GL counts and should not be quoted. The blackboard at `~/Code/admin/coga/tasks/admin/stage-the-uncovered-goal-2-obligations-that-have-n.md:239` ("Open questions for Zach — three of the five need a fact I do not have": whether Gusto files Form 940 and W-2/W-3, whether any contractor was paid $600 or more, whether the company is registered with the City of San Francisco, "Jacob files the return") is a good agent-asks-human example but contains payroll and tax detail plus a named accountant.

### 11. Mechanical spares (use only if a credential/infra example is wanted)

- xpllm line 706/707, 2026-07-19 12:42: `blocked: Claude OAuth was revoked during Haiku zxing raw (401, zero tokens). Refresh the host Claude login at /home/n/.claude/.credentials.json, then tell the agent to resume; preserved t1/t2 casualties must be rerun.` Answered 12:50: `Nick refreshed Claude subscription OAuth; bounded exact-Haiku real-token check passed with allowed rate limit and no auth/fallback error.`
- xpllm lines 701/709/712/713, 2026-07-18 to 07-20: `Fable organization monthly usage limit exhausted during sunflow A3 t2; explicit provider reset is 2026-07-19 09:00 PDT.` then `Paused safely at Nick's request before PC sleep. Await explicit restart signal` then `Nick gave the explicit restart signal at 2026-07-20 13:50 PDT; post-sleep process/home/preflight checks are clean.`
- demo-hackathon lines 64 to 77, 2026-07-17 21:08 to 22:15: DNS and read-only-git blocks answered with `network is here` (21:12) and `GitHub access restored` (22:15), each followed by a `[megalaunch] activated (blocked → active) — explicit megalaunch pick` within a minute.
- tablet line 32 and multiply line 151: the recurring resolve-conflicts wrapper blocking because `'coga launch bootstrap/resolve-conflicts' refuses without a TTY`. Tooling anecdote only.
- multiply lines 74 and 77, 2026-08-18: `blocked: Launch gate unmet: spike-the-codex-plugin-lifecycle [...] has not run; its findings on client surfaces, hook timing, and writable plugin state must land and be attached before this design can assume a capture/buffering mechanism. Human chose to park until the spike lands.` Both canceled the next morning at 11:34 during a 24-action pivot (lines 84 to 125: eight tickets canceled, sixteen created in 21 minutes). Weak as a judgment example because the human's decision is recorded as a cancel, not an answer.

### Best picks

- **Best morning sequence:** xpllm 2026-07-30 07:50 to 12:27, `~/Code/xpllm/coga/log.md` lines 1113 to 1141 (candidate 3). Runner-up: magicator 2026-07-19 12:43 to 12:56, lines 286 to 292 (candidate 2): orient at 12:43, four-point answer at 12:47, launch at 12:49 and again at 12:56.
- **Best megalaunch sweep:** magicator 2026-07-22 21:45 to 22:50, `~/Code/magicator/coga/log.md` lines 486 to 521 (candidate 8): six tickets activated in one minute, executed serially over 65 minutes. Runner-up: xpllm 2026-07-29 14:49, lines 1091 to 1118, six sliceworldpoc tickets activated in one minute and executed serially through the next morning (14:49, 15:19, 16:43, 17:56, then 07:50 and 09:16 on 07-30). Largest by count: admin 2026-09-01 11:26, twelve tickets in one minute (confidentiality check needed).

### Shortfall statement

No shortfall. There are ten candidates across the non-Coga repos: eight strong ones with no confidentiality concern (six judgment questions, one morning sequence, one clean sweep, all from magicator and xpllm), plus two admin items that need a confidentiality pass. The weak repos are multiply (three blocks, all "launch gate unmet", canceled the next morning in a pivot), patents (zero block events, one sequential sweep of five tickets on 2026-07-22 15:14 to 16:09), tablet and demo-hackathon (mechanical blocks only). coga-hosting-probes is a duplicate checkout of multiply and adds nothing.
