#!/usr/bin/env python3
"""Fixture-based regression test for wmgt_batch_hash.py. Run:
    python scripts/wmgt_test_batch_hash.py

Runs the script as a subprocess against fixture files in a temporary directory and
asserts on exit code and JSON output. Exits 0 when every case passes, 1 otherwise.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "wmgt_batch_hash.py"


def run_script(script, *args):
    proc = subprocess.run(
        [sys.executable, str(script), *args], capture_output=True, text=True, check=False
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError:
        return proc.returncode, {
            "ok": False,
            "error": "non-json output",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }


def run(*args):
    return run_script(SCRIPT, *args)


def submission(records, **overrides):
    base = {
        "operation": "create",
        "environment": "production",
        "team_id": "team-1",
        "batch_id": "batch-0001",
        "records": records,
    }
    base.update(overrides)
    return json.dumps(base)


def update_record(i=0, **overrides):
    rec = {
        "id": f"ISSUE-{i}",
        "set": {"status": "Todo"},
        "before": {"title": "T", "status": "Backlog"},
    }
    rec.update(overrides)
    return rec


def main() -> int:
    failures = []

    def check(name, condition):
        if not condition:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        def write(name, text, directory=tmp_path):
            path = directory / name
            path.write_text(text, encoding="utf-8")
            return str(path)

        recs = [{"title": "x", "description": "dx"}, {"title": "y"}, {"title": "z"}]
        a = write("a.json", submission(recs))

        # --- hash / verify -------------------------------------------------------------
        rc, out = run("hash", a)
        check("hash succeeds", rc == 0 and out["ok"] and out["record_count"] == 3)
        digest = out["sha256"]
        check("digest is 64 hex", len(digest) == 64)

        reordered = write(
            "reordered.json",
            '{"records": [{"title": "x", "description": "dx"}, {"title": "y"}, {"title": "z"}],\n'
            ' "batch_id": "batch-0001", "team_id": "team-1",'
            ' "environment": "production", "operation": "create"}',
        )
        rc, out = run("hash", reordered)
        check(
            "key order and whitespace do not change the hash", rc == 0 and out["sha256"] == digest
        )

        for label, text in [
            ("a changed record", submission([recs[0], recs[1], {"title": "w"}])),
            ("record order", submission([recs[1], recs[0], recs[2]])),
            ("a different team", submission(recs, team_id="team-2")),
            ("a different environment", submission(recs, environment="test")),
            ("a different batch_id", submission(recs, batch_id="batch-0002")),
        ]:
            rc, out = run("hash", write("v.json", text))
            check(f"{label} changes the hash", rc == 0 and out["sha256"] != digest)

        rc, out = run("verify", a, digest)
        check("verify accepts the matching hash", rc == 0 and out["ok"])
        rc, out = run("verify", write("v2.json", submission([{"title": "q"}])), digest)
        check("verify rejects a changed set", rc == 1 and "hash mismatch" in out["error"])
        rc, out = run("verify", a, "ABC")
        check("verify rejects a malformed expected hash", rc == 1 and not out["ok"])

        # --- chunk ---------------------------------------------------------------------
        rc, out = run("chunk", a, digest, "1", "3")
        check(
            "chunk returns exactly the hashed records",
            rc == 0 and out["records"] == recs[1:3] and out["start"] == 1,
        )
        check(
            "chunk prints the verified operation, environment and team",
            out.get("operation") == "create"
            and out.get("environment") == "production"
            and out.get("team_id") == "team-1",
        )
        check("chunk reports its byte size", isinstance(out.get("bytes"), int) and out["bytes"] > 0)
        rc, out = run("chunk", a, digest, "2", "5")
        check("chunk range past the end refused", rc == 1 and not out["ok"])
        rc, out = run("chunk", a, digest, "2", "2")
        check("empty chunk range refused", rc == 1 and not out["ok"])
        rc, out = run("chunk", a, "0" * 64, "0", "1")
        check(
            "chunk refuses a mismatched hash and emits no records", rc == 1 and "records" not in out
        )

        many = write("many.json", submission([{"title": f"t{i}"} for i in range(60)]))
        rc, out = run("hash", many)
        many_digest = out["sha256"]
        rc, out = run("chunk", many, many_digest, "0", "25")
        check("a 25-record chunk is allowed", rc == 0 and len(out["records"]) == 25)
        rc, out = run("chunk", many, many_digest, "0", "26")
        check("a chunk over 25 records refused", rc == 1 and not out["ok"])

        fat = write(
            "fat.json",
            submission([{"title": f"t{i}", "description": "d" * 2000} for i in range(25)]),
        )
        rc, out = run("hash", fat)
        fat_digest = out["sha256"]
        rc, out = run("chunk", fat, fat_digest, "0", "25")
        check(
            "a chunk over the byte cap refused with a smaller-range hint",
            rc == 1 and "smaller range" in out["error"],
        )
        rc, out = run("chunk", fat, fat_digest, "0", "5")
        check("a smaller range of the same file is allowed", rc == 0 and len(out["records"]) == 5)

        # --- show / preview ------------------------------------------------------------
        rc, out = run("show", a, digest)
        check(
            "show prints the header without records",
            rc == 0
            and out["submission"]["team_id"] == "team-1"
            and "records" not in out["submission"]
            and out["record_count"] == 3,
        )
        rc, out = run("show", a, "0" * 64)
        check(
            "show refuses a mismatched hash and prints nothing", rc == 1 and "submission" not in out
        )

        rc, out = run("preview", a, digest, "0", "3")
        check(
            "preview returns one row per record and full text of the first three",
            rc == 0
            and len(out["rows"]) == 3
            and out["rows"][0]["title"] == "x"
            and out["full_descriptions"][0] == {"index": 0, "description": "dx"},
        )
        rc, out = run("preview", many, many_digest, "1", "5")
        check(
            "preview with start 1 prints full text only for indices 1 and 2",
            rc == 0 and [d["index"] for d in out["full_descriptions"]] == [1, 2],
        )
        rc, out = run("preview", many, many_digest, "3", "8")
        check(
            "preview with start 3 prints no full descriptions",
            rc == 0 and out["full_descriptions"] == [],
        )

        rc, out = run("preview", fat, fat_digest, "0", "3")
        check(
            "preview excerpts long descriptions",
            rc == 0 and out["rows"][0]["description_excerpt"].endswith("..."),
        )
        rc, out = run("preview", many, many_digest, "0", "60")
        check("preview of 60 short rows is allowed", rc == 0 and len(out["rows"]) == 60)
        big = write("big.json", submission([{"title": f"t{i}"} for i in range(150)]))
        rc, out = run("hash", big)
        rc, out = run("preview", big, out["sha256"], "0", "101")
        check("preview over 100 rows refused", rc == 1 and not out["ok"])
        rc, out = run("preview", a, "0" * 64, "0", "1")
        check("preview refuses a mismatched hash", rc == 1 and "rows" not in out)

        # --- validation ----------------------------------------------------------------
        dup_top = write(
            "dup_top.json",
            '{"operation":"create","environment":"production","team_id":"A","team_id":"B","batch_id":"batch-0001","records":[{"title":"t"}]}',
        )
        rc, out = run("hash", dup_top)
        check("duplicate top-level key refused", rc == 1 and "duplicate" in out["error"])
        dup_rec = write(
            "dup_rec.json",
            '{"operation":"create","environment":"production","team_id":"A","batch_id":"batch-0001","records":[{"title":"1","title":"2"}]}',
        )
        rc, out = run("hash", dup_rec)
        check("duplicate key inside a record refused", rc == 1 and "duplicate" in out["error"])

        for label, text in [
            ("unknown operation", submission(recs, operation="delete")),
            ("unknown environment", submission(recs, environment="staging")),
            ("blank team_id", submission(recs, team_id="  ")),
            (
                "missing batch_id",
                json.dumps(
                    {"operation": "create", "environment": "test", "team_id": "t", "records": recs}
                ),
            ),
            ("short batch_id", submission(recs, batch_id="abc")),
            ("empty records", submission([])),
            ("non-object top level", "[1, 2]"),
            ("invalid JSON", "{not json"),
            ("create record with a team override", submission([{"title": "t", "team": "other"}])),
            ("create record with a parent", submission([{"title": "t", "parent": "X-1"}])),
            ("create record that is empty", submission([{}])),
            ("create record with an owner", submission([{"title": "t", "owner": "someone"}])),
            (
                "create record with dependencies",
                submission([{"title": "t", "dependencies": ["X-1"]}]),
            ),
            ("create record with a cycle", submission([{"title": "t", "cycle": "c1"}])),
            (
                "create title that is not a string",
                submission([{"title": {"id": "x", "teamId": "y"}}]),
            ),
            (
                "create labels as objects",
                submission([{"title": "t", "labels": [{"name": "x", "teamId": "y"}]}]),
            ),
            (
                "create labels over the cap",
                submission([{"title": "t", "labels": [f"l{i}" for i in range(21)]}]),
            ),
            ("create empty label string", submission([{"title": "t", "labels": [""]}])),
            ("unexpected top-level key", submission(recs, project="P-1")),
            (
                "update set value that is null",
                submission([update_record(set={"status": None})], operation="update"),
            ),
            (
                "update before missing the title",
                submission([update_record(before={"status": "Backlog"})], operation="update"),
            ),
            (
                "update before missing a set field",
                submission([update_record(set={"priority": "High"})], operation="update"),
            ),
            (
                "update owner as an object",
                submission(
                    [
                        update_record(
                            set={"owner": {"id": "u"}}, before={"title": "T", "owner": None}
                        )
                    ],
                    operation="update",
                ),
            ),
            (
                "update record without id",
                submission([{"set": {"status": "Todo"}}], operation="update"),
            ),
            (
                "update record with an extra key",
                submission([update_record(team="other")], operation="update"),
            ),
            (
                "update set with description",
                submission([update_record(set={"description": "x"})], operation="update"),
            ),
            (
                "update set with team",
                submission([update_record(set={"team": "x"})], operation="update"),
            ),
            ("update set empty", submission([update_record(set={})], operation="update")),
            (
                "update before with a stray field",
                submission([update_record(before={"description": "x"})], operation="update"),
            ),
            (
                "update without before",
                submission([{"id": "I-1", "set": {"status": "Todo"}}], operation="update"),
            ),
        ]:
            rc, out = run("hash", write("bad.json", text))
            check(f"{label} refused", rc == 1 and not out["ok"])

        upd_null_before = write(
            "upd_null.json",
            submission(
                [update_record(set={"owner": "u-1"}, before={"title": "T", "owner": None})],
                operation="update",
            ),
        )
        rc, out = run("hash", upd_null_before)
        check("update before may hold null for an unset field", rc == 0 and out["ok"])

        deep = write("deep.json", "[" * 100000 + "]" * 100000)
        rc, out = run("hash", deep)
        check(
            "deeply nested JSON gives a typed failure, not a traceback", rc == 1 and not out["ok"]
        )

        upd = write(
            "upd.json", submission([update_record(0), update_record(1)], operation="update")
        )
        rc, out = run("hash", upd)
        check("a well-formed update submission is accepted", rc == 0 and out["record_count"] == 2)
        upd_digest = out["sha256"]
        rc, out = run("preview", upd, upd_digest, "0", "2")
        check(
            "update preview shows id, title and before/after",
            rc == 0
            and out["rows"][0]["id"] == "ISSUE-0"
            and out["rows"][0]["title"] == "T"
            and out["rows"][0]["before"]["status"] == "Backlog",
        )

        rc, out = run("hash", str(tmp_path / "missing.json"))
        check("missing file gives a typed failure", rc == 1 and not out["ok"])
        rc, out = run("hash", str(tmp_path))
        check("directory refused", rc == 1 and not out["ok"])
        rc, out = run("hash", write("toomany.json", submission([{"t": i} for i in range(1001)])))
        check("more than 1000 records refused", rc == 1 and not out["ok"])

        # --- purge ---------------------------------------------------------------------
        scratch = tmp_path / "wmgt-intake"
        scratch.mkdir()
        sub_file = scratch / "batch-0001.json"
        sub_file.write_text("{}", encoding="utf-8")
        progress = scratch / ("a" * 64 + "-batch-0001.progress.json")
        progress.write_text("[]", encoding="utf-8")
        rc, out = run("purge", str(tmp_path), str(sub_file))
        check(
            "purge deletes an intake-named submission file",
            rc == 0 and out["purged"] and not sub_file.exists(),
        )
        rc, out = run("purge", str(tmp_path), str(progress))
        check(
            "purge deletes an intake-named progress file",
            rc == 0 and out["purged"] and not progress.exists(),
        )

        outside = Path(write("outside.json", "{}"))
        rc, out = run("purge", str(tmp_path), str(outside))
        check("purge refuses a file outside wmgt-intake", rc == 1 and outside.exists())

        elsewhere = tmp_path / "elsewhere" / "wmgt-intake"
        elsewhere.mkdir(parents=True)
        decoy = elsewhere / "batch-0002.json"
        decoy.write_text("{}", encoding="utf-8")
        rc, out = run("purge", str(tmp_path), str(decoy))
        check(
            "purge refuses a wmgt-intake directory under a different root",
            rc == 1 and decoy.exists(),
        )

        for short in ("a.json", "1234567.json"):
            short_file = scratch / short
            short_file.write_text("{}", encoding="utf-8")
            rc, out = run("purge", str(tmp_path), str(short_file))
            check(
                f"purge refuses the {len(short) - 5}-character name {short}",
                rc == 1 and short_file.exists(),
            )
        eight = scratch / "12345678.json"
        eight.write_text("{}", encoding="utf-8")
        rc, out = run("purge", str(tmp_path), str(eight))
        check("purge accepts an 8-character batch id", rc == 0 and not eight.exists())

        target = Path(write("symlink-target.json", "{}"))
        link = scratch / "12345678-link.json"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            link = None  # this platform cannot create a symlink here; the case is skipped
        if link is not None:
            rc, out = run("purge", str(tmp_path), str(link))
            check(
                "purge refuses a symlink and leaves its target alone",
                rc == 1 and target.exists() and link.is_symlink(),
            )

        odd = scratch / "notes.txt"
        odd.write_text("x", encoding="utf-8")
        rc, out = run("purge", str(tmp_path), str(odd))
        check("purge refuses a name intake does not generate", rc == 1 and odd.exists())
        settings = scratch / "settings!.json"
        settings.write_text("{}", encoding="utf-8")
        rc, out = run("purge", str(tmp_path), str(settings))
        check("purge refuses a name outside the generated pattern", rc == 1 and settings.exists())
        folder_named_like_a_file = scratch / "dir-12345.json"
        folder_named_like_a_file.mkdir()
        rc, out = run("purge", str(tmp_path), str(folder_named_like_a_file))
        check(
            "purge refuses a folder named like an intake file",
            rc == 1 and folder_named_like_a_file.exists(),
        )

        no_scratch_root = tmp_path / "no-scratch"
        no_scratch_root.mkdir()
        rc, out = run(
            "purge", str(no_scratch_root), str(no_scratch_root / "wmgt-intake" / "missing1.json")
        )
        check("purge with no wmgt-intake folder is a typed failure", rc == 1 and not out["ok"])

        rc, out = run("purge", str(tmp_path), str(scratch / "missing1.json"))
        check("purge of a missing file is a typed failure", rc == 1 and not out["ok"])
        rc, out = run("purge", str(tmp_path), str(scratch / ".." / "outside.json"))
        check("purge refuses a path that climbs out of wmgt-intake", rc == 1 and outside.exists())

        silent = tmp_path / "silent.py"
        silent.write_text("pass\n", encoding="utf-8")
        rc, out = run_script(silent)
        check(
            "the harness reports empty output as a failed case",
            out["ok"] is False and out["error"] == "non-json output",
        )
        noisy = tmp_path / "noisy.py"
        noisy.write_text("print('not json')\n", encoding="utf-8")
        rc, out = run_script(noisy)
        check(
            "the harness reports non-JSON output as a failed case",
            out["ok"] is False and out["stdout"].strip() == "not json",
        )

        rc, out = run("bogus")
        check("invalid arguments give a typed failure", rc == 1 and not out["ok"])

    for name in failures:
        print("FAIL  " + name)
    if not failures:
        print("PASS  all wmgt_batch_hash.py cases")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
