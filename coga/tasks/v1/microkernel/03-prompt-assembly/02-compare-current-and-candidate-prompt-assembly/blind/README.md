# Blinded evaluation pack

Each item folder holds one run under a neutral pair label (X/Y, shuffled per
pair; the seed is stored only in the key). For each item, judge the predeclared expectation in
`facts.md` against the files, diff and ordered tool trace (`trace.md`; probe
items also have `answer.txt`), then fill `verdicts.csv`. Open
`reveal-after-verdict/` (agent prose, delivered prompt) only after recording
the behavioral verdict, and mark `blinding_broken` where wording or trace
features revealed the arm. Ambiguous outcomes stay `inconclusive`.

Arm words and run-directory names are masked in traces; prompt wording echoed
by the agent may still reveal the arm. The key is `../blind-key.json`
(sha256 `9cbf6c363eeba232779889b4fca85ce4dfd969783aac2e34e1d668fccc07f554`); do not open it until
every verdict is recorded. Deterministic control and transport checks are
not blinded (their two arms run identical code); see the report.
