#!/usr/bin/env python3
"""Self test for todo-expiry-ledger. Run: python self_test.py
Last line: SUMMARY: PASS n/n"""

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import todo_expiry_ledger as tel

PASS = 0
FAIL = 0
FAILED = []


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILED.append(name)


def run_cli(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = tel.main(argv)
    return code, buf.getvalue()


# ---------- functional ----------
e = tel.parse_todo("x = 1  # TODO(2026-10-20, @alice): fix the thing")
check("parse_basic", e and e["due"] == "2026-10-20" and e["owner"] == "alice" and "fix the thing" in e["message"])
e = tel.parse_todo("# TODO(@bob): no date here")
check("parse_owner_only", e and e["owner"] == "bob" and e["due"] is None)
e = tel.parse_todo("// TODO(2026-12-01): owner in message @carol")
check("parse_owner_in_message", e and e["owner"] == "carol" and e["due"] == "2026-12-01")
e = tel.parse_todo("TODO: bare marker no parens")
check("parse_bare", e and e["due"] is None and e["owner"] is None)
e = tel.parse_todo("TODO(2026-13-45): bad date")
check("parse_invalid_date_flagged", e and e["invalid_date"] == "2026-13-45")
check("parse_non_todo_returns_none", tel.parse_todo("plain text without marker") is None)
check("parse_empty_line_returns_none", tel.parse_todo("") is None)
e = tel.parse_todo("todo(2026-01-02) lowercase marker works")
check("parse_case_insensitive", e and e["due"] == "2026-01-02")

led = tel.build_ledger([
    {"file": "a", "line": 1, "message": "m", "due": "2026-10-01", "owner": None, "invalid_date": None},
    {"file": "b", "line": 2, "message": "m", "due": "2026-10-15", "owner": None, "invalid_date": None},
    {"file": "c", "line": 3, "message": "m", "due": "2026-11-30", "owner": None, "invalid_date": None},
    {"file": "d", "line": 4, "message": "m", "due": None, "owner": None, "invalid_date": None},
], "2026-10-11")
check("classify_overdue", led[0]["status"] == "overdue" and led[0]["days_overdue"] == 10)
check("classify_due_soon", led[1]["status"] == "due_soon" and led[1]["days_left"] == 4)
check("classify_open", led[2]["status"] == "open")
check("classify_no_due", led[3]["status"] == "no_due")
led2 = tel.build_ledger([{"due": "2026-13-01", "invalid_date": "2026-13-01", "file": "x", "line": 1, "message": "", "owner": None}], "2026-10-11")
check("classify_invalid_date", led2[0]["status"] == "invalid_date")

b = tel.aging_buckets(led + led2)
check("buckets_not_overdue", b["not_overdue"] == 4)
check("buckets_1_7", b["overdue_1_7"] == 0)
check("buckets_8_30", b["overdue_8_30"] == 1)
check("buckets_empty_all_zero", all(tel.aging_buckets([])[k] == 0 for k in tel.BUCKETS))
led3 = tel.build_ledger([{"due": "2026-01-01", "invalid_date": None, "file": "x", "line": 1, "message": "", "owner": None}], "2026-10-11")
check("buckets_90_plus", tel.aging_buckets(led3)["overdue_90_plus"] == 1)
led4 = tel.build_ledger([{"due": "2026-08-20", "invalid_date": None, "file": "x", "line": 1, "message": "", "owner": None}], "2026-10-11")
check("buckets_31_90", tel.aging_buckets(led4)["overdue_31_90"] == 1)

tr = tel.trend(led, [])
check("trend_vs_empty", tr["overdue"] == 1 and tr["open"] == 1)
tr = tel.trend(led, led)
check("trend_self_zero", all(v == 0 for v in tr.values()))

check("valid_date_ok", tel.valid_date("2026-02-29") is None)  # 2026 not a leap year
check("valid_date_leap", tel.valid_date("2024-02-29") == "2024-02-29")
check("valid_date_garbage", tel.valid_date("not-a-date") is None)
check("days_diff_sign", tel.days_diff("2026-10-01", "2026-10-11") == -10 and tel.days_diff("2026-10-21", "2026-10-11") == 10)

tmp = tempfile.mkdtemp()
with open(os.path.join(tmp, "sample.py"), "w", encoding="utf-8") as f:
    f.write("# TODO(2026-10-01, @dan): first\ndef f():\n    pass  # TODO: second\n")
with open(os.path.join(tmp, "notes.md"), "w", encoding="utf-8") as f:
    f.write("- TODO(2026-11-01) @erin: docs\n")
with open(os.path.join(tmp, "empty.txt"), "w", encoding="utf-8") as f:
    f.write("")
found = tel.scan_directory(tmp)
check("scan_finds_all", len(found) == 3)
check("scan_filenames_sorted", [x["file"] for x in found] == sorted(x["file"] for x in found))
check("scan_ext_filter", len(tel.scan_directory(tmp, extensions={".py"})) == 2)
try:
    tel.scan_directory(os.path.join(tmp, "definitely_missing_dir"))
    check("scan_missing_raises", False)
except FileNotFoundError:
    check("scan_missing_raises", True)

code, out = run_cli(["scan", tmp, "--as-of", "2026-10-11", "--json"])
r = json.loads(out)
check("cli_json_total", code == 0 and r["total"] == 3)
check("cli_status_counts", r["status_counts"].get("overdue") == 1)
code, out = run_cli(["scan", tmp, "--as-of", "2026-10-11"])
check("cli_human_mode", code == 0 and "as_of=2026-10-11" in out)
prev_file = os.path.join(tmp, "prev.json")
with open(prev_file, "w", encoding="utf-8") as f:
    json.dump({"entries": [{"status": "overdue"}] * 5}, f)
code, out = run_cli(["scan", tmp, "--as-of", "2026-10-11", "--json", "--compare", prev_file])
r = json.loads(out)
check("cli_trend_delta", code == 0 and r["trend"].get("overdue") == -4)

# ---------- exception paths ----------
check("parse_none_input", tel.parse_todo(None) is None)
try:
    tel.days_diff("garbage-date", "2026-10-11")
    check("days_diff_raises", False)
except Exception:
    check("days_diff_raises", True)
try:
    tel.days_diff("2026-02-30", "2026-10-11")
    check("days_diff_feb30_raises", False)
except Exception:
    check("days_diff_feb30_raises", True)
code, out = run_cli(["scan", os.path.join(tmp, "missing_file.py")])
check("cli_missing_file_exit2", code == 2)
code, out = run_cli(["scan", tmp, "--as-of", "2026-10-11", "--compare", os.path.join(tmp, "no.json")])
check("cli_bad_compare_exit2", code == 2)
with open(os.path.join(tmp, "bin.dat"), "wb") as f:
    f.write(b"\x00\x01TODO(2026-01-01) binary")
check("scan_skips_binary", len(tel.scan_directory(tmp, extensions={".dat"})) == 0)
with open(os.path.join(tmp, "bad_utf8.py"), "wb") as f:
    f.write(b"# TODO(2026-01-01) \xff\xfe garbage bytes")
check("scan_replaces_bad_utf8", len(tel.scan_directory(tmp, extensions={".py"})) == 3)
try:
    tel.build_ledger([{"due": "not-a-date", "invalid_date": None, "file": "x", "line": 1, "message": "", "owner": None}], "2026-10-11")
    check("classify_garbage_date_safe", True)  # falls back to invalid_date
except Exception:
    check("classify_garbage_date_safe", tel.build_ledger([{"due": "not-a-date", "invalid_date": None, "file": "x", "line": 1, "message": "", "owner": None}], "2026-10-11")[0]["status"] == "invalid_date")
ledg = tel.build_ledger([{"due": "not-a-date", "invalid_date": None, "file": "x", "line": 1, "message": "", "owner": None}], "2026-10-11")
check("classify_garbage_becomes_invalid", ledg[0]["status"] == "invalid_date")
code, out = run_cli(["scan", tmp, "--as-of", "bad-as-of"])
check("cli_bad_asof_handled", code in (0, 2))

# ---------- extreme edge cases ----------
check("edge_very_long_line", tel.parse_todo("TODO(" + "9" * 5000 + "): " + "x" * 10000) is not None)
check("edge_unicode_todo", (tel.parse_todo("# TODO(2026-11-11, @阿明): 修复 中文 message ☃"))["owner"] == "阿明")
check("edge_unicode_roundtrip", json.dumps(tel.parse_todo("# TODO(2026-11-11): 日本語テキスト"), ensure_ascii=False))
deep = os.path.join(tmp, *(["d%d" % i for i in range(30)]))
os.makedirs(deep, exist_ok=True)
with open(os.path.join(deep, "deep.py"), "w", encoding="utf-8") as f:
    f.write("# TODO(2026-12-12): deep nest")
check("edge_deep_dir_scan", any(x["file"].endswith("deep.py") for x in tel.scan_directory(tmp)))
with open(os.path.join(tmp, "crlf.py"), "w", encoding="utf-8", newline="\r\n") as f:
    f.write("# TODO(2026-12-25): crlf line\r\nplain\r\n")
check("edge_crlf", any(x["due"] == "2026-12-25" for x in tel.scan_directory(tmp, extensions={".py"})))
e = tel.parse_todo("TODO((")
check("edge_unbalanced_parens", e is not None and e["due"] is None)
e = tel.parse_todo("TODO(   ): whitespace only inner")
check("edge_blank_inner", e is not None)
e = tel.parse_todo("TODO(2026-10-20, 2026-11-20, @a, @b): two dates two owners")
check("edge_multi_tokens_first_wins", e["due"] == "2026-10-20" and e["owner"] == "a")
e = tel.parse_todo("TODO" + " " * 200 + "(2026-10-20): spaced")
check("edge_many_spaces", e is not None and e["due"] == "2026-10-20")
empty_dir = tempfile.mkdtemp()
check("edge_empty_dir", tel.scan_directory(empty_dir) == [])
code, out = run_cli(["scan", empty_dir, "--as-of", "2026-10-11", "--json"])
r = json.loads(out)
check("edge_empty_dir_cli", r["total"] == 0 and all(v == 0 for v in r["aging_buckets"].values()))
e = tel.parse_todo("TODO(): no message no date")
check("edge_empty_parens", e is not None and e["message"] == "no message no date")
check("edge_message_truncated", len(tel.parse_todo("TODO: " + "y" * 5000)["message"]) == 200)
e = tel.parse_todo("TODO(2026-01-01)@leader: owner glued")
check("edge_owner_glued", e["owner"] == "leader")

print()
if FAILED:
    print("FAILED CASES:", ", ".join(FAILED))
print("SUMMARY: PASS %d/%d" % (PASS, PASS + FAIL))
sys.exit(1 if FAIL else 0)
