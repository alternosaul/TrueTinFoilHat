from app.diff import align, for_llm
from app.extract.segment import Segment


def segs(*texts: str) -> list[Segment]:
    return [Segment(idx=i, heading=None, text=t) for i, t in enumerate(texts)]


def test_detects_added_removed_modified():
    old = segs(
        "We collect your email address to create your account.",
        "We never sell your personal data to third parties.",
        "You can delete your account at any time from the settings page.",
    )
    new = segs(
        "We collect your email address to create your account.",
        "We may sell your personal data to selected third parties and partners.",
        "Any dispute will be resolved by binding arbitration.",
    )
    changes = align(old, new)
    types = sorted(c["type"] for c in changes)
    assert types == ["added", "modified", "removed"]
    mod = next(c for c in changes if c["type"] == "modified")
    assert "never sell" in mod["old_text"] and "may sell" in mod["new_text"]
    assert [c["id"] for c in changes] == list(range(len(changes)))


def test_identical_documents_have_no_changes():
    a = segs("One clause about cookies.", "Another clause about data.")
    assert align(a, a) == []


def test_whitespace_only_changes_ignored():
    assert align(segs("Hello,   world. We use cookies."), segs("Hello, world. We use cookies!")) == []


def test_for_llm_truncates():
    changes = align(segs("x"), segs("y" * 5000))
    added = next(c for c in for_llm(changes) if c["type"] == "added")
    assert added["new_text"].endswith("[…]") and len(added["new_text"]) < 1600
