The blackboard is a notepad to be written to often as the human and agent works through a task.

## Plan (2026-05-19, claude1)

This is an implementation ticket — title says "skill" but the body actually asks for the *mechanism* (TOML schema + scaffold + validate + mark active). The bootstrap/ticket skill needs a small touch-up too, but it's not a brand-new skill.

### Implementation order

1. **`Config` carries `ticket_fields`** — new dataclass `TicketField(name, description, values, default, required)`. Parsed in `config.py` from `[ticket.fields.<name>]`. Reserved-name collision check at parse time against the canonical set (`title status mode owner human agent assignee watchers workflow step contexts skills`). Schema-creep guard: reject keys other than `description/values/default/required`.
2. **Template marker** — append `# --- extensions ---` as the last line inside the frontmatter block of `relay-os/tasks/_template/ticket.md`. YAML comment, parser-safe.
3. **`scaffold_task()` writes declared fields below marker** — populate every `[ticket.fields.<name>]` with its `default` (or `""`). They're standard YAML keys after the comment.
4. **Ticket renderer preserves the marker** — currently `Ticket.render()` calls `yaml.safe_dump`, which drops comments. Two options:
   - (a) hand-render the frontmatter so the comment is preserved.
   - (b) treat extension fields as ordinary YAML keys and drop the marker from the on-disk file (it's only there for the *template*; what matters is the spec lives in TOML, not in the file).
   - Going with (b): the marker is a human cue in the template, and the actual contract is "any frontmatter key declared in `[ticket.fields]` is an extension; any unknown key not in the canonical set is illegal." Simpler and round-trip-safe. The template carries the marker as a one-time visual hint, but rendered tickets just have the extension keys mixed in at the bottom.
   - Wait — the ticket description shows the marker in the rendered output. Re-reading: yes, the example shows `# --- extensions ---` in the rendered ticket. So path (a) it is. We hand-render the frontmatter, or pre-serialize the canonical block and append the extension block with the marker.
5. **`validate.py` understands extensions** — `_check_frontmatter_schema` currently rejects any key not in REQUIRED/OPTIONAL. Loosen: accept any key that is declared in `cfg.ticket_fields`. Enforce: declared-but-missing → error; present-but-undeclared → error (with carve-out: orphaned undeclared keys on tickets predating a now-removed declaration → warn, per spec). Enum violations → error. Required-empty at activation → enforced in `mark_active` not here (validation accepts empty drafts).
6. **`mark active` gates required fields** — extend `relay mark active` to refuse if any `required = true` field has an empty value.
7. **Bootstrap/ticket skill update** — short note that the interview should ask for declared extension fields too, and write them under the marker.
8. **Tests** — config parsing (happy + collision + bad keys), scaffold writes fields, validate accepts/declines correctly, mark active gates required.

### Open questions / decisions

- **Marker preservation.** Need custom frontmatter render. I'll keep `yaml.safe_dump` for the canonical block, then concatenate the marker + extension block (also `safe_dump`ed). Both blocks are valid YAML — concatenation works because YAML is line-oriented and `# --- extensions ---` is a comment. Reading uses the existing parser unchanged (comments are stripped, extension keys come through as ordinary dict entries).
- **Reading round-trip.** After read, `Ticket.frontmatter` is a flat dict with no notion of "extension." Determining what's an extension at validate/render time requires re-asking `cfg.ticket_fields`. That's fine.
- **Render needs config?** Currently `Ticket.render()` is config-free. For the marker to land in the right place we either (a) thread `cfg.ticket_fields` into render, or (b) have `Ticket.render` accept an explicit `extension_keys: set[str]` arg, or (c) always render the marker before any keys whose names aren't in the canonical set. (c) is cleanest — purely structural, no config dep. Going with (c).
- **Order of extension fields.** Insertion order in TOML preserved by `tomllib`. So `[ticket.fields.docket]` then `[ticket.fields.application_number]` → `docket:` then `application_number:`. `scaffold_task()` iterates `cfg.ticket_fields` in TOML order.
- **Reserved name set.** Canonical fields from `validate.py`: `title status mode owner human agent assignee watchers workflow step contexts skills`. Cross-checked against ticket.md template — `skills` is in the canonical set.
- **`required` at scaffold time.** A required field in scaffolded `draft` is fine empty; that's the human's TODO before `mark active`. Don't error in `scaffold_task` for required-empty drafts.

### Reading list

- `src/relay/config.py` — add `ticket_fields` to `Config`, parsing + reserved-name check.
- `src/relay/ticket.py` — render preserves marker.
- `src/relay/scaffold.py` — write extension fields into new tickets.
- `src/relay/validate.py` — extension-aware schema check.
- `src/relay/mark.py` / `src/relay/commands/mark.py` — gate `mark active` on required fields.
- `relay-os/tasks/_template/ticket.md` — add marker line.
- `relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md` — note about extensions.
- Tests across the corresponding `tests/test_*.py`.

## Implementation log (2026-05-19, claude1)

Implemented in this order, all green:

- `src/relay/config.py`: new `TicketField` dataclass; `_parse_ticket_fields()` reads `[ticket.fields.<name>]` and rejects (a) collisions with the canonical key set, (b) keys outside `{description, values, default, required}`, (c) malformed shapes, (d) enum defaults outside `values`. `Config.ticket_fields` is now a TOML-order-preserving dict.
- `src/relay/ticket.py`: rendering splits frontmatter into canonical vs non-canonical keys (using the new `CANONICAL_TICKET_KEYS` set, single source of truth) and prints non-canonical ones below a `# --- extensions ---` marker. No marker when nothing extends.
- `src/relay/scaffold.py`: after building the canonical frontmatter dict, every `cfg.ticket_fields[name]` is set to `spec.default` (or `""`).
- `src/relay/validate.py`: `_check_frontmatter_schema()` excludes declared extension keys from the "unknown key" set; declared-but-missing → `missing-extension` (error); enum violation on non-empty value → `bad-extension-value` (error); undeclared non-canonical key → `orphan-extension` (warn, since "removing an extension is symmetric"). Empty values stay valid at validate time — that's a `mark active` concern.
- `src/relay/mark.py`: `mark_active()` raises new `RequiredExtensionMissing(fields)` before touching disk if any `required = true` field is empty. The CLI catches it and prints `Cannot activate <slug>: required extension field(s) empty: '<name>'. Fill them in ticket.md then retry.`.
- `relay-os/tasks/_template/ticket.md` + bundled template: marker line added with a one-comment hint.
- Bootstrap `bootstrap/ticket` skill (both project-local copy and bundled template): step 6 in the interview spelling out the extension-field interview workflow.
- `relay/architecture` context (both project-local and bundled): new "Canonical ticket frontmatter" + "Ticket frontmatter extensions" sections so the reference points are real.

### Tests added

- `tests/test_config.py` — 10 new cases covering parse happy path, declaration order preservation, every shape/validation failure mode (reserved name collision, unsupported keys, missing description, empty/non-string-values, default not in enum, non-bool required), and the default-empty case.
- `tests/test_create.py` — 3 cases: scaffold writes declared fields with correct defaults below marker, no marker when no extensions, and read→edit→write round-trip preserves both extension value and marker.
- `tests/test_validate.py` — 5 cases: declared+filled passes clean, missing-extension errors, orphan-extension warns (declaration removed after ticket on disk), enum violation errors, empty value allowed at validate time even when required.
- `tests/test_mark.py` — 3 cases: required-empty blocks activation with named field in error, filling required allows activation, non-required empty is fine.

End-to-end manual test in `/tmp/relay-ext-test` exercised draft → fail-to-activate → fill → activate → validate. All paths behave as specified.

Full suite: `343 passed, 1 skipped`.

The pre-existing `try-me` / `try-me-2` validation errors on the relay-os repo are unrelated (they were errors before this change too).

## Retro

status: processed
skill: retro/done-ticket
result: no-new-durable-knowledge
title: No new durable knowledge for add-extend-ticket-format-skill
