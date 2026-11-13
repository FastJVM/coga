# Rendered payload measurements

These are render-only measurements of the frozen specimens, not trial outcomes.
Bytes include invocation provenance, argument suffixes and the illustrative
interactive marker. Estimated tokens use ceil(chars/4), not model tokenization.

| Case | Baseline bytes | C1 bytes | Baseline estimated tokens | C1 estimated tokens |
| --- | ---: | ---: | ---: | ---: |
| author-paused | 37109 | 33793 | 9232 | 8404 |
| workflow-inline | 9972 | 9641 | 2491 | 2409 |
| workflow-skilled | 10395 | 9865 | 2597 | 2465 |
| input-attended | 10013 | 9679 | 2502 | 2419 |
| input-megalaunch | 10269 | 9718 | 2566 | 2428 |
| owner-assist | 10052 | 9700 | 2511 | 2424 |
| script-handoff | 10233 | 9730 | 2555 | 2430 |
| stateless-recurring | 6943 | 5372 | 1733 | 1340 |
| autofix-ok | 2216 | 3439 | 551 | 857 |
| autofix-duplicate | 2372 | 3602 | 590 | 897 |
| autofix-problem | 2285 | 3513 | 569 | 876 |

Total bytes: baseline 111,859; C1 108,052; reduction 3.40%.

This is below the proposed 15% aggregate payload threshold. All three
analysis cases grow because C1 retains their full independent procedure
and adds shared orientation, authority and invocation provenance.
No behavioral or reasoning improvement follows from these measurements.
The deterministic control has zero prompt bytes and no model session.
