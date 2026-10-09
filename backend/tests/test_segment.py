from pathlib import Path

from app.extract.segment import MAX_CLAUSE_CHARS, segment

FIXTURES = Path(__file__).parent / "fixtures"


def test_markdown_headings_and_numbering():
    text = """# Terms

## 1. Your account
You are responsible for your account and everything that happens with it, including the security of your password.

## 2. Arbitration
Any dispute will be resolved by binding arbitration. You waive the right to participate in a class action lawsuit.

3. Changes to these terms
We may change these terms at any time. Continued use of the service means you accept the new terms.
"""
    segs = segment(text)
    headings = [s.heading for s in segs]
    assert "1. Your account" in headings
    assert "2. Arbitration" in headings
    assert "3. Changes to these terms" in headings
    assert [s.idx for s in segs] == list(range(len(segs)))


def test_real_document_bounds():
    segs = segment((FIXTURES / "github_tos.md").read_text())
    assert 30 < len(segs) < 150
    # trozos razonables: ninguno gigantesco
    assert max(len(s.text) for s in segs) <= MAX_CLAUSE_CHARS * 1.1
    assert any(s.heading and "Definitions" in s.heading for s in segs)


def test_markdown_escapes_removed():
    segs = segment("## Section\n\n2\\. Your personal data rights and controls are described here in detail for you.")
    assert "2." in segs[0].text and "\\" not in segs[0].text
