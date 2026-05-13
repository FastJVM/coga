## Creation Notes

Created from the bootstrap/orient session after checking current `gh skill`
docs. The user wants Relay-managed skills installed in `relay-os/skills`, a way
to install/remove from URLs, an update-all path, and a Dream PR so skill changes
are reviewed before merge.

Key decision: use `gh skill` as the substrate for GitHub-backed installs and
updates, but keep Relay wrappers for non-GitHub URLs, exact removal, local
adaptation conflict reporting, and PR/blackboard workflow.

External requirement: GitHub CLI `2.90.0+` with `gh skill` available. Do not
put this in Python `requirements.txt`; it is not a pip dependency.
