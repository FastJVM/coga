This blackboard persists across every run of this recurring task. A run reads
it at the start to pick up where the last run left off, and updates it at the
end with whatever the next run needs.

If your REM task carries state between runs — a last-processed commit, a
high-water mark, a cursor — record it here in a clearly named section, and
say in `ticket.md` that runs read and update it.
