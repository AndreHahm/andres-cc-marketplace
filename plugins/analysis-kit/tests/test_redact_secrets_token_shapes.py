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


def test_prose_without_an_assignment_is_untouched():
    text = "the password was rotated and the key is stored elsewhere"
    redacted, counts = redact_secrets.redact(text)
    assert redacted == text
    assert counts == {}
