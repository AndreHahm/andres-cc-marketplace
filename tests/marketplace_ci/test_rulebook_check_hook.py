"""The PostToolUse rulebook hook's link check must not flag non-links (issues #594, #390)."""

import importlib.util
from pathlib import Path

HOOK = Path(__file__).resolve().parents[2] / "plugins/plugin-devkit/hooks/pdk-rulebook-check.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("pdk_rulebook_check", HOOK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _link_findings(tmp_path, body):
    skill = tmp_path / "SKILL.md"
    (tmp_path / "references").mkdir()
    (tmp_path / "references" / "real.md").write_text("x", encoding="utf-8")
    skill.write_text(body, encoding="utf-8")
    findings = []
    _load_hook().check_skill_links_and_orphans(body, skill, findings)
    return [message for severity, tag, message in findings if tag == "LINKS"]


def test_same_document_anchor_is_not_a_broken_link(tmp_path):
    assert (
        _link_findings(tmp_path, "See [Flow](#implementation-workflow) and references/real.md")
        == []
    )


def test_inline_code_example_is_not_a_link(tmp_path):
    body = "Format: `![Description](attachment-name.png)` references/real.md"
    assert _link_findings(tmp_path, body) == []


def test_fenced_example_is_not_a_link(tmp_path):
    body = "references/real.md\n```\n[x](missing-in-fence.md)\n```\n"
    assert _link_findings(tmp_path, body) == []


def test_tilde_fenced_example_is_not_a_link(tmp_path):
    body = "references/real.md\n~~~\n[x](missing-in-fence.md)\n~~~\n"
    assert _link_findings(tmp_path, body) == []


def test_a_fence_of_one_kind_inside_the_other_does_not_end_it(tmp_path):
    body = "references/real.md\n```\n~~~\n[x](missing-in-fence.md)\n```\n"
    assert _link_findings(tmp_path, body) == []


def test_a_four_backtick_fence_can_hold_a_three_backtick_example(tmp_path):
    body = "references/real.md\n````\n```\n[x](missing.md)\n```\n````\n"
    assert _link_findings(tmp_path, body) == []


def test_a_double_backtick_span_can_hold_a_single_backtick_and_a_link(tmp_path):
    body = "references/real.md ``use ` and [x](missing.md) here`` end"
    assert _link_findings(tmp_path, body) == []


def test_an_indented_fence_inside_a_list_item_is_code(tmp_path):
    body = "references/real.md\n- item\n    ```\n    [x](missing.md)\n    ```\n"
    assert _link_findings(tmp_path, body) == []


def test_a_fence_closes_only_on_an_equal_or_longer_run(tmp_path):
    # The three-backtick line does not end the four-backtick fence: the link inside stays code.
    body = "references/real.md\n````\n```\n[x](missing.md)\n````\n[after](missing-after.md)\n"
    assert _link_findings(tmp_path, body) == ["broken link: missing-after.md"]


def test_an_unclosed_fence_hides_nothing(tmp_path):
    body = "references/real.md\n```\n[x](missing.md)\n"
    assert _link_findings(tmp_path, body) == ["broken link: missing.md"]


def test_a_stray_backtick_does_not_swallow_a_later_link(tmp_path):
    body = "references/real.md a lone ` tick\n[x](missing.md)\n"
    assert _link_findings(tmp_path, body) == ["broken link: missing.md"]


def test_a_url_in_a_four_backtick_fence_or_double_backtick_span_is_not_a_bare_url():
    hook = _load_hook()
    for text in (
        "````\n```\nsee https://example.com/x\n```\n````\n",
        "use ``a ` https://example.com/x b`` here\n",
    ):
        findings = []
        hook.check_bare_urls(text, findings)
        assert findings == [], text


def test_a_url_inside_a_tilde_fence_is_not_a_bare_url():
    hook = _load_hook()
    for fence in ("```", "~~~"):
        findings = []
        hook.check_bare_urls(f"{fence}\nsee https://example.com/x\n{fence}\n", findings)
        assert findings == [], fence
    findings = []
    hook.check_bare_urls("see https://example.com/x here\n", findings)
    assert [rule for _, rule, _ in findings] == ["R17"]


def test_anchor_on_a_real_file_resolves(tmp_path):
    assert _link_findings(tmp_path, "[r](references/real.md#top)") == []


def test_real_broken_link_is_still_flagged(tmp_path):
    findings = _link_findings(tmp_path, "[gone](references/missing.md) and `[ok](x.md)`")
    assert findings == ["broken link: references/missing.md"]
