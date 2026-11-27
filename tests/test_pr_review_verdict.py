import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).parent.parent / "plugins" / "pr-review" / "scripts" / "verdict.py"
    spec = importlib.util.spec_from_file_location("pr_review_verdict", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.review_event


review_event = _load()


def test_no_findings_approves():
    assert review_event(["Taste: acceptable. No issues."]) == "APPROVE"


def test_only_non_critical_findings_approve():
    assert review_event(["Summary", "🟠 Important: x.", "🟡 Suggestion: y.", None]) == "APPROVE"


def test_a_critical_inline_comment_comments_without_approving():
    assert review_event(["Summary", "🟠 Important: x.", "🔴 Critical: data loss."]) == "COMMENT"


def test_a_critical_in_the_review_body_comments_without_approving():
    assert review_event(["🔴 Critical: the drop matches PR 12."]) == "COMMENT"


def test_a_critical_listed_in_the_review_body_comments_without_approving():
    assert review_event(["Findings:\n- **🔴 Critical:** the drop matches PR 12."]) == "COMMENT"


def test_a_critical_mentioned_mid_sentence_still_approves():
    assert review_event(["Good. The earlier 🔴 Critical no longer applies on this head."]) == "APPROVE"


def _load_relabel():
    path = Path(__file__).parent.parent / "plugins" / "pr-review" / "scripts" / "verdict.py"
    spec = importlib.util.spec_from_file_location("pr_review_verdict_relabel", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.relabel_unproven


relabel_unproven = _load_relabel()

PROOF = "\n\n```\n$ python -c 'import m; print(m.f(1))'\nNone\n```\n"


def test_a_critical_with_a_command_and_its_output_stays_critical():
    body = "🔴 Critical: f(1) returns None." + PROOF
    assert relabel_unproven(body) == body
    assert review_event([relabel_unproven(body)]) == "COMMENT"


def test_a_critical_without_proof_is_relabelled_important_and_approves():
    body = "🔴 Critical: `ci_owner` is not imported.\n\n```python\nowner = ci_owner(name)\n```"
    relabelled = relabel_unproven(body)
    assert relabelled.startswith("🟠 Important: `ci_owner` is not imported.")
    assert "🔴" not in relabelled
    assert review_event([relabelled]) == "APPROVE"


def test_a_command_with_no_output_is_not_proof():
    body = "🔴 Critical: it crashes.\n\n```\n$ python -m m\n```"
    assert relabel_unproven(body).startswith("🟠 Important")


def test_a_bold_listed_critical_without_proof_is_relabelled():
    body = "Findings:\n- **🔴 Critical:** the drop matches PR 12."
    assert relabel_unproven(body) == "Findings:\n- **🟠 Important:** the drop matches PR 12."


def test_a_critical_mentioned_mid_sentence_is_left_alone():
    body = "Good. The earlier 🔴 Critical no longer applies on this head."
    assert relabel_unproven(body) == body


def test_an_empty_body_is_left_alone():
    assert relabel_unproven(None) is None


def test_a_suggestion_block_is_not_proof():
    body = "🔴 Critical: wrong.\n\n```suggestion\n$ run it\nfixed line\n```"
    assert relabel_unproven(body).startswith("🟠 Important")


def test_proof_indented_under_a_list_item_counts():
    body = "- 🔴 Critical: f(1) returns None.\n\n  ```\n  $ python -c 'print(f(1))'\n  None\n  ```"
    assert relabel_unproven(body) == body


def test_a_tilde_fenced_proof_counts():
    body = "🔴 Critical: it crashes.\n\n~~~console\n$ python -m m\nTraceback (most recent call last):\n~~~"
    assert relabel_unproven(body) == body


def test_a_dollar_line_outside_a_fence_is_not_proof():
    body = "🔴 Critical: it crashes.\n$ python -m m\nTraceback"
    assert relabel_unproven(body).startswith("🟠 Important")


def test_a_red_marker_wrapped_to_the_start_of_a_line_is_not_a_finding():
    body = "🟠 Important: a later unproven Critical stays\n🔴. `review_event` then returns COMMENT."
    assert relabel_unproven(body) == body
    assert review_event([body]) == "APPROVE"


def test_each_critical_in_a_review_body_needs_its_own_proof():
    body = "- 🔴 Critical: a." + PROOF + "- 🔴 Critical: b, unproven."
    relabelled = relabel_unproven(body)
    assert relabelled.startswith("- 🔴 Critical: a.")
    assert relabelled.endswith("- 🟠 Important: b, unproven.")
    assert review_event([relabelled]) == "COMMENT"


def test_a_heading_critical_withholds_approval():
    assert review_event(["### 🔴 Critical: data loss." + PROOF]) == "COMMENT"


def test_a_critical_quoted_inside_a_code_block_is_not_a_finding():
    body = "🟠 Important: one proof covers both.\n\n```\n- 🔴 Critical: g() raises KeyError.\n```"
    assert relabel_unproven(body) == body
    assert review_event([body]) == "APPROVE"
