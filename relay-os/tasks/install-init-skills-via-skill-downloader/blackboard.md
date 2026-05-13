## Creation Notes

Created from bootstrap/orient after the user clarified that `relay init` should
not copy/paste Relay-owned skills from bundled templates once the skill
installer exists. Init should install/download skills through the same public
skill-management path so provenance and update metadata exist from day one.

Keep the boundary narrow: non-skill scaffolding can stay template-based; skill
directories should come from a manifest and installer/updater API.
