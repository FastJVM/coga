This blackboard persists across every run of this recurring task. A run reads
it at the start to pick up where the last run left off, and updates it at the
end with whatever the next run needs.

Dream's per-period task is disposable and deletes itself, so Dream keeps no
durable state here — every Dream finding ends in a PR, a draft ticket, or a
recorded marker instead.
