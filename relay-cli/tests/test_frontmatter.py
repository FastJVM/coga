"""Tests for relay_os.frontmatter.

Covers:
- Reading: simple, full spec ticket, minimal ticket, recurring template,
  body-only files, empty frontmatter, `---` in body, multiline strings,
  special YAML chars, unicode.
- Writing: byte-identical no-op round-trip, single-field update preserves
  others, nested workflow object update, list-field updates, body
  preservation, save to alternate path.
- Step field helpers.
- Error paths: malformed YAML, non-mapping frontmatter.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from relay_os.frontmatter import (
    Document,
    FrontmatterError,
    format_step_field,
    parse_step_field,
)


# ------------------------------------------------------------------
# Reading — happy paths
# ------------------------------------------------------------------


def test_read_simple(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text("---\ntitle: hello\n---\nbody text\n")
    doc = Document.read(p)
    assert doc.frontmatter == {"title": "hello"}
    assert doc.body == "body text\n"


def test_read_full_spec_ticket(tmp_path: Path) -> None:
    """The "Full ticket example" from the spec — workflow nested object,
    list contexts, list watchers, every field type."""
    p = tmp_path / "ticket.md"
    p.write_text(
        dedent("""\
            ---
            title: Fix retry logic
            status: active
            mode: interactive
            owner: marc
            assignee: claude1
            watchers:
              - pierre
            workflow:
              name: code/with-review
              steps:
                - name: implement
                  skill: infra/testing-conventions
                - name: pr
                - name: approve
                  skill: process/approve
                - name: merge
            step: 1 (implement)
            contexts:
              - email/payment-flow
            ---

            ## Description

            Stripe webhook retries are silently failing.

            ## Context

            The retry logic lives in `lib/webhooks/retry.ts`.
        """)
    )
    doc = Document.read(p)
    assert doc.get("title") == "Fix retry logic"
    assert doc.get("status") == "active"
    assert doc.get("watchers") == ["pierre"]
    assert doc.get("contexts") == ["email/payment-flow"]
    wf = doc.get("workflow")
    assert wf["name"] == "code/with-review"
    assert len(wf["steps"]) == 4
    assert wf["steps"][0] == {"name": "implement", "skill": "infra/testing-conventions"}
    assert wf["steps"][1] == {"name": "pr"}
    assert doc.get("step") == "1 (implement)"
    assert "## Description" in doc.body
    assert "lib/webhooks/retry.ts" in doc.body


def test_read_minimal_ticket(tmp_path: Path) -> None:
    """The minimal ticket from the spec — title + status + body, no
    workflow, no contexts."""
    p = tmp_path / "minimal.md"
    p.write_text(
        dedent("""\
            ---
            title: Look into slow DNS resolution on staging
            status: ready
            owner: marc
            ---

            ## Description

            Staging DNS lookups are taking 2-3s.
        """)
    )
    doc = Document.read(p)
    assert doc.get("title") == "Look into slow DNS resolution on staging"
    assert doc.get("status") == "ready"
    assert doc.get("workflow") is None
    assert doc.get("contexts") is None


def test_read_recurring_template(tmp_path: Path) -> None:
    p = tmp_path / "weekly.md"
    p.write_text(
        dedent("""\
            ---
            schedule: "0 9 * * 1"
            schedule_comment: Every Monday at 9am
            mode: auto
            workflow: ops/check
            assignee: claude1
            owner: marc
            contexts:
              - email/deliverability
            project: email-tool
            ---

            ## Description

            Run the deliverability suite.
        """)
    )
    doc = Document.read(p)
    assert doc.get("schedule") == "0 9 * * 1"
    assert doc.get("workflow") == "ops/check"  # plain string here, not nested
    assert doc.get("contexts") == ["email/deliverability"]
    assert doc.get("project") == "email-tool"


def test_read_body_only_no_frontmatter(tmp_path: Path) -> None:
    p = tmp_path / "plain.md"
    p.write_text("# Just a heading\n\nNo frontmatter at all.\n")
    doc = Document.read(p)
    assert doc.frontmatter == {}
    assert doc.body == "# Just a heading\n\nNo frontmatter at all.\n"


def test_read_empty_frontmatter(tmp_path: Path) -> None:
    p = tmp_path / "empty-fm.md"
    p.write_text("---\n---\nbody\n")
    doc = Document.read(p)
    assert doc.frontmatter == {}
    assert doc.body == "body\n"


def test_read_dashes_in_body_are_not_delimiters(tmp_path: Path) -> None:
    """A `---` line inside the body must NOT be treated as a closing
    frontmatter delimiter. Non-greedy matching ensures the FIRST `---`
    after the opener wins."""
    p = tmp_path / "t.md"
    p.write_text(
        dedent("""\
            ---
            title: hello
            ---
            first body line

            ---

            this `---` separator is markdown, not frontmatter.
        """)
    )
    doc = Document.read(p)
    assert doc.frontmatter == {"title": "hello"}
    assert "this `---` separator" in doc.body
    # Body contains both the horizontal rule and the backtick-wrapped `---`.
    assert doc.body.count("---") == 2
    # Frontmatter only has the title — the body's `---` lines didn't leak in.
    assert doc.frontmatter == {"title": "hello"}


def test_read_multiline_string(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text(
        dedent("""\
            ---
            title: long
            description: |
              line one
              line two
              line three
            ---
            body
        """)
    )
    doc = Document.read(p)
    assert doc.get("description") == "line one\nline two\nline three\n"


def test_read_special_chars_colons_and_quotes(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text(
        dedent("""\
            ---
            title: "Fix: handle 'edge' case"
            url: "https://example.com/path:with:colons"
            ---
            body
        """)
    )
    doc = Document.read(p)
    assert doc.get("title") == "Fix: handle 'edge' case"
    assert doc.get("url") == "https://example.com/path:with:colons"


def test_read_unicode(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text("---\ntitle: café — résumé 北京\n---\nemoji body 🎉\n")
    doc = Document.read(p)
    assert doc.get("title") == "café — résumé 北京"
    assert "🎉" in doc.body


def test_read_no_trailing_newline(tmp_path: Path) -> None:
    """Files without a trailing newline are valid. We must preserve
    that on round-trip."""
    p = tmp_path / "t.md"
    p.write_text("---\ntitle: x\n---\nbody no newline")
    doc = Document.read(p)
    assert doc.body == "body no newline"


# ------------------------------------------------------------------
# Reading — error paths
# ------------------------------------------------------------------


def test_read_invalid_yaml(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text("---\ntitle: : :\n  bad: indent\n   wrong\n---\nbody\n")
    with pytest.raises(FrontmatterError, match="invalid YAML"):
        Document.read(p)


def test_read_non_mapping_frontmatter(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text("---\n- a\n- b\n---\nbody\n")
    with pytest.raises(FrontmatterError, match="must be a YAML mapping"):
        Document.read(p)


# ------------------------------------------------------------------
# Round-trip — byte identity is the contract
# ------------------------------------------------------------------


@pytest.mark.parametrize(
    "content",
    [
        # Simple
        "---\ntitle: hello\n---\nbody\n",
        # Trailing newline preserved
        "---\ntitle: hello\n---\nbody",
        # Empty body
        "---\ntitle: hello\n---\n",
        # Empty frontmatter
        "---\n---\nbody\n",
        # No frontmatter
        "# heading\n\ntext\n",
        # Multiline string and lists
        dedent("""\
            ---
            title: x
            list:
              - a
              - b
            block: |
              line1
              line2
            ---
            body
        """),
        # Dashes in body
        "---\ntitle: x\n---\nbefore\n---\nafter\n",
        # Unicode
        "---\ntitle: 北京\n---\n🎉\n",
    ],
    ids=[
        "simple",
        "no-trailing-newline",
        "empty-body",
        "empty-frontmatter",
        "no-frontmatter",
        "multiline-and-lists",
        "dashes-in-body",
        "unicode",
    ],
)
def test_round_trip_no_changes_byte_identical(tmp_path: Path, content: str) -> None:
    src = tmp_path / "src.md"
    src.write_text(content)
    doc = Document.read(src)
    out = tmp_path / "out.md"
    doc.save(out)
    assert out.read_text() == content


# ------------------------------------------------------------------
# Mutation: update preserves other fields and the body
# ------------------------------------------------------------------


def test_update_preserves_other_fields(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text(
        dedent("""\
            ---
            title: hello
            status: ready
            owner: zach
            ---
            body
        """)
    )
    doc = Document.read(p)
    doc.update(status="active")
    doc.save()

    reloaded = Document.read(p)
    assert reloaded.get("title") == "hello"
    assert reloaded.get("status") == "active"
    assert reloaded.get("owner") == "zach"
    assert reloaded.body == "body\n"


def test_update_preserves_body_exactly(tmp_path: Path) -> None:
    body = "## Description\n\nFirst paragraph.\n\n## Context\n\nSecond paragraph.\n"
    p = tmp_path / "t.md"
    p.write_text(f"---\ntitle: x\n---\n{body}")
    doc = Document.read(p)
    doc.update(title="y")
    doc.save()
    assert Document.read(p).body == body


def test_update_preserves_field_order(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text(
        dedent("""\
            ---
            title: x
            status: ready
            owner: zach
            ---
            body
        """)
    )
    doc = Document.read(p)
    doc.update(status="active")
    doc.save()
    text = p.read_text()
    # status appears between title and owner — i.e. the original order
    title_idx = text.index("title:")
    status_idx = text.index("status:")
    owner_idx = text.index("owner:")
    assert title_idx < status_idx < owner_idx


def test_update_nested_workflow(tmp_path: Path) -> None:
    """Workflow is a nested dict — make sure updating the step field
    doesn't disturb the workflow structure."""
    p = tmp_path / "t.md"
    p.write_text(
        dedent("""\
            ---
            title: x
            workflow:
              name: code/with-review
              steps:
                - name: implement
                - name: pr
            step: 1 (implement)
            ---
            body
        """)
    )
    doc = Document.read(p)
    doc.update(step="2 (pr)")
    doc.save()

    reloaded = Document.read(p)
    assert reloaded.get("step") == "2 (pr)"
    wf = reloaded.get("workflow")
    assert wf["name"] == "code/with-review"
    assert wf["steps"] == [{"name": "implement"}, {"name": "pr"}]


def test_update_list_field(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text("---\ntitle: x\ncontexts:\n  - a\n---\nbody\n")
    doc = Document.read(p)
    doc.update(contexts=["a", "b"])
    doc.save()
    assert Document.read(p).get("contexts") == ["a", "b"]


def test_update_multiple_fields_at_once(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text("---\ntitle: x\nstatus: ready\n---\nbody\n")
    doc = Document.read(p)
    doc.update(status="active", assignee="claude1", contexts=["foo"])
    doc.save()
    r = Document.read(p)
    assert r.get("status") == "active"
    assert r.get("assignee") == "claude1"
    assert r.get("contexts") == ["foo"]


def test_update_new_field_appends(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text("---\ntitle: x\n---\nbody\n")
    doc = Document.read(p)
    doc.update(status="ready")
    doc.save()
    text = p.read_text()
    assert text.index("title:") < text.index("status:")


def test_update_no_args_is_noop(tmp_path: Path) -> None:
    """Calling update() with nothing should not mark the document dirty
    — the next save should still be byte-identical."""
    content = "---\ntitle: x\n---\nbody\n"
    p = tmp_path / "t.md"
    p.write_text(content)
    doc = Document.read(p)
    doc.update()
    out = tmp_path / "out.md"
    doc.save(out)
    assert out.read_text() == content


def test_remove_field(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text("---\ntitle: x\nstatus: ready\n---\nbody\n")
    doc = Document.read(p)
    doc.remove("status")
    doc.save()
    r = Document.read(p)
    assert "status" not in r
    assert r.get("title") == "x"


def test_remove_missing_field_is_noop(tmp_path: Path) -> None:
    content = "---\ntitle: x\n---\nbody\n"
    p = tmp_path / "t.md"
    p.write_text(content)
    doc = Document.read(p)
    doc.remove("nonexistent")
    out = tmp_path / "out.md"
    doc.save(out)
    assert out.read_text() == content


def test_set_single_key_convenience(tmp_path: Path) -> None:
    """Set is sugar for update(**{key: value}) — useful when the key
    name isn't a valid Python identifier (e.g. has hyphens)."""
    p = tmp_path / "t.md"
    p.write_text("---\nname: x\n---\nbody\n")
    doc = Document.read(p)
    doc.set("schedule_comment", "every Monday")
    doc.save()
    assert Document.read(p).get("schedule_comment") == "every Monday"


# ------------------------------------------------------------------
# Save semantics
# ------------------------------------------------------------------


def test_save_to_alternate_path(tmp_path: Path) -> None:
    src = tmp_path / "src.md"
    src.write_text("---\ntitle: x\n---\nbody\n")
    dst = tmp_path / "dst.md"
    Document.read(src).save(dst)
    assert dst.exists()
    assert dst.read_text() == src.read_text()
    # Source untouched
    assert src.exists()


def test_save_after_update_overwrites_in_place(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text("---\ntitle: old\n---\nbody\n")
    doc = Document.read(p)
    doc.update(title="new")
    doc.save()
    assert "title: new" in p.read_text()
    assert "title: old" not in p.read_text()


# ------------------------------------------------------------------
# Document.parse (string input, no file)
# ------------------------------------------------------------------


def test_parse_from_string() -> None:
    doc = Document.parse("---\ntitle: x\n---\nbody\n")
    assert doc.get("title") == "x"
    assert doc.body == "body\n"


# ------------------------------------------------------------------
# parse_step_field / format_step_field
# ------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1 (implement)", (1, "implement")),
        ("2 (pr)", (2, "pr")),
        ("10 (approve)", (10, "approve")),
        # Step name with hyphens / slashes / spaces
        ("3 (code-review-and-merge)", (3, "code-review-and-merge")),
        ("1 (publish to linkedin)", (1, "publish to linkedin")),
        # Tolerate extra whitespace
        ("  1 (implement)  ", (1, "implement")),
        ("1  (implement)", (1, "implement")),
    ],
)
def test_parse_step_field_valid(raw: str, expected: tuple[int, str]) -> None:
    assert parse_step_field(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "1", "(implement)", "implement", "1.5 (x)"])
def test_parse_step_field_invalid_returns_none(raw) -> None:
    assert parse_step_field(raw) == (None, None)


def test_format_step_field() -> None:
    assert format_step_field(1, "implement") == "1 (implement)"
    assert format_step_field(10, "approve") == "10 (approve)"


def test_step_field_round_trip() -> None:
    n, name = 7, "merge"
    assert parse_step_field(format_step_field(n, name)) == (n, name)


# ------------------------------------------------------------------
# `__contains__` and `get` defaults
# ------------------------------------------------------------------


def test_contains(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text("---\ntitle: x\n---\nbody\n")
    doc = Document.read(p)
    assert "title" in doc
    assert "missing" not in doc


def test_get_with_default(tmp_path: Path) -> None:
    p = tmp_path / "t.md"
    p.write_text("---\ntitle: x\n---\nbody\n")
    doc = Document.read(p)
    assert doc.get("title") == "x"
    assert doc.get("missing") is None
    assert doc.get("missing", "fallback") == "fallback"
