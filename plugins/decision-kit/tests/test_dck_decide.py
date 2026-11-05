"""Tests dck-decide.py against a local fake server. No network, no real key."""

import ast
import importlib.util
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

SKILL = Path(__file__).resolve().parents[1] / "skills" / "consulting-decision-model"
SPEC = importlib.util.spec_from_file_location("dck_decide", SKILL / "scripts" / "dck-decide.py")
assert SPEC is not None and SPEC.loader is not None
sys.dont_write_bytecode = True
dck = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dck)

PIN = "liquid/d1-ultra-20261015"
FALL = "baseten/elephant-1-20261021"
FAKE_KEY = "test-placeholder-value"


def answer(model, safe=0.99, risk=0.2, choice=None):
    answers = {
        "safe_to_proceed": {"type": "noul", "noul": safe},
        "risk": {"type": "score", "score": risk},
    }
    if choice:
        answers["best_option"] = {"type": "choice", "choice": choice}
    return {"model": model, "answers": answers, "usage": {"cost": 0.0001}}


@pytest.fixture(autouse=True)
def no_proxy_for_the_local_server(monkeypatch):
    monkeypatch.setenv("no_proxy", "127.0.0.1")


@pytest.fixture
def server():
    state: dict[str, Any] = {"requests": [], "reply": {}, "listing": {"data": []}, "headers": []}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def _send(self, status, body):
            raw = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            state["headers"].append(dict(self.headers))
            self._send(200, state["listing"])

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["requests"].append(body)
            status, reply = state["reply"].get(body["model"], (500, b""))
            self._send(status, reply)

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    state["base"] = f"http://127.0.0.1:{httpd.server_port}"
    yield state
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    return tmp_path


def decision(**over):
    base = {
        "trigger": "security",
        "action": "Add a scoped grant.",
        "state": "The skill deletes files under .temp/ only.",
        "claude_position": "proceed",
        "claude_risk": "low",
    }
    return {**base, **over}


def test_agreement_proceeds_and_records(server, repo):
    server["reply"][PIN] = (200, answer(PIN))
    out = dck.run(decision(), server["base"], repo)
    assert (out["verdict"], out["reason"], out["source"]) == ("no_stop", "agree", "primary")
    assert server["requests"][0]["provider"] == {"zdr": True}
    record = Path(out["record"]).read_text(encoding="utf-8")
    assert "Add a scoped grant" in record and FAKE_KEY not in record
    assert (repo / ".claude/decision-kit/.gitignore").read_text(encoding="utf-8") == "*\n"


@pytest.mark.parametrize(
    "position,safe,reason",
    [
        ("proceed", 0.50, "uncertain"),
        ("proceed", 0.10, "disagree"),
        ("stop", 0.10, "agree_stop"),
        ("stop", 0.50, "uncertain"),
        ("stop", 0.99, "disagree"),
    ],
)
def test_everything_but_agreement_asks(server, repo, position, safe, reason):
    server["reply"][PIN] = (200, answer(PIN, safe=safe))
    out = dck.run(decision(claude_position=position), server["base"], repo)
    assert (out["verdict"], out["reason"]) == ("ask_user", reason)


def test_threshold_edges(server, repo):
    server["reply"][PIN] = (200, answer(PIN, safe=0.95))
    assert dck.run(decision(), server["base"], repo)["verdict"] == "no_stop"
    server["reply"][PIN] = (200, answer(PIN, safe=0.949))
    assert dck.run(decision(), server["base"], repo)["reason"] == "uncertain"


def test_stop_threshold_edges(server, repo):
    server["reply"][PIN] = (200, answer(PIN, safe=0.2))
    out = dck.run(decision(claude_position="stop"), server["base"], repo)
    assert out["reason"] == "agree_stop"
    server["reply"][PIN] = (200, answer(PIN, safe=0.21))
    out = dck.run(decision(claude_position="stop"), server["base"], repo)
    assert out["reason"] == "uncertain"


def test_missing_best_option_is_not_an_answer(server, repo):
    server["reply"][PIN] = (200, answer(PIN))
    server["reply"][FALL] = (200, answer(FALL))
    data = decision(options={"a": "one", "b": "two"}, claude_choice="a")
    assert dck.run(data, server["base"], repo)["verdict"] == "ask_user"


def test_unknown_best_option_is_not_an_answer(server, repo):
    server["reply"][PIN] = (200, answer(PIN, choice="c"))
    server["reply"][FALL] = (200, answer(FALL, choice="c"))
    data = decision(options={"a": "one", "b": "two"}, claude_choice="a")
    assert dck.run(data, server["base"], repo)["verdict"] == "ask_user"


def test_record_is_owner_only(server, repo):
    server["reply"][PIN] = (200, answer(PIN))
    out = dck.run(decision(), server["base"], repo)
    assert Path(out["record"]).stat().st_mode & 0o777 == 0o600


def test_higher_risk_asks(server, repo):
    server["reply"][PIN] = (200, answer(PIN, risk=2.0))
    assert dck.run(decision(), server["base"], repo)["reason"] == "disagree_on_risk"


def test_other_option_asks(server, repo):
    server["reply"][PIN] = (200, answer(PIN, choice="b"))
    data = decision(options={"a": "first", "b": "second"}, claude_choice="a")
    assert dck.run(data, server["base"], repo)["reason"] == "disagree_on_option"


@pytest.mark.parametrize(
    "status,body",
    [
        (429, b""),
        (503, b""),
        (404, b"No endpoints found matching your data policy"),
        (400, b'{"message": "Model x does not exist"}'),
        (200, b"not json"),
        (200, answer("some/other-model")),
    ],
)
def test_fallback_is_labelled(server, repo, status, body):
    server["reply"][PIN] = (status, body)
    server["reply"][FALL] = (200, answer(FALL))
    out = dck.run(decision(), server["base"], repo)
    assert (out["verdict"], out["source"], out["model"]) == ("no_stop", "fallback", FALL)
    assert all(r["provider"] == {"zdr": True} for r in server["requests"])


@pytest.mark.parametrize("status", [401, 402, 403, 413])
def test_no_fallback_when_it_would_fail_alike(server, repo, status):
    server["reply"][PIN] = (status, b"")
    out = dck.run(decision(), server["base"], repo)
    assert len(server["requests"]) == 1
    assert (out["verdict"], out["reason"]) == ("ask_user", "unavailable")


def test_expired_pin_skips_to_fallback_and_warns(server, repo):
    server["listing"] = {"data": [{"canonical_slug": PIN, "expiration_date": "2027-01-01"}]}
    server["reply"][FALL] = (200, answer(FALL))
    out = dck.run(decision(), server["base"], repo)
    assert [r["model"] for r in server["requests"]] == [FALL]
    assert any("re-pin" in w for w in out["warnings"])
    assert not any("Authorization" in h for h in server["headers"])


@pytest.mark.parametrize(
    "trigger,verdict",
    [("critical", "ask_user"), ("security", "ask_user"), ("confidence", "no_second_opinion")],
)
def test_both_models_down(server, repo, trigger, verdict):
    out = dck.run(decision(trigger=trigger), server["base"], repo)
    assert (out["verdict"], out["reason"]) == (verdict, "unavailable")


def test_high_risk_confidence_decision_asks_when_down(server, repo):
    out = dck.run(decision(trigger="confidence", claude_risk="high"), server["base"], repo)
    assert out["verdict"] == "ask_user"


@pytest.mark.parametrize("bad", ["abc\r", "abc\n", "a b"])
def test_malformed_key_sends_nothing_and_stays_out_of_output(server, repo, monkeypatch, bad):
    monkeypatch.setenv("OPENROUTER_API_KEY", bad)
    out = dck.run(decision(), server["base"], repo)
    assert out["verdict"] == "ask_user" and not server["requests"]
    assert bad not in json.dumps(out)
    assert json.dumps(bad)[1:-1] not in json.dumps(out)


def test_no_key_sends_nothing(server, repo, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY")
    out = dck.run(decision(trigger="critical"), server["base"], repo)
    assert out["verdict"] == "ask_user" and not server["requests"]


@pytest.mark.parametrize(
    "over",
    [
        {"state": "token ghp_" + "a" * 36},
        {"state": f"key is {FAKE_KEY}"},
        {"state": "x" * (dck.MAX_STATE_CHARS + 1)},
        {"options": {"ghp_" + "a" * 36: "one", "b": "two"}, "claude_choice": "b"},
        {"state": "%20sk-" + "a" * 24},
        {"state": "line\\nsk-" + "a" * 24},
        {"state": "API_KEY_sk-" + "a" * 24},
        {"state": "API_KEY_ghp_" + "a" * 36},
        {"state": "token%3Dghp_" + "a" * 36},
        {"state": "%2520ghp_" + "a" * 36},
        {"state": "line\\nghp_" + "a" * 36},
        {"state": "-----BEGIN RSA PRIVATE KEY-----"},
        {"state": "postgres://user:hunter22@db/x"},
        {"state": "password=correcthorse"},
        {"state": "redis://:s3cretpassw0rd@host:6379"},
        {"state": "SECRET_KEY=" + "a" * 16},
        {"state": "aws_secret_access_key = wJalrXUtnFEMI"},
        {"state": "TOKEN=" + "a" * 16},
        {"state": "access_token: " + "a" * 16},
        {"state": "Authorization: Bearer " + "a" * 16},
        {"state": "'Authorization': 'Bearer " + "a" * 16 + "'"},
        {"state": "'Authorization' => 'Bearer " + "a" * 16 + "'"},
        {"state": "GITHUB_TOKEN=" + "a" * 16},
        {"state": "AWS_SESSION_TOKEN=" + "a" * 16},
        {"state": "POSTGRES://user:hunter22@db/x"},
        {"state": "ASIA" + "A" * 16},
        {"state": "API_KEY_ASIA" + "A" * 16},
        {"state": "password\\u003dhunter2hunter"},
        {"state": "line\\\\nghp_" + "a" * 36},
        {"state": "postgres:\\\\/\\\\/user:hunter22@db"},
        {"state": "ya29." + "a" * 24},
        {"state": "hf_" + "a" * 34},
        {"state": "xapp-" + "1" * 24},
        {"state": "https://hooks.slack.com/services/" + "a" * 12},
        {"state": "whsec_" + "a" * 24},
        {"state": "pypi-" + "a" * 54},
        {"state": "dop_v1_" + "a" * 44},
        {"state": "SG." + "a" * 18 + "." + "b" * 18},
        {"state": "line\\u0022ghp_" + "a" * 36},
        {"state": "postgres:\\/\\/user:hunter22@db"},
        {"state": "{'password': 'hunter2hunter'}"},
        {"state": "'password' => 'hunter2hunter'"},
        {"options": {"a": "x" * dck.MAX_STATE_CHARS, "b": "two"}, "claude_choice": "b"},
        {"trigger": ["critical"]},
        {"trigger": {}},
        {"claude_risk": []},
        {"options": {"a": "1", "b": "2"}, "claude_choice": ["a"]},
        {"trigger": "other"},
        {"claude_risk": "huge"},
        {"options": {"a": "only"}, "claude_choice": "a"},
    ],
)
def test_refused_sends_and_records_nothing(server, repo, over):
    out = dck.run(decision(**over), server["base"], repo)
    assert out["verdict"] == "refused"
    assert not server["requests"] and not (repo / ".claude/decision-kit").exists()


def test_unreadable_patterns_refuse(tmp_path, monkeypatch):
    monkeypatch.setattr(dck, "SKILL_DIR", tmp_path)
    assert dck.screen(["text"], "") == "the secret patterns could not be loaded"


def _local(repo, **values):
    (repo / ".claude").mkdir(exist_ok=True)
    (repo / dck.LOCAL_SETTINGS).write_text(json.dumps(values), encoding="utf-8")


def test_override_is_found_from_a_subdirectory(repo):
    _local(repo, enabled=False)
    nested = repo / "a" / "b"
    nested.mkdir(parents=True)
    assert dck.project_root(nested) == repo


def test_run_from_a_subdirectory_uses_the_parent_override(server, repo, monkeypatch):
    _local(repo, proceed_max_p_block=0.5)
    nested = repo / "a"
    nested.mkdir()
    monkeypatch.chdir(nested)
    server["reply"][PIN] = (200, answer(PIN, safe=0.6))
    out = dck.run(decision(), server["base"])
    assert out["verdict"] == "no_stop"
    assert str(repo / dck.LOCAL_SETTINGS) in " ".join(out["warnings"])
    assert Path(out["record"]).is_relative_to(repo / ".claude/decision-kit")


def test_a_parent_override_is_named_even_when_it_changes_nothing(server, repo, monkeypatch):
    _local(repo)
    nested = repo / "a"
    nested.mkdir()
    monkeypatch.chdir(nested)
    out = dck.run(decision(), server["base"])
    assert any("project folder" in w and str(repo) in w for w in out["warnings"])


def test_project_root_skips_an_unreadable_folder(repo, monkeypatch):
    def denied(self):
        raise PermissionError

    monkeypatch.setattr(Path, "is_file", denied)
    assert dck.project_root(repo) == repo


def test_project_root_defaults_to_the_start_folder(repo):
    nested = repo / "a"
    nested.mkdir()
    assert dck.project_root(nested) == nested


def test_a_token_count_is_not_refused():
    assert dck.screen(["The token limit: 4000 per request."], FAKE_KEY) is None


def test_local_override_is_honoured(server, repo):
    _local(repo, proceed_max_p_block=0.5)
    server["reply"][PIN] = (200, answer(PIN, safe=0.6))
    out = dck.run(decision(), server["base"], repo)
    assert out["verdict"] == "no_stop"
    assert any("overrides: proceed_max_p_block" in w for w in out["warnings"])


def test_invalid_local_override_is_ignored(server, repo):
    _local(repo, proceed_max_p_block=0.9, stop_min_p_block=0.1)
    server["reply"][PIN] = (200, answer(PIN, safe=0.6))
    assert dck.run(decision(), server["base"], repo)["reason"] == "uncertain"


def test_disabled(server, repo):
    _local(repo, enabled=False)
    assert dck.run(decision(trigger="confidence"), server["base"], repo)["verdict"] == "disabled"
    assert dck.run(decision(), server["base"], repo)["verdict"] == "ask_user"
    assert not server["requests"]


def test_redirect_is_not_followed(repo):
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_POST(self):
            seen.append(self.path)
            self.send_response(307)
            self.send_header("Location", "/stolen")
            self.send_header("Content-Length", "0")
            self.end_headers()

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    status, _ = dck.post(f"http://127.0.0.1:{httpd.server_port}", FAKE_KEY, {"model": "m"}, 5)
    httpd.shutdown()
    httpd.server_close()
    assert status == 307 and seen == [dck.DECISIONS_PATH]


def test_script_stays_compatible_with_python_3_9():
    source = (SKILL / "scripts" / "dck-decide.py").read_text(encoding="utf-8")
    ast.parse(source, feature_version=(3, 9))
    assert "import UTC" not in source and "datetime.UTC" not in source


def test_hook_is_silent_without_a_key():
    hook = SKILL.parents[1] / "hooks" / "dck-session-context.sh"
    env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
    assert (
        subprocess.run(
            ["bash", str(hook)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=True,
        ).stdout
        == ""
    )
    env["OPENROUTER_API_KEY"] = FAKE_KEY
    out = subprocess.run(
        ["bash", str(hook)], capture_output=True, text=True, encoding="utf-8", env=env, check=True
    ).stdout
    assert "consulting-decision-model" in out and FAKE_KEY not in out


def test_key_forms_are_refused(server, repo):
    import base64
    from urllib.parse import quote

    for form in (quote(FAKE_KEY, safe=""), base64.b64encode(FAKE_KEY.encode()).decode()):
        assert dck.run(decision(state=f"x {form}"), server["base"], repo)["verdict"] == "refused"


def test_extra_fields_stay_out_of_the_record(server, repo):
    server["reply"][PIN] = (200, answer(PIN))
    out = dck.run(decision(extra=FAKE_KEY, claude_choice=FAKE_KEY), server["base"], repo)
    assert FAKE_KEY not in Path(out["record"]).read_text(encoding="utf-8")


def test_request_marks_facts_as_data(server, repo):
    server["reply"][PIN] = (200, answer(PIN))
    dck.run(decision(), server["base"], repo)
    assert "not evidence" in server["requests"][0]["state"]["data_note"]


@pytest.mark.parametrize(
    "link",
    [
        ".claude/decision-kit",
        ".claude/decision-kit/consultations",
        ".claude/decision-kit/.gitignore",
    ],
)
def test_links_on_the_record_path_block_the_record(server, repo, tmp_path_factory, link):
    outside = tmp_path_factory.mktemp("outside")
    (repo / link).parent.mkdir(parents=True, exist_ok=True)
    (repo / link).symlink_to(outside / "target", target_is_directory=not link.endswith("ignore"))
    server["reply"][PIN] = (200, answer(PIN))
    out = dck.run(decision(), server["base"], repo)
    assert out["record"] is None and out["verdict"] == "no_stop"
    assert not list(outside.iterdir())


def test_changed_gitignore_blocks_the_record(server, repo):
    (repo / ".claude/decision-kit").mkdir(parents=True)
    (repo / ".claude/decision-kit/.gitignore").write_text("", encoding="utf-8")
    server["reply"][PIN] = (200, answer(PIN))
    assert dck.run(decision(), server["base"], repo)["record"] is None


@pytest.mark.parametrize(
    "body",
    [
        answer(PIN, safe=float("nan")),
        {"model": PIN, "answers": {"safe_to_proceed": {"noul": 10**400}, "risk": {"score": 0}}},
        answer(PIN, safe=True),
        answer(PIN, safe=1.5),
        answer(PIN, risk=9),
        answer(PIN, risk=[1]),
    ],
)
def test_bad_answers_fall_back(server, repo, body):
    raw = json.dumps(body).encode()
    server["reply"][PIN] = (200, raw)
    server["reply"][FALL] = (200, answer(FALL))
    assert dck.run(decision(), server["base"], repo)["source"] == "fallback"


def test_risk_half_step_rounds_up(server, repo):
    server["reply"][PIN] = (200, answer(PIN, risk=1.5))
    assert dck.run(decision(), server["base"], repo)["reason"] == "disagree_on_risk"


def test_truncated_response_is_no_answer(repo):
    import socket

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)

    def serve():
        conn, _ = listener.accept()
        conn.recv(65536)
        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\nshort")
        conn.close()

    threading.Thread(target=serve, daemon=True).start()
    status, body = dck.post(f"http://127.0.0.1:{listener.getsockname()[1]}", FAKE_KEY, {}, 5)
    listener.close()
    assert (status, body) == (200, b"short")
    assert dck.parse_answers(body, PIN, decision()) is None


def test_oversized_response_is_a_failure(repo, monkeypatch, server):
    monkeypatch.setattr(dck, "MAX_RESPONSE_BYTES", 5)
    server["reply"][PIN] = (200, answer(PIN))
    assert dck.post(server["base"], FAKE_KEY, {"model": PIN}, 5) == (None, b"")


def test_bad_listing_is_ignored(server):
    server["listing"] = {"data": ["x"]}
    assert dck.expiring_snapshots(server["base"], 5) == set()


def _cli(stdin: bytes, env=None):
    done = subprocess.run(
        ["python3", "-I", str(SKILL / "scripts" / "dck-decide.py")],
        input=stdin,
        capture_output=True,
        env=env,
        check=True,
        timeout=30,
    )
    assert done.stderr == b""
    return json.loads(done.stdout)


def test_cli_always_prints_a_verdict():
    assert _cli(b"not json")["verdict"] == "refused"
    assert _cli(b"[" * 200000)["verdict"] == "refused"
    assert _cli(b"\xff")["verdict"] == "refused"


def test_cli_crash_asks_the_user(tmp_path):
    script = tmp_path / "scripts" / "dck-decide.py"
    script.parent.mkdir()
    script.write_bytes((SKILL / "scripts" / "dck-decide.py").read_bytes())
    data = json.dumps(decision()).encode()
    done = subprocess.run(
        ["python3", "-I", str(script)], input=data, capture_output=True, check=True, timeout=30
    )
    out = json.loads(done.stdout)
    assert (out["verdict"], out["reason"]) == ("ask_user", "internal_error")


def test_ordinary_kebab_text_is_not_a_token(server, repo):
    server["reply"][PIN] = (200, answer(PIN))
    data = decision(state="see risk-assessment-of-the-migration-plan for details")
    assert dck.run(data, server["base"], repo)["verdict"] == "no_stop"
