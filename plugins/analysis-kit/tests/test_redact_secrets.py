"""Tests for scripts/redact_secrets.py's home_directory_path pattern.

Other patterns in this module are already exercised indirectly via
test_persist_report.py (sk-ant-api03 key) and test_recommendation_registry.py
(AWS access key) -- this file covers the home-directory-path pattern added to
close plugin-auditor finding security-reviewer:M2 (report-evidence-convention.md
claims a mechanical OS-username redaction backstop that didn't actually exist).
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import redact_secrets  # noqa: E402


def test_redacts_windows_home_path_but_preserves_trailing_segment():
    text = r"Evidence source: C:\Users\andre\Dev\Repos\andres-cc-marketplace\evals\report.md"
    redacted, counts = redact_secrets.redact(text)
    assert r"C:\Users\andre" not in redacted
    assert "[REDACTED]" in redacted
    assert counts.get("home_directory_path") == 1
    # The repo-relative tail survives as citable evidence.
    assert r"Dev\Repos\andres-cc-marketplace\evals\report.md" in redacted


def test_redacts_windows_home_path_with_forward_slashes():
    text = "Evidence source: C:/Users/andre/Dev/Repos/andres-cc-marketplace/evals/report.md"
    redacted, counts = redact_secrets.redact(text)
    assert "C:/Users/andre" not in redacted
    assert "[REDACTED]" in redacted
    assert counts.get("home_directory_path") == 1
    assert "Dev/Repos/andres-cc-marketplace/evals/report.md" in redacted


def test_redacts_posix_home_path():
    text = "Evidence source: /home/andre/repos/andres-cc-marketplace/evals/report.md"
    redacted, counts = redact_secrets.redact(text)
    assert "/home/andre" not in redacted
    assert "[REDACTED]" in redacted
    assert counts.get("home_directory_path") == 1
    assert "repos/andres-cc-marketplace/evals/report.md" in redacted


def test_redacts_macos_users_home_path():
    text = "Evidence source: /Users/andre/repos/andres-cc-marketplace/evals/report.md"
    redacted, counts = redact_secrets.redact(text)
    assert "/Users/andre" not in redacted
    assert "[REDACTED]" in redacted
    assert counts.get("home_directory_path") == 1


def test_repo_relative_path_with_no_home_segment_is_untouched():
    text = "Evidence source: plugins/analysis-kit/skills/comparing-sessions/SKILL.md"
    redacted, counts = redact_secrets.redact(text)
    assert redacted == text
    assert "home_directory_path" not in counts
