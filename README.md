# todo-expiry-ledger

Scan source-code TODO comments that carry a due date and/or an owner, and turn
them into a dated ledger: an overdue list, a due-soon list, aging buckets, and
an optional trend delta against a previous scan. Pure Python standard library,
single file, no network access. If your TODOs rot silently today, this makes
the rot visible and countable.

## Problem

`TODO` comments are write-only debt. Nobody remembers them, grep shows them
unordered, and a TODO from 2023 sits next to one from this morning with no way
to tell which is on fire. Issue trackers fix this but add process friction; a
deadline embedded in the code line itself (`TODO(2026-10-01, @alice): ...`)
adds none — but only if something actually reads those dates back. That reader
is missing, so deadlines in comments decay into decoration.

## How it works

1. **Parse** — a line-oriented regex finds `TODO` markers and extracts an
   optional parenthesized annotation containing an ISO due date and/or an
   `@owner` handle, plus the message. `// TODO(2026-10-20, @alice): fix login`
   becomes `{due: 2026-10-20, owner: alice}`.
2. **Classify** — against a reference date (`--as-of`, default today) each
   entry becomes `overdue`, `due_soon` (≤7 days), `open`, `no_due`, or
   `invalid_date` (e.g. `2026-13-45` is flagged, not silently accepted).
3. **Bucket** — overdue entries fall into aging buckets: 1–7, 8–30, 31–90,
   and 90+ days overdue; everything else is `not_overdue`.
4. **Trend** — `--compare prev.json` diffs status counts against a previous
   ledger so a scan can assert "overdue did not grow".

## Quickstart

```bash
# scan a repo and show the ledger (~1 second, measured)
python todo_expiry_ledger.py scan ./src --as-of 2026-10-11

# JSON ledger for CI consumption
python todo_expiry_ledger.py scan ./src --as-of 2026-10-11 --json

# assert overdue count did not grow vs last week's snapshot
python todo_expiry_ledger.py scan ./src --json --compare last_week.json
```

Self-test suite: 57/57 passing in under a second (measured: `python
self_test.py`; all seven sibling tool suites together took 4.4 s wall clock on
Python 3.13 / Windows 10, including interpreter startup).

## Why not X

| Alternative | Stars (as of 2026-10-11) | How this differs |
| --- | --- | --- |
| [ttoyaj/ledger](https://github.com/ttoyaj/ledger) | 0 | A personal todo-ledger app: it tracks tasks you enter into it. This tool scans dates already written inside source-code TODO comments — no second place to record anything. |
| [Gaurang200/TodoLedger](https://github.com/Gaurang200/TodoLedger) | 0 | Another task-tracking ledger application. This is a read-only static scanner over existing files; it never becomes the system of record, the code stays the system of record. |
| [dugnsdbs/nexus](https://github.com/dugnsdbs/nexus) (`todo_ledger_stock_with_aiagent`) | 0 | An AI-agent-driven todo/stock experiment. This tool is deterministic regex-and-date math: same input file tree and `--as-of` date always produce the same ledger, which is what a CI gate needs. |

Generic alternatives (grep, issue trackers) are covered in the FAQ.

## Minimal Fallback

If you cannot run Python in your pipeline, the same discipline fits one shell
line — it just loses buckets, owners, and trend:

```bash
grep -rnE "TODO\([0-9]{4}-[0-9]{2}-[0-9]{2}" src/ | sort   # dated TODOs, oldest last
```

That catches a date-annotated TODO rotting; it cannot flag `2026-13-45` as
invalid or compute days-overdue, which is the tool's core value.

## Design Trade-offs

- **Regex, not language parsers.** One parser per language is unaffordable for
  a single-file tool; the regex sees inside strings and comments of any
  language uniformly. Cost: a string literal mentioning "TODO" counts — in
  practice rare, and message text is advisory.
- **Date-in-comment convention, not metadata files.** The deadline lives where
  the work lives and dies with the line (refactors delete stale TODOs
  naturally). Cost: no reminders, no assignment notifications — this is a
  mirror, not a tracker.
- **Snapshot + explicit compare, not history storage.** The tool keeps no
  state; trend requires you to commit a previous JSON. Cost: one extra CI
  artifact; benefit: no hidden database to corrupt.
- **7-day `due_soon` window is hardcoded by default** but exposed as a
  parameter in `classify()`.

## Limits & Second-order Effects

- **Deadlines are honor-system.** An owner can push the date forward forever;
  the ledger records the push, it does not prevent it.
- **Goodhart risk.** Teams may stop writing due dates to keep the ledger
  green. Counter: track `no_due` count as its own metric — a rise there is
  the signal.
- **Large monorepos**: full-tree walking is O(files); a 100k-file tree takes
  seconds, not minutes, but it is still linear [estimated].
- **Second order**: once a CI gate fails on overdue TODOs, people delete
  finished TODOs faster — which is the point — but also occasionally delete
  *unfinished* ones. The trend delta makes mass deletions visible in review.

## FAQ

**Does it read git blame to find who wrote the TODO?** No. Ownership comes
from `@handle` in the comment itself; blame integration was rejected as
vCS-dependent and slow.

**What about `FIXME`/`HACK`?** Out of scope by design; the convention that
carries a *date* is `TODO`. Other markers are one regex away if you need them.

**When NOT to use this?** When your team already tracks everything in an issue
tracker and writes no dated TODOs — a second ledger nobody feeds is noise. Also
skip it for generated/vendored directories (exclude them before scanning).

**Can a TODO have two owners?** The first `@handle` wins. Lists become
"nobody's job".

## Core Assumptions

1. Your team is willing to write `TODO(date, @owner)` in code comments; the
   tool amplifies a convention, it cannot create one.
2. Day-granularity deadlines are sufficient — no time-of-day, no timezones;
   all dates are calendar dates in one reference frame.
3. `--as-of` is trusted as "now"; for CI use, pin it to the build date so
   results are reproducible.
4. Comment text is ASCII-or-UTF-8 decodable; binary files are skipped.

Confidence: high on parsing/classification logic (57 deterministic self-tests),
medium on adoption assumptions. As of 2026-10-11.

---

Part of the [zhengming-toolbox](https://github.com/chenhz01/zhengming-toolbox) — 55 purpose-built AI-engineering tools across neglected niches.

Related tools: [self-heal-runbook](https://github.com/chenhz01/self-heal-runbook) · [deploy-checklist-code](https://github.com/chenhz01/deploy-checklist-code) · [quota-aware-scheduler](https://github.com/chenhz01/quota-aware-scheduler)
