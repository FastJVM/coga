# Recorded patents runs

Frozen inputs and output for the two production runs named in the ticket:

- `maintenance-output.txt` is copied from the maintenance sweep's 2026-07-13
  production notes. Its minimal ticket fixtures preserve the eight-patent
  inventory, two flags, and one paid suppression from that run.
- `candidate-output.txt` expands the candidate sweep's 2026-07-21 production
  notes through the original script's report format: four candidates, the three
  recorded missing-date slugs, and no in-window flag.

The fixtures intentionally archive those runs instead of reading the live
patents repo, whose ticket state has since changed.
