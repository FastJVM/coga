Item b7ec76, label Y (pair probe-1 r2)

# probe-1 (workflow-skilled), repetition 2

## Question asked

Do not change any files. Answer one question about the instructions you were given in this session. Customization wanted: change how the current step writes its result. (1) Which file is the effective source of those instructions in this session, and what fact selected it? (2) Which file should I edit to make that customization, and why there? You may read at most four files. Give one answer.

## Predeclared correct answers (protocol)

Each fresh probe gets one frozen prompt, the same fixture/source tree and only
this question: identify (1) the effective source file and selection fact and
(2) the file to edit for the requested customization. Allow at most four file
reads, one answer, no mutations, no coaching. A correct answer needs both parts;
count wrong sources, wrong edit paths and corrections separately.

1. `workflow-skilled`: change how the current step writes its result. Correct:
   local `coga/skills/trial/write/SKILL.md`, selected by frozen current-step
   `skills: [trial/write]`, edited there; the dormant inline workflow section
   is not effective. Role/order belong to the workflow, not that skill.
2. `author-paused`: change the authoring interview greeting. Correct: resolved
   packaged `bootstrap/ticket/SKILL.md`, selected by the authoring projection;
   obtain a local `coga/skills/bootstrap/ticket/SKILL.md` override. Do not edit
   target execution workflow or installed package. A local override is a fork
   whose future upstream changes need explicit reconciliation.
3. `autofix-problem`: change what counts as an analyst problem. Correct in the
   current baseline and C1 specimen: `recurring_autofix.build_prompt`'s procedure
   (snapshotted as `sources/autofix-procedure.txt`), selected by one-shot analysis
   dispatch. Current production has no repo override for that text; identify
   that limitation and the owning source edit, rather than inventing a local
   skill/config override. Editing C1's experimental fragment changes only the
   specimen. Editable distribution of that procedure remains prototype work.

## Mechanical

- exit 0, timed out False, wall 14.2 s
- files mutated: False; live repo changed: False
- tool calls: 3 (the >4 file-read limit is judged from trace.md; one call may read several files)