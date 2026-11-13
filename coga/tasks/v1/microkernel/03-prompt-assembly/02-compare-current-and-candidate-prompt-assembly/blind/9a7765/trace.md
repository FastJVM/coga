## Rollout 0 (main): 13 tool calls

### Call 1

```
{"questions":[{"title":"What would you like to change in `author-paused`?"}]}
```

Output (first 2500 chars):

```
{"accepted":true}
```

### Call 2

```
text(await tools.exec_command({cmd:"pwd && rg --files -g 'AGENTS.md' -g 'coga.toml' -g 'coga.local.toml' -g '*SKILL.md' -g '*ticket.md' -g '*.md' coga | head -70","max_output_tokens":2500}));
text(await tools.exec_command({cmd:"git status --short --branch && cat coga/tasks/author-paused/ticket.md && cat coga.toml","max_output_tokens":4500}));

```

Output (first 2500 chars):

```
Script completed
Wall time 0.2 seconds
Output:
{"chunk_id":"c7efe2","wall_time_seconds":0.000019277,"exit_code":0,"original_token_count":75,"output":"/tmp/coga-prompt-trial-667707cc\ncoga/coga.local.toml\ncoga/coga.toml\ncoga/context.md\ncoga/contexts/trial/format/SKILL.md\ncoga/log.md\ncoga/skills/trial/report/SKILL.md\ncoga/skills/trial/write/SKILL.md\ncoga/tasks/author-paused/ticket.md\ncoga/workflows/trial/inline.md\ncoga/workflows/trial/skilled.md\n"}{"chunk_id":"9f5802","wall_time_seconds":0.000013549,"exit_code":1,"original_token_count":137,"output":"## main...origin/main\n---\ntitle: author-paused\nstatus: paused\nowner: trial-owner\nagent: claude\ncontexts:\n- trial/format\nskills:\n- trial/report\nworkflow:\n  name: trial/inline\n  steps:\n  - name: write\n    assignee: agent\n  - name: judge\n    assignee: owner\nstep: 1 (write)\n---\n\n## Description\n\nPreserve the existing intent: write the agreed result after the owner resumes execution.\n\n## Context\n\nUse only the isolated trial repository.\n\n<!-- coga:blackboard -->\n\n## Notes\n\nKeep this unrelated owner note.\ncat: coga.toml: No such file or directory\n"}
```

### Call 3

```
text(await tools.exec_command({cmd:"cat coga/coga.toml coga/coga.local.toml && python -c \"from importlib.resources import files; print(files('coga.resources').joinpath('templates', 'coga', 'bootstrap'))\" && rg --files -g AGENTS.md -g SKILL.md /tmp 2>/dev/null | head -50","max_output_tokens":3000}));

```

Output (first 2500 chars):

```
Script completed
Wall time 0.1 seconds
Output:
{"chunk_id":"5b9c0b","wall_time_seconds":0.000014318,"exit_code":1,"original_token_count":635,"output":"version = 1\ndefault_status = \"draft\"\n[agents.claude]\ncli = \"claude\"\nfile = \"CLAUDE.md\"\n[git]\nenabled = true\nremote = \"origin\"\ncontrol_branch = \"main\"\n[notification.slack]\nenabled = false\n\n[agents.codex]\ncli = \"codex\"\nfile = \"AGENTS.md\"\nmode = \"local\"\nlaunch_args = \"--no-daemon -m gpt-6.1-sol -c model_reasoning_effort=\\\"medium\\\" -a never -c 'permissions.trial.filesystem={\\\":root\\\"=\\\"read\\\",\\\":slash_tmp\\\"=\\\"write\\\",\\\"/tmp/coga-prompt-trial-667707cc/.git\\\"=\\\"write\\\"}' -c permissions.trial.network.enabled=true -c 'default_permissions=\\\"trial\\\"' -c 'projects.\\\"/tmp/coga-prompt-trial-667707cc\\\".trust_level=\\\"trusted\\\"'\"\ndiscussion = \"-c developer_instructions={prompt}\"\nanalyze = \"-m gpt-6.1-sol -c model_reasoning_effort=\\\"medium\\\" -c 'permissions.trial.filesystem={\\\":root\\\"=\\\"read\\\",\\\":slash_tmp\\\"=\\\"write\\\",\\\"/tmp/coga-prompt-trial-667707cc/.git\\\"=\\\"write\\\"}' -c permissions.trial.network.enabled=true -c 'default_permissions=\\\"trial\\\"' -c 'projects.\\\"/tmp/coga-prompt-trial-667707cc\\\".trust_level=\\\"trusted\\\"' exec {prompt}\"\n\n[telemetry]\nenabled = false\nuser = \"trial-owner\"\nTraceback (most recent call last):\n  File \"<string>\", line 1, in <module>\n  File \"/home/n/.local/share/uv/python/cpython-3.12.12-linux-x86_64-gnu/lib/python3.12/importlib/resources/_common.py\", line 46, in wrapper\n    return func(anchor)\n           ^^^^^^^^^^^^\n  File \"/home/n/.local/share/uv/python/cpython-3.12.12-linux-x86_64-gnu/lib/python3.12/importlib/resources/_common.py\", line 56, in files\n    return from_package(resolve(anchor))\n                        ^^^^^^^^^^^^^^^\n  File \"/home/n/.local/share/uv/python/cpython-3.12.12-linux-x86_64-gnu/lib/python3.12/functools.py\", line 912, in wrapper\n    return dispatch(args[0].__class__)(*args, **kw)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/home/n/.local/share/uv/python/cpython-3.12.12-linux-x86_64-gnu/lib/python3.12/importlib/resources/_common.py\", line 82, in _\n    return importlib.import_module(cand)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/home/n/.local/share/uv/python/cpython-3.12.12-linux-x86_64-gnu/lib/python3.12/importlib/__init__.py\", line 90, in import_module\n    return _bootstrap._gcd_import(name[level:], pack
```

### Call 4

```
text(await tools.exec_command({cmd:"command -v coga; ls -la; cat coga/workflows/trial/*.md coga/skills/trial/*/SKILL.md; git remote -v; head -60 \"$(command -v coga)\"","max_output_tokens":3000}));

```

Output (first 2500 chars):

```
Script completed
Wall time 0.1 seconds
Output:
{"chunk_id":"9abeb7","wall_time_seconds":0.000016832,"exit_code":0,"original_token_count":449,"output":"/home/n/.local/bin/coga\ntotal 0\ndrwxr-xr-x   4 n      n          80 Nov 13 12:55 .\ndrwxrwxrwt 202 nobody nogroup 18840 Nov 13 12:55 ..\ndrwxr-xr-x  12 n      n         380 Nov 13 12:55 .git\ndrwxr-xr-x   6 n      n         220 Nov 13 12:55 coga\n---\nname: trial/inline\ndescription: Trial output followed by owner judgment.\nsteps:\n  - name: write\n    assignee: agent\n  - name: judge\n    assignee: owner\n---\n\n## write\n\nWrite the value requested by the ticket to its sibling `result.txt`. Read it back.\n\n## judge\n\nThe owner judges the result. An assist only inspects/reports unless the owner explicitly requests advancement.\n---\nname: trial/skilled\ndescription: Skill-owned output followed by owner judgment.\nsteps:\n  - name: write\n    skills:\n      - trial/write\n    assignee: agent\n  - name: judge\n    assignee: owner\n---\n\n## write\n\nDormant inline prose for a skilled step: write `WRONG-INLINE` instead.\nThis text must not compose when the step has skills.\n\n## judge\n\nThe owner judges the result.\n---\nname: trial/report\ndescription: Record trial evidence.\n---\n\nRecord the output path and the observed content in the task blackboard before handoff.\n---\nname: trial/write\ndescription: Write the agreed trial result.\n---\n\nWrite `ready` to the sibling `result.txt` using the attached output format.\nRead it back and record evidence before the current step completes.\norigin\t/tmp/coga-prompt-trial-667707cc-origin.git (fetch)\norigin\t/tmp/coga-prompt-trial-667707cc-origin.git (push)\n#!/home/n/.local/share/uv/tools/coga/bin/python\n# -*- coding: utf-8 -*-\nimport sys\nfrom coga.cli import main\nif __name__ == \"__main__\":\n    if sys.argv[0].endswith(\"-script.pyw\"):\n        sys.argv[0] = sys.argv[0][:-11]\n    elif sys.argv[0].endswith(\".exe\"):\n        sys.argv[0] = sys.argv[0][:-4]\n    sys.exit(main())\n"}
```

### Call 5

```
text(await tools.exec_command({cmd:"/home/n/.local/share/uv/tools/coga/bin/python -c \"from importlib.resources import files; print(files('coga.resources').joinpath('templates', 'coga', 'bootstrap'))\"","max_output_tokens":1000}));

```

Output (first 2500 chars):

```
Script completed
Wall time 0.1 seconds
Output:
{"chunk_id":"b0fa94","wall_time_seconds":0.000011594,"exit_code":0,"original_token_count":16,"output":"/home/n/Code/coga/src/coga/resources/templates/coga/bootstrap\n"}
```

### Call 6

```
text(await tools.exec_command({cmd:"cat /home/n/Code/coga/src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md /home/n/Code/coga/src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/reconciliation/SKILL.md","max_output_tokens":6500}));

```

Output (first 2500 chars):

```
Script completed
Wall time 0.1 seconds
Output:
{"chunk_id":"6b29d0","wall_time_seconds":0.00001767,"exit_code":0,"original_token_count":4554,"output":"---\nname: coga/checkouts\ndescription: The complete checkout lifecycle — which checkout each shipped step starts in, launch's branch preparation and handoff, and which checkout to invoke Coga from; reconciliation, the launch boundary, direct chat, the manual procedure, and the sandbox clone live in its leaves.\n---\n\n# Feature checkouts\n\nCode-ticket work runs in the checkout the session was launched from. Every\nsession starts from a clean, current `main`, a step that changes code works\non its feature branch, and the session ends back on `main`. Under\n`coga launch` the launcher performs the branch setup and both moves; in any\nother session the agent does. Ticket work creates no linked worktrees; the\none alternative checkout is the [sandbox clone fallback](sandbox-clone/SKILL.md).\nOnly the recurring runner's temporary control worktree and Retro's isolated\ncheckout (created and removed for one Retro pass) are linked worktrees; ones\nleft from an earlier layout are disposed of by\n[coga/checkout-cleanup](../checkout-cleanup/SKILL.md).\n\nThe ticket's `## Dev` record (`branch:`, `worktree:` for a sandbox clone,\n`pr:`) is the link from ticket to branch to PR. It is explicit, not inferred\nfrom the slug, because slug conventions break whenever a PR bundles tickets,\nan agent picks another branch name, or a slug is truncated. Anything that\nfollows the link (bump gates, `open-pr`, autoclose, retire, status views)\nreads the record; a branch name need not match the slug.\n\n`origin` and `main` stand for the configured `[git].remote` and\n`[git].control_branch`; `coga/tasks/`, `coga/recurring/`, and `coga/log.md`\nfor the configured workspace's task, recurring, and log paths. **The Coga\nroots** are the Coga root plus the configured contexts root; every eligible (unignored) file there is Coga state\nthat publication carries ([coga/state-publication](../state-publication/SKILL.md)).\n\n## Leaves\n\n- [reconciliation](reconciliation/SKILL.md) — keeping edits current with main.\n- [launch-boundary](launch-boundary/SKILL.md) — preparing and returning the\n  invoking checkout, refusal recovery, and exemptions.\n- [chat](chat/SKILL.md) — direct chat's occupancy guard and branch.\n- [manual](manual/SKILL.md) — the start, work, and end an agent performs\n  when launch did not prepare the branch.\n- [sandbox-clone]
```

### Call 7

```
text(await tools.exec_command({cmd:"cat /home/n/Code/coga/src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/manual/SKILL.md; git fetch origin; git diff main origin/main -- coga; git show origin/main:coga/tasks/author-paused/ticket.md; git log -3 --oneline","max_output_tokens":3500}));

```

Output (first 2500 chars):

```
Script completed
Wall time 0.1 seconds
Output:
{"chunk_id":"bb187c","wall_time_seconds":0.000019975,"exit_code":0,"original_token_count":1176,"output":"---\nname: coga/checkouts/manual\ndescription: The start check, branch work, and end-of-step return an agent performs itself when launch did not prepare its branch, and how to publish pre-branch ticket edits before switching.\n---\n\n# Manual start, work, end\n\nPart of [coga/checkouts](../SKILL.md), which owns the launched lifecycle and\nwhich checkout each step starts in.\n\n## Procedure\n\nUse this when no `COGA_LAUNCH_RETURNS_CHECKOUT=1` witness is set — manual or\nAPI sessions, megalaunch picks, exempt checkouts — and before editing in a\nstep whose runtime notice says launch set up no branch (manual policy, or a\ncontrol step that must exceptionally change code). The agent performs both\nmoves:\n\n1. **Start check.** `git fetch origin main`, then require HEAD on `main`, a\n   clean tree with Coga state included, and a successful `git merge\n   --ff-only origin/main`. Launch regenerates the ignored\n   `coga/.agent-skills/` view; a repo initialized before `coga init` wrote\n   that ignore rule sees it as dirt — add `.agent-skills/` to\n   `coga/.gitignore`, never commit it. Anything else — dirty files, another\n   ticket's branch, a diverged `main` — means stop: ask the attending human,\n   or `coga block` in a queue run. Do not work around an occupied checkout\n   with a linked worktree, a control checkout, a stash, or a switch.\n2. **Work.** Write ticket state (`branch:` under `## Dev` once created with\n   `git branch <name>`, plan notes) on `main`, publish it (below), then\n   switch to the feature branch and change code only; ticket edits made\n   there are not published until the next sweep. A resumed branch is reused:\n   switch to it and `git rebase` onto fetched `origin/main`.\n3. **End.** Commit, push the branch (`git push -u origin <branch>`, or\n   `--force-with-lease` after a rebase), then return:\n   - `git fetch origin main`;\n   - for every dirty path under the Coga roots, verify it is already on\n     `origin/main` by the rules of\n     [the launch boundary](../launch-boundary/SKILL.md) (`git diff --quiet origin/main -- <path>`;\n     for `coga/log.md`, every added line is on `origin/main`) and discard it\n     (`git restore --source=HEAD --staged --worktree -- <path>`). `git diff`\n     skips untracked files, so compare an untracked one with\n     `git show origin/main:<path> | cmp - 
```

### Call 8

```
text(await tools.exec_command({cmd:"git fetch origin main && git status --short --branch && git merge --ff-only origin/main && cat coga/tasks/author-paused/ticket.md","max_output_tokens":1800}));

```

Output (first 2500 chars):

```
Script completed
Wall time 0.1 seconds
Output:
{"chunk_id":"a8c542","wall_time_seconds":0.000017321,"exit_code":0,"original_token_count":154,"output":"From /tmp/coga-prompt-trial-667707cc-origin\n * branch            main       -> FETCH_HEAD\n## main...origin/main\nAlready up to date.\n---\ntitle: author-paused\nstatus: paused\nowner: trial-owner\nagent: claude\ncontexts:\n- trial/format\nskills:\n- trial/report\nworkflow:\n  name: trial/inline\n  steps:\n  - name: write\n    assignee: agent\n  - name: judge\n    assignee: owner\nstep: 1 (write)\n---\n\n## Description\n\nPreserve the existing intent: write the agreed result after the owner resumes execution.\n\n## Context\n\nUse only the isolated trial repository.\n\n<!-- coga:blackboard -->\n\n## Notes\n\nKeep this unrelated owner note.\n"}
```

### Call 9

```
text(await tools.apply_patch("*** Begin Patch\n*** Update File: /tmp/coga-prompt-trial-667707cc/coga/tasks/author-paused/ticket.md\n@@\n Preserve the existing intent: write the agreed result after the owner resumes execution.\n+Verify the output before handoff.\n*** End Patch"));
text(await tools.exec_command({cmd:"coga launch author-paused --prompt-report","max_output_tokens":1800}));

```

Output (first 2500 chars):

```
Script completed
Wall time 0.3 seconds
Output:
{}{"chunk_id":"d14be3","wall_time_seconds":0.109168602,"exit_code":0,"original_token_count":327,"output":"Prompt report for author-paused\nApproximate tokens use characters / 4; exact tokenizer parity is not assumed.\n\nlayer                ref                                     bytes  approx_tokens\n-------------------- ---------------------------------- ---------- --------------\nheader               -                                       107 B             27\nbase_prompt          prompt.md                             3.6 KiB            920\nticket_loop          prompt-ticket.md                      3.1 KiB            795\nsession_conduct      prompt-attended.md                    1.7 KiB            434\nrepo_context         context.md                              190 B             48\nticket_context       trial/format                            168 B             42\ntop_level_skill      trial/report                            174 B             44\nworkflow_inline      trial/inline                            106 B             27\ntask_description     ticket.md##Description                  143 B             36\ntask_context         ticket.md##Context                       65 B             17\nblackboard           ticket.md##blackboard                    72 B             18\ncheckout_notice      -                                       234 B             59\n\nTotal composed prompt: 9.7 KiB (~2481 tokens)\n"}
```

### Call 10

```
{"task_name":"review_ticket","fork_turns":"none","message":"gAAAAABq93ltJN5a0tQK8JAgWaDVXDUkZKZcAU3xdqpITTr4D_qRjBkOuqJzMR3QmQAxQ9pTj4OD1-OjQrojLJ7YT6ZdwrIofGtbZ8PIUZH2F3Pp7fJIllWuQce98FVS90v7G5P3hZz91eD44EIXrh93uwk9bhmCEM0zwa6e7ZmnUpiSqZlgsgSOG3Rsk3ff_Gof9iEnVMUTlgthRZ7w_zG2BkqAQo6bppobkfB7qZe5-vTEL9C6-XW878hZT5ExFFeGfan2oR0tSiLvW61Yy0tx7dXDbLX9Bp3g_5b3Bdwgg3ljIHun9Y7ks1Xcp3wSL27mMNiwKBcMOA7kp41VYtelgFxTDu30Q8iYGDFiIj59qWqz0FZpMzfMPdXe4ZU-aT5VyhQXf3u_Z_XCIJ8GJjCKyhjRmmSq0-PEvpZCMQ6JQl42jcIZ2b8sdMqKTxyofqsNFssLsNkzDKgKcQg2K3C61KREygmWdBxOsdgRtQ5wOzf8ITMMPAnL1rwMCT7kdaauTysQcBTAI7zYGR5M518csXaawNgwwR4PjM3P-HAOfstzGjIBoG07suyZaHdYpzbnvP2nIYAsFWv_LUZ_XrQyRyPtkrvNaNEyXM3EXIR9tMqmIM5KJOr7LmVywLA_aEI_YSZ8gOeg7Nra46ZvasU5fyC1Ocsu20lHZ_PT5vBGsYMGcPiuBkVBleLdrwY9DP4ZmjN2Zb1Ev0GKEs-3P_obPYdHjzivlI9IBt1zzVuBmI_QI4_b4xEQffa0WzyZh-ZISFDIs8HM61CWoFlHBptV6Hbr6WprDf-RutfEO7Y_kCq6hhdIK60l29jC5-PM4rwzyrY7-5-3Stu_uJkF42uhM2iPBpKaF2B44BBCTTcmY30kzWAOu8Kzmsytagc_mv-Ykxw-mPrtzwrUOON1lqFLxzOkri35EzhI7SojV1R2UTBzvpeWFJ8fZMX-zKcD0TPB4pyKktZFLjsZ3CEBcHG6yiF8LQd1AHN1hyJaqYAtMwKnDSjyLmi4OZ6QrzjwxxJnHACkCd_6Yol-FLb38nub1NshA2SB-H8nU-ctTtPv_QfvPNKsJlmpJigj66W5wPSEWi0luJBJ"}
```

Output (first 2500 chars):

```
{"task_name":"/root/review_ticket"}
```

### Call 11

```
text(await tools.exec_command({cmd:"git diff -- coga/tasks/author-paused/ticket.md && git status --short","max_output_tokens":1200}));

```

Output (first 2500 chars):

```
Script completed
Wall time 0.1 seconds
Output:
{"chunk_id":"e5220e","wall_time_seconds":0.000021372,"exit_code":0,"original_token_count":107,"output":"diff --git a/coga/tasks/author-paused/ticket.md b/coga/tasks/author-paused/ticket.md\nindex e94603a..a0908d6 100644\n--- a/coga/tasks/author-paused/ticket.md\n+++ b/coga/tasks/author-paused/ticket.md\n@@ -20,6 +20,7 @@ step: 1 (write)\n ## Description\n \n Preserve the existing intent: write the agreed result after the owner resumes execution.\n+Verify the output before handoff.\n \n ## Context\n \n M coga/tasks/author-paused/ticket.md\n"}
```

### Call 12

```
{"timeout_ms":10000}
```

Output (first 2500 chars):

```
{"message":"Wait completed.","timed_out":false}
```

### Call 13

```
text(await tools.exec_command({cmd:"git fetch origin main && git diff --exit-code HEAD origin/main -- coga/tasks/author-paused/ticket.md && python - <<'PY'\nfrom pathlib import Path\nimport subprocess\np = Path('coga/tasks/author-paused/ticket.md')\nold = subprocess.check_output(['git', 'show', 'HEAD:coga/tasks/author-paused/ticket.md']).decode()\nexpected = old.replace('Preserve the existing intent: write the agreed result after the owner resumes execution.\\n', 'Preserve the existing intent: write the agreed result after the owner resumes execution.\\nVerify the output before handoff.\\n', 1)\nassert p.read_text() == expected\nprint('Verified: only the requested sentence changed; lifecycle, workflow and owner note preserved.')\nPY\ncoga run publish-state /tmp/coga-prompt-trial-667707cc/coga/tasks/author-paused/ticket.md","max_output_tokens":1500}));

```

Output (first 2500 chars):

```
Script completed
Wall time 0.4 seconds
Output:
{"chunk_id":"5f795e","wall_time_seconds":0.266449468,"exit_code":0,"original_token_count":65,"output":"From /tmp/coga-prompt-trial-667707cc-origin\n * branch            main       -> FETCH_HEAD\nVerified: only the requested sentence changed; lifecycle, workflow and owner note preserved.\npublish-state: published to origin/main\n  coga/tasks/author-paused/ticket.md\n"}
```

## Rollout 1 (sub-agent): 3 tool calls

### Call 1

```
text(await tools.exec_command({cmd:"cat coga/tasks/author-paused/ticket.md","max_output_tokens":3000}));

```

Output (first 2500 chars):

```
Script completed
Wall time 0.1 seconds
Output:
{"chunk_id":"bf0f81","wall_time_seconds":0.000019905,"exit_code":0,"original_token_count":129,"output":"---\ntitle: author-paused\nstatus: paused\nowner: trial-owner\nagent: claude\ncontexts:\n- trial/format\nskills:\n- trial/report\nworkflow:\n  name: trial/inline\n  steps:\n  - name: write\n    assignee: agent\n  - name: judge\n    assignee: owner\nstep: 1 (write)\n---\n\n## Description\n\nPreserve the existing intent: write the agreed result after the owner resumes execution.\nVerify the output before handoff.\n\n## Context\n\nUse only the isolated trial repository.\n\n<!-- coga:blackboard -->\n\n## Notes\n\nKeep this unrelated owner note.\n"}
```

### Call 2

```
text(await tools.exec_command({cmd:"rg --files coga | sort","max_output_tokens":2000}));

```

Output (first 2500 chars):

```
Script completed
Wall time 0.1 seconds
Output:
{"chunk_id":"eeb1b2","wall_time_seconds":0.000016762,"exit_code":0,"original_token_count":61,"output":"coga/coga.toml\ncoga/context.md\ncoga/contexts/trial/format/SKILL.md\ncoga/log.md\ncoga/skills/trial/report/SKILL.md\ncoga/skills/trial/write/SKILL.md\ncoga/tasks/author-paused/ticket.md\ncoga/workflows/trial/inline.md\ncoga/workflows/trial/skilled.md\n"}
```

### Call 3

```
text(await tools.exec_command({cmd:"cat coga/workflows/trial/inline.md coga/contexts/trial/format/SKILL.md coga/skills/trial/report/SKILL.md","max_output_tokens":2000}));

```

Output (first 2500 chars):

```
Script completed
Wall time 0.1 seconds
Output:
{"chunk_id":"3874cf","wall_time_seconds":0.000015784,"exit_code":0,"original_token_count":167,"output":"---\nname: trial/inline\ndescription: Trial output followed by owner judgment.\nsteps:\n  - name: write\n    assignee: agent\n  - name: judge\n    assignee: owner\n---\n\n## write\n\nWrite the value requested by the ticket to its sibling `result.txt`. Read it back.\n\n## judge\n\nThe owner judges the result. An assist only inspects/reports unless the owner explicitly requests advancement.\n---\nname: trial/format\ndescription: The trial output format.\n---\n\nOutput files contain exactly the requested value followed by one newline.\n---\nname: trial/report\ndescription: Record trial evidence.\n---\n\nRecord the output path and the observed content in the task blackboard before handoff.\n"}
```
