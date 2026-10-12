#!/usr/bin/env python3
"""todo-expiry-ledger: scan code TODOs (due date / owner) into a ledger
with an overdue list and aging buckets. Pure standard library."""

import argparse
import json
import os
import re
import sys
from datetime import date

DEFAULT_EXTS = {
    ".py", ".md", ".txt", ".js", ".ts", ".json", ".yaml", ".yml", ".rst",
    ".toml", ".cfg", ".ini", ".html", ".css", ".sh", ".bat", ".java",
    ".go", ".rs", ".c", ".h", ".cpp", ".rb", ".php", ".sql",
}

TODO_RE = re.compile(r"\bTODO\b[ \t]*(?:\(([^)]*)\))?[ \t]*:?[ \t]*(.*)", re.IGNORECASE)
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
OWNER_RE = re.compile(r"@([\w.-]+)", re.UNICODE)

BUCKETS = ["not_overdue", "overdue_1_7", "overdue_8_30", "overdue_31_90", "overdue_90_plus"]


def valid_date(s):
    """Return the ISO string if s is a real calendar date, else None."""
    try:
        y, m, d = (int(x) for x in s.split("-"))
        date(y, m, d)
        return s
    except Exception:
        return None


def parse_todo(text, filepath="<memory>", lineno=0):
    """Parse one line of text. Return a TODO entry dict or None."""
    m = TODO_RE.search(text or "")
    if not m:
        return None
    inner, message = m.group(1), (m.group(2) or "").strip()
    due, owner, invalid_date = None, None, None
    if inner:
        dm = DATE_RE.search(inner)
        if dm:
            if valid_date(dm.group(0)):
                due = dm.group(0)
            else:
                invalid_date = dm.group(0)
        om = OWNER_RE.search(inner)
        if om:
            owner = om.group(1)
    if not owner:
        om = OWNER_RE.search(message)
        if om:
            owner = om.group(1)
    return {
        "file": filepath,
        "line": lineno,
        "message": message[:200],
        "due": due,
        "owner": owner,
        "invalid_date": invalid_date,
    }


def days_diff(due, as_of):
    """Positive => days remaining until due; negative => days overdue."""
    a = date(*(int(x) for x in as_of.split("-")))
    b = date(*(int(x) for x in due.split("-")))
    return (b - a).days


def classify(entry, as_of, soon_days=7):
    """Attach a status to an entry: open / due_soon / overdue / no_due / invalid_date."""
    if entry["invalid_date"]:
        entry["status"] = "invalid_date"
    elif not entry["due"]:
        entry["status"] = "no_due"
    else:
        try:
            dd = days_diff(entry["due"], as_of)
        except Exception:
            entry["status"] = "invalid_date"
            return entry
        if dd < 0:
            entry["status"] = "overdue"
            entry["days_overdue"] = -dd
        elif dd <= soon_days:
            entry["status"] = "due_soon"
            entry["days_left"] = dd
        else:
            entry["status"] = "open"
            entry["days_left"] = dd
    return entry


def build_ledger(entries, as_of, soon_days=7):
    return [classify(dict(e), as_of, soon_days) for e in entries]


def aging_buckets(ledger):
    b = {k: 0 for k in BUCKETS}
    for e in ledger:
        if e.get("status") == "overdue":
            d = e.get("days_overdue", 0)
            if d <= 7:
                b["overdue_1_7"] += 1
            elif d <= 30:
                b["overdue_8_30"] += 1
            elif d <= 90:
                b["overdue_31_90"] += 1
            else:
                b["overdue_90_plus"] += 1
        else:
            b["not_overdue"] += 1
    return b


def trend(current, previous):
    """Delta of status counts vs a previous ledger (list of entries)."""
    def counts(ledger):
        c = {}
        for e in ledger:
            c[e.get("status", "unknown")] = c.get(e.get("status", "unknown"), 0) + 1
        return c
    cur, prev = counts(current), counts(previous)
    keys = sorted(set(cur) | set(prev))
    return {k: cur.get(k, 0) - prev.get(k, 0) for k in keys}


def scan_directory(root, extensions=None):
    """Walk root and return parsed TODO entries. Skips binary/undecodable files."""
    if extensions is None:
        extensions = DEFAULT_EXTS
    entries = []
    if not os.path.exists(root):
        raise FileNotFoundError(root)
    if os.path.isfile(root):
        paths = [root]
    else:
        paths = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            for fn in sorted(filenames):
                paths.append(os.path.join(dirpath, fn))
    for p in paths:
        if extensions is not None and os.path.splitext(p)[1].lower() not in extensions:
            continue
        try:
            with open(p, "rb") as f:
                raw = f.read()
            if b"\x00" in raw[:4096]:
                continue
            text = raw.decode("utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            e = parse_todo(line, filepath=p, lineno=i)
            if e:
                entries.append(e)
    return entries


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="todo-expiry-ledger",
        description="Scan code TODOs (due date / owner) into a ledger with overdue list and aging buckets.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="scan a file or directory for TODOs")
    s.add_argument("path", help="file or directory to scan")
    s.add_argument("--as-of", default=date.today().isoformat(), help="reference date (YYYY-MM-DD)")
    s.add_argument("--json", action="store_true", help="output JSON ledger")
    s.add_argument("--compare", help="previous ledger JSON file for trend deltas")
    args = p.parse_args(argv)

    try:
        entries = scan_directory(args.path)
    except FileNotFoundError:
        print("error: path not found: %s" % args.path, file=sys.stderr)
        return 2

    ledger = build_ledger(entries, args.as_of)
    buckets = aging_buckets(ledger)
    counts = {}
    for e in ledger:
        counts[e["status"]] = counts.get(e["status"], 0) + 1

    result = {
        "as_of": args.as_of,
        "total": len(ledger),
        "status_counts": counts,
        "aging_buckets": buckets,
        "entries": ledger,
    }
    if args.compare:
        try:
            with open(args.compare, "r", encoding="utf-8") as f:
                prev = json.load(f)
            if isinstance(prev, dict):
                prev = prev.get("entries", [])
            result["trend"] = trend(ledger, prev)
        except Exception as exc:
            print("error: cannot read previous ledger: %s" % exc, file=sys.stderr)
            return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("as_of=%s total=%d" % (result["as_of"], result["total"]))
        for k in sorted(counts):
            print("  %-13s %d" % (k, counts[k]))
        print("aging: " + ", ".join("%s=%d" % (k, v) for k, v in buckets.items()))
        if "trend" in result:
            print("trend: " + ", ".join("%s=%+d" % (k, v) for k, v in result["trend"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
