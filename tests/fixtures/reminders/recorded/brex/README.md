# Recorded Brex runs

Real output from the two production Brex scripts in the admin repo, captured
2026-07-25 and used as the oracle for the retrofitted sweeps.

| File | Source | Contents |
| --- | --- | --- |
| `gl-missing.json` | `admin/coga/skills/brex/missing-gl/missing_gl.py --dry-run` | The 11 card charges missing a Debit GL account |
| `receipts-missing.json` | `admin/coga/skills/brex/api/missing_receipts.py --year 2026` | The 14 card expenses over $40 missing a receipt, `2026-01-09` → `2026-07-11` |
| `record-shape.json` | `missing_receipts.py --month 2026-06 --debug` | One full `/v3/accounting/records` record, pinning the field structure both sweeps parse |

## Anonymization

Vendor names, cardholder names/emails, and every Brex object id are replaced
with stable placeholders (`Vendor A`, `Cardholder One`, `accr_0000…001`). Real
card spend does not belong in a public repo.

Everything the sweep contract depends on is preserved unchanged: field names and
nesting, `posted_at` timestamps, amounts and currencies, review statuses, record
counts, and the `line_items` → `DEBIT` → `accounting_field_values` path the GL
probe walks. The trailing whitespace in `user.first_name` / `user.last_name` is a
real Brex quirk and is kept deliberately — the sweeps must collapse it.

## Why these exist

`record-shape.json` is the load-bearing one. The v3 accounting record carries
**no purchase date** — its only dates are `posted_at`, `updated_at`, `due_at`,
and `erp_posting_date`. An earlier draft of these sweeps filtered on an
`incurred` field that the API does not return, and no test could catch it because
the Brex query was stubbed with `NotImplementedError`. Freezing a real record
means the next change to the query shape is checked against what Brex actually
sends.
