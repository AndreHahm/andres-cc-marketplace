#!/usr/bin/env python3
"""Ask the pinned OpenRouter decision model for a second opinion and print a JSON verdict.

Reads one JSON object on stdin and writes one JSON object on stdout. Standard library only.
This is the only code in decision-kit that talks to the API. The thresholds are applied here so
that the verdict does not depend on how Claude reads the numbers.

Input fields:
  trigger           "critical", "security" or "confidence"
  action            one sentence: what Claude proposes to do
  state             the facts the decision rests on (excerpts, never whole files)
  claude_position   "proceed" or "stop"
  claude_risk       "none", "low", "medium", "high" or "critical"
  options           optional map of option key to a one-line criterion (at least two)
  claude_choice     the key Claude prefers, required with options

Verdicts:
  no_stop           the model adds no stop; this authorizes nothing
  no_second_opinion no answer was available for a below-high-risk confidence decision
  ask_user          disagreement, uncertainty, agreement on a stop, an unavailable API on a
                    critical, security or high-risk decision, the `enabled` setting off on such
                    a decision, or an internal error
  refused           nothing was sent; fix the input and run once more
  disabled          the plugin's `enabled` setting is off, for a below-high-risk confidence decision
"""

from __future__ import annotations

import base64
import functools
import http.client
import json
import math
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_BASE = "https://openrouter.ai"
DECISIONS_PATH = "/api/alpha/decisions"
MODELS_PATH = "/api/v1/models?output_modalities=decisions"
REQUEST_TIMEOUT = 20.0
LISTING_TIMEOUT = 5.0
MAX_RESPONSE_BYTES = 2_000_000

# The fallback has a 16,384-token context, and code runs at roughly 3 characters per token.
MAX_STATE_CHARS = 40_000

# Passes of URL and string decoding before the screen refuses. Ordinary text settles in one or two.
MAX_DECODE_PASSES = 8
MAX_BASE64_LAYERS = 2
BASE64_SPAN = re.compile(r"[A-Za-z0-9+/_-]{16,}")

# Worth trying the other model. 401, 402, 403 and 413 would fail the same way on both.
FALLBACK_STATUSES = {404, 429, 500, 502, 503, 524, 529}

LOCAL_SETTINGS = ".claude/decision-kit.local.json"
RECORDS_DIR = ".claude/decision-kit"
TRIGGERS = ("critical", "security", "confidence")
SKILL_DIR = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"[a-z0-9._-]+/[a-z0-9._:-]+")
INPUT_FIELDS = (
    "trigger",
    "action",
    "state",
    "claude_position",
    "claude_risk",
    "options",
    "claude_choice",
)

# Shapes the shared list does not carry, because it is prefix-based and also drives redaction.
EXTRA_SHAPES = (
    ("private_key", r"-----BEGIN [A-Z ]*PRIVATE KEY"),
    ("credential_url", r"(?i)(?<![a-z0-9+.-])[a-z][a-z0-9+.-]*://[^\s:/@]*:[^\s/@]+@"),
    (
        "secret_assignment",
        r"(?i)(?:password|passwd|api[_-]?key|access[_-]?key|secret(?:[_-]?(?:access[_-]?)?key)?"
        r"|(?<![A-Za-z0-9])token)[\"']?\s*(?:=>|[:=])\s*[\"']?[^\s\"']{8,}",
    ),
    (
        "authorization_header",
        r"(?i)authorization[\"']?\s*(?:=>|[:=])\s*[\"']?(?:bearer|basic|token)\s+\S{8,}",
    ),
    ("stripe_key", r"[sr]k_(?:live|test)_[A-Za-z0-9]{16,}"),
    ("gitlab_token", r"glpat-[A-Za-z0-9_-]{20,}"),
    ("npm_token", r"npm_[A-Za-z0-9]{36,}"),
    ("aws_temporary_key", r"(?<![A-Za-z0-9])ASIA[A-Z0-9]{16}"),
    ("google_oauth_token", r"ya29\.[A-Za-z0-9_-]{20,}"),
    ("huggingface_token", r"hf_[A-Za-z0-9]{30,}"),
    ("slack_app_token", r"xapp-[0-9A-Za-z-]{20,}"),
    ("slack_webhook", r"hooks\.slack\.com/services/\S+"),
    ("stripe_webhook_secret", r"whsec_[A-Za-z0-9]{20,}"),
    ("pypi_token", r"pypi-[A-Za-z0-9_-]{50,}"),
    ("digitalocean_token", r"dop_v1_[a-f0-9]{40,}"),
    ("sendgrid_key", r"SG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}"),
)


class _Unsettled(Exception):
    """The text still changes after every decoding pass, so the screen cannot judge it."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """urllib would replay the Authorization header to a redirect target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _link_on_path(root: Path, relative: str) -> bool:
    """True if any part of the path below the root is a symlink. A repository can commit one."""
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _valid_settings(settings: dict) -> bool:
    low, high = settings.get("proceed_max_p_block"), settings.get("stop_min_p_block")
    if isinstance(low, bool) or isinstance(high, bool):
        return False
    if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
        return False
    slugs = all(
        isinstance(settings.get(k), str) and SLUG.fullmatch(settings[k])
        for k in ("pinned_model", "fallback_model")
    )
    return bool(slugs) and isinstance(settings.get("enabled"), bool) and 0 <= low < high <= 1


def load_settings(root: Path, warnings: list[str]) -> dict:
    """Shipped defaults, then the optional local override. Changed fields go in the warnings.

    An unusable override turns the check off: it may be the file that was meant to do that, and
    the warning would only arrive after the text had left the machine.
    """
    settings = json.loads(
        (SKILL_DIR / "assets" / "decision-kit.settings.json").read_text(encoding="utf-8")
    )
    if not _valid_settings(settings):
        raise ValueError("invalid shipped settings")
    path = root / LOCAL_SETTINGS
    if not os.path.lexists(path):
        return settings
    off = {**settings, "enabled": False}
    try:
        local = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        warnings.append(f"{path} is not readable JSON: the check is off until it is fixed")
        return off
    merged = (
        {**settings, **local} if isinstance(local, dict) and set(local) <= set(settings) else {}
    )
    if not _valid_settings(merged):
        warnings.append(f"{path} has invalid values or keys: the check is off until it is fixed")
        return off
    changed = sorted(k for k in settings if merged[k] != settings[k])
    if changed:
        warnings.append(f"{path} overrides: " + ", ".join(changed))
    return merged


def validate_input(data: object) -> str | None:
    """Returns the reason the input is unusable, or None."""
    if not isinstance(data, dict):
        return "input must be a JSON object"
    trigger = data.get("trigger")
    if not isinstance(trigger, str) or trigger not in TRIGGERS:
        return "trigger must be critical, security or confidence"
    for field in ("action", "state"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            return f"{field} must be a non-empty string"
    if data.get("claude_position") not in ("proceed", "stop"):
        return "claude_position must be proceed or stop"
    rubric = _templates()["risk_rubric"]
    if not isinstance(data.get("claude_risk"), str) or data["claude_risk"] not in rubric:
        return "claude_risk must be one of " + ", ".join(rubric)
    options = data.get("options")
    if options is not None:
        if not isinstance(options, dict) or len(options) < 2:
            return "options must map at least two keys to criteria"
        if not all(
            isinstance(k, str) and isinstance(v, str) and k and v for k, v in options.items()
        ):
            return "options keys and criteria must be non-empty strings"
        choice = data.get("claude_choice")
        if not isinstance(choice, str) or choice not in options:
            return "claude_choice must be one of the option keys"
    return None


@functools.lru_cache(maxsize=1)
def _templates() -> dict:
    return json.loads(
        (SKILL_DIR / "assets" / "question-templates.json").read_text(encoding="utf-8")
    )


def _key_forms(key: str) -> list[str]:
    raw = key.encode("utf-8", "surrogateescape")
    return (
        [key, urllib.parse.quote(key, safe=""), base64.b64encode(raw).decode("ascii")]
        if key
        else []
    )


def _unescape(text: str) -> str:
    """Removes one layer of JSON and string escapes."""
    text = text.replace("\\\\", "\\").replace("\\/", "/")
    text = re.sub(
        r"\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})",
        lambda found: chr(int(found.group(1) or found.group(2), 16)),
        text,
    )
    return re.sub(r"\\[nrtbf\"']", " ", text)


def _decode_fully(text: str) -> str:
    """`text` with its URL and string escapes removed. Raises `_Unsettled` if it never settles."""
    for _ in range(MAX_DECODE_PASSES):
        decoded = _unescape(urllib.parse.unquote(text))
        if decoded == text:
            return text
        text = decoded
    raise _Unsettled


def _base64_payloads(text: str, layers: int = MAX_BASE64_LAYERS) -> list[str]:
    """What each span that could be base64 decodes to. Most spans decode to noise, which is fine.

    Ordinary neighbours such as `path/` or `name_` join a span, so every alignment is tried.
    """
    payloads: list[str] = []
    for span in BASE64_SPAN.findall(text):
        raw = span.replace("-", "+").replace("_", "/")
        for offset in range(4):
            chunk = raw[offset:]
            if len(chunk) % 4 == 1:
                chunk = chunk[:-1]
            payload = base64.b64decode(chunk + "=" * (-len(chunk) % 4)).decode("utf-8", "replace")
            payload = _decode_fully(payload)
            payloads.append(payload)
            if layers > 1:
                payloads += _base64_payloads(payload, layers - 1)
    return payloads


def screen(texts: list[str], key: str) -> str | None:
    """Returns why the text must not leave the machine, or None. An unreadable pattern file refuses.

    The shared shapes start at a word boundary, which a leading `_`, a URL escape or a JSON escape
    hides, so the boundary here counts `_` as a separator, and escapes are removed before matching.
    Text that does not settle is refused, and base64 spans are checked in their decoded form.
    """
    try:
        raw = (SKILL_DIR / "scripts" / "dck-token-shapes.json").read_text(encoding="utf-8")
        shapes = [(s["name"], s["pattern"]) for s in json.loads(raw)["shapes"]]
        shared = [(name, r"(?<![A-Za-z0-9])" + p.removeprefix(r"\b")) for name, p in shapes]
        patterns = [(name, re.compile(p, re.ASCII)) for name, p in (*shared, *EXTRA_SHAPES)]
    except (OSError, ValueError, KeyError, TypeError, re.error):
        return "the secret patterns could not be loaded"
    forms = _key_forms(key)
    for text in texts:
        try:
            decoded = _decode_fully(text)
            views = [text, decoded, *_base64_payloads(decoded)]
        except _Unsettled:
            return "the text has too many layers of encoding to check"
        if any(form in view for form in forms for view in views):
            return "the text contains the API key"
        for name, pattern in patterns:
            if any(pattern.search(view) for view in views):
                return f"the text matches the secret shape {name}"
    return None


def build_payload(data: dict, model: str) -> dict:
    """The request body. `zdr` is fixed: a model without a ZDR endpoint must fail, not answer."""
    templates = _templates()
    trigger = templates["triggers"][data["trigger"]]
    questions: dict = {
        "safe_to_proceed": {
            "type": "noul",
            "instructions": trigger["instructions"],
            "criteria": {"true": trigger["true"], "false": trigger["false"]},
        },
        "risk": {
            "type": "score",
            "instructions": "How risky is carrying out the proposed action as described?",
            "criteria": templates["risk_rubric"],
        },
    }
    if data.get("options"):
        questions["best_option"] = {
            "type": "choice",
            "instructions": "Which option should be taken?",
            "criteria": data["options"],
        }
    return {
        "model": model,
        "state": {
            "policy": trigger["policy"],
            "data_note": templates["data_note"],
            "proposed_action": data["action"],
            "facts": data["state"],
        },
        "questions": questions,
        "provider": {"zdr": True},
    }


def _read_capped(response, deadline: float) -> bytes | None:
    """The body, or None if it is too large or arrives too slowly. Socket timeouts are per read."""
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = response.read1(65536)
        if not chunk:
            return b"".join(chunks)
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES or time.monotonic() > deadline:
            return None
        chunks.append(chunk)


def post(base: str, key: str, payload: dict, timeout: float) -> tuple[int | None, bytes]:
    """Returns (status or None on a network failure, body). Never retries: the caller falls back."""
    request = urllib.request.Request(  # nosec B310
        base + DECISIONS_PATH,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    deadline = time.monotonic() + timeout
    try:
        try:
            with _OPENER.open(request, timeout=timeout) as response:
                status, body = response.status, _read_capped(response, deadline)
        except urllib.error.HTTPError as exc:
            status, body = exc.code, _read_capped(exc, deadline)
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError, ValueError):
        # No exception text anywhere: http.client quotes the whole header in its ValueError.
        return None, b""
    return (status, body) if body is not None else (None, b"")


def expiring_snapshots(base: str, timeout: float) -> set[str]:
    """Dated slugs with an expiration date. A failed lookup returns nothing."""
    deadline = time.monotonic() + timeout
    try:
        with _OPENER.open(base + MODELS_PATH, timeout=timeout) as response:  # nosec B310
            entries = json.loads(_read_capped(response, deadline) or b"")["data"]
        return {
            e["canonical_slug"]
            for e in entries
            if e.get("expiration_date") and e.get("canonical_slug")
        }
    except (
        urllib.error.URLError,
        http.client.HTTPException,
        TimeoutError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        RecursionError,
    ):
        return set()


def _number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse_answers(body: bytes, model: str, data: dict) -> dict | None:
    """The validated answers, or None. Only numbers and known keys get past this point."""
    try:
        parsed = json.loads(body)
        answers = parsed["answers"]
        safe = answers["safe_to_proceed"]["noul"]
        risk = answers["risk"]["score"]
        last_step = len(_templates()["risk_rubric"]) - 1
        if parsed.get("model") != model or not _number(safe) or not 0 <= safe <= 1:
            return None
        if not _number(risk) or not 0 <= risk <= last_step:
            return None
        # Rounded only to remove float noise: 1 - 0.95 is not exactly 0.05.
        result = {"p_block": round(1 - safe, 12), "risk_score": risk, "usage": {}}
        if isinstance(parsed.get("usage"), dict) and _number(parsed["usage"].get("cost")):
            result["usage"] = {"cost": parsed["usage"]["cost"]}
        if data.get("options"):
            choice = answers["best_option"]["choice"]
            if not isinstance(choice, str) or choice not in data["options"]:
                return None
            result["best_option"] = choice
        return result
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError, RecursionError):
        return None


def _try_fallback(status: int | None, body: bytes) -> bool:
    """A 200 reaches this only with an unusable answer, which the other model may not repeat."""
    if status is None or status == 200 or status in FALLBACK_STATUSES:
        return True
    return status == 400 and b"does not exist" in body


def consult(
    base: str, key: str, data: dict, settings: dict, warnings: list[str]
) -> tuple[dict | None, str, str]:
    """Returns (answers or None, model used, source), trying each model once."""
    pinned, fallback = settings["pinned_model"], settings["fallback_model"]
    expiring = expiring_snapshots(base, LISTING_TIMEOUT)
    if fallback in expiring:
        warnings.append(f"the fallback {fallback} has an expiration date; choose a new one")
    if pinned in expiring:
        warnings.append(
            f"{pinned} has an expiration date; using the fallback. Re-run the evaluation and re-pin"
        )
    else:
        status, body = post(base, key, build_payload(data, pinned), REQUEST_TIMEOUT)
        answers = parse_answers(body, pinned, data) if status == 200 else None
        if answers:
            return answers, pinned, "primary"
        if status == 400 and b"does not exist" in body:
            warnings.append(f"{pinned} was rejected as unknown; re-run the evaluation and re-pin")
        if not _try_fallback(status, body):
            warnings.append(f"the API refused the request with HTTP {status}")
            return None, pinned, "primary"
    status, body = post(base, key, build_payload(data, fallback), REQUEST_TIMEOUT)
    answers = parse_answers(body, fallback, data) if status == 200 else None
    if answers:
        return answers, fallback, "fallback"
    warnings.append(
        f"the fallback failed with HTTP {status}" if status else "the fallback could not be reached"
    )
    return None, fallback, "fallback"


def compare(data: dict, answers: dict, settings: dict) -> tuple[str, str]:
    """(verdict, reason). `no_stop` needs full agreement, and it still authorizes nothing."""
    p_block = answers["p_block"]
    clear_proceed = p_block <= settings["proceed_max_p_block"]
    clear_stop = p_block >= settings["stop_min_p_block"]
    if data["claude_position"] == "stop":
        if clear_stop:
            return "ask_user", "agree_stop"
        return "ask_user", "disagree" if clear_proceed else "uncertain"
    if clear_stop:
        return "ask_user", "disagree"
    if not clear_proceed:
        return "ask_user", "uncertain"
    if data.get("options") and answers.get("best_option") != data.get("claude_choice"):
        return "ask_user", "disagree_on_option"
    # The score is an expected value, so it is read as its nearest rubric step, half rounding up.
    assumed = _templates()["risk_rubric"].index(data["claude_risk"])
    if int(answers["risk_score"] + 0.5) > assumed:
        return "ask_user", "disagree_on_risk"
    return "no_stop", "agree"


def _high_stakes(data: dict) -> bool:
    return data["trigger"] != "confidence" or data["claude_risk"] in ("high", "critical")


def write_record(root: Path, record: dict, warnings: list[str]) -> str | None:
    """Local full record. The folder ignores itself, so this holds in any repository.

    A repository can commit a link or a `.gitignore` here to move records somewhere public or
    un-ignore them, so any of those means no record is written.
    """
    if _link_on_path(root, RECORDS_DIR + "/consultations") or _link_on_path(
        root, RECORDS_DIR + "/.gitignore"
    ):
        warnings.append("no consultation record written: a symlink is on the record path")
        return None
    folder = root / RECORDS_DIR
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        (folder / "consultations").mkdir(parents=True, exist_ok=True, mode=0o700)
        ignore = folder / ".gitignore"
        if ignore.exists():
            if ignore.read_text(encoding="utf-8") != "*\n":
                warnings.append(
                    "no consultation record written: the folder's .gitignore was changed"
                )
                return None
        else:
            with os.fdopen(os.open(ignore, flags, 0o600), "w", encoding="utf-8") as handle:
                handle.write("*\n")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # noqa: UP017 (Python 3.9)
        path = folder / "consultations" / f"{stamp}-{secrets.token_hex(4)}.json"
        with os.fdopen(os.open(path, flags, 0o600), "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2)
        return str(path)
    except (OSError, ValueError) as exc:
        warnings.append(f"the consultation record could not be written ({type(exc).__name__})")
        return None


def project_root(start: Path) -> Path:
    """The nearest folder at or above `start` that holds the local settings, else `start`."""
    for folder in (start, *start.parents):
        if os.path.lexists(folder / LOCAL_SETTINGS):
            return folder
    return start


def run(data: Any, base: str = API_BASE, root: Path | None = None) -> dict:
    warnings: list[str] = []
    if root is None:
        root = project_root(Path.cwd())
        if root != Path.cwd():
            warnings.append(f"Using the project folder {root}")
    problem = validate_input(data)
    if problem:
        return {"verdict": "refused", "reason": problem, "warnings": warnings}
    settings = load_settings(root, warnings)
    if not settings["enabled"]:
        verdict = "ask_user" if _high_stakes(data) else "disabled"
        return {"verdict": verdict, "reason": "disabled", "warnings": warnings}
    options = data.get("options") or {}
    texts = [data["action"], data["state"], *options.values(), *options]
    if sum(len(text) for text in texts) > MAX_STATE_CHARS:
        return {
            "verdict": "refused",
            "reason": f"the text exceeds {MAX_STATE_CHARS} characters",
            "warnings": warnings,
        }
    key = os.environ.get("OPENROUTER_API_KEY", "")
    problem = screen(texts, key)
    if problem:
        return {"verdict": "refused", "reason": problem, "warnings": warnings}

    answers, model, source = None, settings["pinned_model"], "none"
    if not key:
        warnings.append("OPENROUTER_API_KEY is not set")
    elif not re.fullmatch(r"[\x21-\x7e]+", key):
        warnings.append(
            "OPENROUTER_API_KEY contains whitespace or control characters; check how it is set"
        )
    else:
        answers, model, source = consult(base, key, data, settings, warnings)
    if answers:
        verdict, reason = compare(data, answers, settings)
    else:
        reason = "unavailable"
        verdict = "ask_user" if _high_stakes(data) else "no_second_opinion"
    result = {
        "verdict": verdict,
        "reason": reason,
        "model": model,
        "source": source,
        "warnings": warnings,
    }
    if answers:
        result["answers"] = {k: v for k, v in answers.items() if k != "usage"}
    record = {
        "time": datetime.now(timezone.utc).isoformat(),  # noqa: UP017 (Python 3.9)
        "input": {
            k: data[k] for k in INPUT_FIELDS if k in data and (k != "claude_choice" or options)
        },
        "thresholds": {k: settings[k] for k in ("proceed_max_p_block", "stop_min_p_block")},
        "usage": (answers or {}).get("usage", {}),
        "result": result,
    }
    result["record"] = write_record(root, record, warnings)
    return result


def main() -> int:
    """Always prints a verdict: a crash must not read as safe, and error text can hold the key."""
    try:
        try:
            data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        except (ValueError, RecursionError):
            data = None
        result = run(data)
    except Exception:  # noqa: BLE001
        result = {
            "verdict": "ask_user",
            "reason": "internal_error",
            "warnings": ["dck-decide.py failed unexpectedly"],
        }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
