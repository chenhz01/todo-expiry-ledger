# Changelog

## v0.1.1 — 2026-10-11

Round-2 revision after a line-by-line self-review of v0.1.0:

- Self-test suite expanded from 34 to 57 cases (+68%): added exception-path
  coverage (binary files, undecodable UTF-8, corrupt `--compare` JSON, bad
  `--as-of`) and extreme-edge coverage (10k-char lines, Unicode owners
  `@阿明`, CRLF files, 30-level directory nesting, empty directories).
- Owner regex switched to Unicode-aware `@([\w.-]+)` so non-ASCII handles
  parse instead of silently dropping the owner.
- Invalid calendar dates (e.g. `2026-02-30`) now classify as
  `invalid_date` even when the digits match the ISO shape.
- Documented measured timing (self_test 57/57, <1 s; measured 2026-10-11).
- All tests re-run green: `SUMMARY: PASS 57/57`.

## v0.1.0 — 2026-10-11

Initial release: TODO parsing with parenthesized date/owner annotations,
status classification (overdue / due_soon / open / no_due / invalid_date),
aging buckets, `--compare` trend deltas, argparse CLI with `--json` output.
34 self-test cases.
