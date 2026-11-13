"""
Unit tests for text cleaning and normalization.
"""

from rag.cleaner import clean_legal_text, clean_unicode_artifacts, is_footnote_line, remove_running_headers_and_footers


def test_clean_unicode_artifacts():
    dirty_text = "Section 21\x00 \u201cProtection\u201d of \u2018life\u2019\u2014liberty\u2013law \xa0\u200b."
    cleaned = clean_unicode_artifacts(dirty_text)
    assert "\x00" not in cleaned
    assert "\xa0" not in cleaned
    assert "\u200b" not in cleaned
    assert '"Protection"' in cleaned
    assert "'life'" in cleaned
    assert "—" in cleaned


def test_remove_running_headers():
    gazette_header = "THE GAZETTE OF INDIA EXTRAORDINARY [PART II—SEC. 1]\nActual legal text."
    cleaned = remove_running_headers_and_footers(gazette_header)
    assert "THE GAZETTE OF INDIA" not in cleaned
    assert "PART II" not in cleaned
    assert "Actual legal text." in cleaned


def test_clean_legal_text_empty_and_spaces():
    assert clean_legal_text("") == ""
    assert clean_legal_text("   ") == ""
    text_with_spaces = "Section   103.    Murder.\n\n\n\nPunishment."
    cleaned = clean_legal_text(text_with_spaces)
    assert "Section 103. Murder." in cleaned
    assert "\n\n\n" not in cleaned


def test_is_footnote_line():
    assert is_footnote_line("1. Subs. by the Constitution (Seventh Amendment) Act, 1956, s. 2.")
    assert is_footnote_line("2. Ins. by Act 5 of 2005, s. 10.")
    assert is_footnote_line("3. The words 'in the State' omitted by s. 4, ibid.")
    assert not is_footnote_line("1. Name and territory of the Union.")
    assert not is_footnote_line("103. (1) Whoever commits murder shall be punished with death.")
