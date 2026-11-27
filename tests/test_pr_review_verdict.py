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
