This blackboard persists across every run of this recurring task. A run reads
it at the start to pick up where the last run left off, and updates it at the
end with whatever the next run needs.

Dream's per-period task is disposable and deletes itself, so Dream keeps no
durable state here — every Dream finding ends in a PR, a draft ticket, or a
recorded marker instead. `relay recurring` still appends one `scaffolded …`
line per period below so a self-deleted run isn't re-scaffolded by the next
sweep.

[2026-05-22 15:54] scaffolded dream-2026-W21
[2026-05-26 14:52] scaffolded dream-2026-W22
