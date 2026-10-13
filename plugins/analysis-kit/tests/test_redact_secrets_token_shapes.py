"""Tests for scripts/anls_redact_secrets.py's token shapes and mid-line assignments (issue #546).

The fine-grained GitHub token shape (`github_pat_...`) was redacted by the codex-kit and CI
copies of this pattern list but not by this one, and the dotenv-style rule only matched an
assignment at the start of a line.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import anls_redact_secrets as redact_secrets  # noqa: E402

# Built from pieces so no token-shaped literal sits in this source file.
FINE_GRAINED_TOKEN = "github_pat_" + "a" * 22 + "_" + "b" * 30


def test_redacts_fine_grained_github_token():
    redacted, counts = redact_secrets.redact(f"push failed with {FINE_GRAINED_TOKEN} rejected")
    assert FINE_GRAINED_TOKEN not in redacted
    assert "push failed with [REDACTED] rejected" == redacted
    assert counts.get("github_pat_token") == 1


def test_redacts_mid_line_secret_assignment_value_only():
    value = "hunter2" + "abcdef"
    text = f"could not read env DATABASE_PASSWORD={value} then more"
    redacted, _ = redact_secrets.redact(text)
    assert value not in redacted
    # Value-only replacement keeps the name and the surrounding prose.
    assert redacted.startswith("could not read env DATABASE_PASSWORD=")
    assert redacted.endswith(" then more")


def test_name_that_only_contains_a_credential_word_is_not_redacted():
    for text in ("error while sorting: sortKey=asc then more", "saw monkey=banana today"):
        redacted, counts = redact_secrets.redact(text)
        assert redacted == text
        assert counts == {}


def test_redacts_camel_case_compound_credential_name():
    value = "hunter2" + "abcdef"
    redacted, _ = redact_secrets.redact(f"failed with apiKey={value} again")
    assert value not in redacted
    assert redacted.startswith("failed with apiKey=")


def test_redacts_camel_case_names_ending_in_a_credential_word():
    value = "hunter2" + "abcdef"
    for name in ("databasePassword", "awsAccessKey", "clientSecret", "authToken"):
        redacted, _ = redact_secrets.redact(f"request failed: {name}={value} retrying")
        assert value not in redacted, name
        assert redacted.endswith(" retrying"), name


def test_unterminated_quote_redacts_only_the_rest_of_its_line():
    redacted, _ = redact_secrets.redact('stderr: API_KEY="abc\nlots of other diagnostic text\nmore')
    assert "abc" not in redacted
    assert "lots of other diagnostic text" in redacted
    assert redacted.endswith("\nmore")


def test_quoted_value_ending_in_a_lone_backslash_is_redacted_whole():
    bs = chr(92)
    for quote in ('"', "'"):
        at_end, _ = redact_secrets.redact(f"diag: API_KEY={quote}two words{bs}")
        assert "words" not in at_end, quote
        before_newline, _ = redact_secrets.redact(
            f"diag: DB_PASSWORD={quote}top secret{bs}\nnext line stays"
        )
        assert "secret" not in before_newline, quote
        assert before_newline.endswith("\nnext line stays"), quote


def test_escaped_quote_inside_a_quoted_value_still_redacts_through_the_closing_quote():
    bs = chr(92)
    redacted, _ = redact_secrets.redact(f'diag: DB_PASSWORD="top {bs}"secret" tail')
    assert "secret" not in redacted
    assert redacted.endswith(" tail")


def test_prose_without_an_assignment_is_untouched():
    text = "the password was rotated and the key is stored elsewhere"
    redacted, counts = redact_secrets.redact(text)
    assert redacted == text
    assert counts == {}
