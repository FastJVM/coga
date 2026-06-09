The blackboard is a notepad to be written to often as the human and agent works through a task.

## Origin

Split from `close-imported-skill-provenance-conflict-and-dream` on nick's
decision — this is gap 4 of the `add-imported-skill-update-check` audit (the
Dream skill-update maintenance phase), separated because it is template +
bundled-worker-skill authoring rather than CLI code+tests. The underlying
`relay skill update --all --pr` flow already exists (shipped in #143); this
ticket only adds the Dream worker + phase that calls it. Independent of the
sibling at the code level — can land in any order.
