"""
Unit tests for voice/response_formatter.py

No audio device or API key required — pure Python logic tests.
"""

import pytest
from archon.voice.response_formatter import (
    format_for_speech,
    _strip_bold_italic,
    _strip_headers,
    _strip_code_spans,
    _expand_code_fences,
    _list_to_prose,
    _cap_sentences,
    MAX_SENTENCES,
)


class TestStripBoldItalic:
    def test_double_star_bold(self):
        assert _strip_bold_italic("**hello world**") == "hello world"

    def test_single_star_italic(self):
        assert _strip_bold_italic("*hello*") == "hello"

    def test_triple_star(self):
        assert _strip_bold_italic("***bold italic***") == "bold italic"

    def test_underscore_italic(self):
        assert _strip_bold_italic("_hello_") == "hello"

    def test_plain_text_unchanged(self):
        assert _strip_bold_italic("plain text") == "plain text"

    def test_mixed_content(self):
        result = _strip_bold_italic("Run **pytest** tests with *coverage*.")
        assert result == "Run pytest tests with coverage."


class TestStripHeaders:
    def test_h1(self):
        assert _strip_headers("# Title") == "Title"

    def test_h3(self):
        assert _strip_headers("### Section") == "Section"

    def test_multiline(self):
        text = "# First\nSome text\n## Second"
        result = _strip_headers(text)
        assert "First\n" in result
        assert "Second" in result
        assert "#" not in result


class TestStripCodeSpans:
    def test_inline_code(self):
        assert _strip_code_spans("Use `asyncio.run()` here") == "Use asyncio.run() here"

    def test_multiple_spans(self):
        result = _strip_code_spans("`foo` and `bar`")
        assert result == "foo and bar"


class TestExpandCodeFences:
    def test_python_block(self):
        text = "```python\ndef hello():\n    pass\n```"
        result = _expand_code_fences(text)
        assert "Here's the python" in result
        assert "def hello():" in result
        # Fence markers should be gone
        assert "```" not in result

    def test_no_lang_block(self):
        text = "```\nsome code here\n```"
        result = _expand_code_fences(text)
        assert "Here's the" in result
        assert "some code here" in result


class TestListToProse:
    def test_bullet_list(self):
        text = "- item one\n- item two\n- item three"
        result = _list_to_prose(text)
        assert "item one" in result
        assert "item two" in result
        assert "item three" in result
        assert "and" in result

    def test_numbered_list(self):
        text = "1. first\n2. second"
        result = _list_to_prose(text)
        assert "first" in result
        assert "second" in result

    def test_single_item(self):
        text = "- only thing"
        result = _list_to_prose(text)
        assert "only thing" in result

    def test_plain_text_unchanged(self):
        text = "No bullets here."
        assert _list_to_prose(text) == text


class TestCapSentences:
    def test_under_limit(self):
        text = "One. Two."
        assert _cap_sentences(text, max_sentences=4) == text

    def test_over_limit(self):
        text = "One. Two. Three. Four. Five. Six."
        result = _cap_sentences(text, max_sentences=3)
        parts = result.split(". ")
        # Should have at most 3 + trailing dot
        assert len(result.split(". ")) <= 4

    def test_question_marks(self):
        text = "What is it? It is a test. Right? Yes. Indeed."
        result = _cap_sentences(text, max_sentences=2)
        assert "What is it?" in result


class TestFormatForSpeech:
    def test_strips_markdown_end_to_end(self):
        md = "## Database Design\n\nUse **SQLite** for local storage with `aiosqlite`."
        result = format_for_speech(md)
        assert "##" not in result
        assert "**" not in result
        assert "`" not in result
        assert "SQLite" in result

    def test_code_fence_verbalized(self):
        md = "Here is the code:\n\n```python\ndef foo():\n    return 42\n```"
        result = format_for_speech(md)
        assert "Here's the python" in result
        assert "```" not in result

    def test_full_detail_bypasses_cap(self):
        # Build a string with 10 sentences
        long_text = " ".join(f"Sentence {i}." for i in range(10))
        default_result = format_for_speech(long_text, full_detail=False)
        full_result = format_for_speech(long_text, full_detail=True)
        assert len(full_result) >= len(default_result)

    def test_empty_string(self):
        assert format_for_speech("") == ""

    def test_plain_text_passes_through(self):
        text = "Here is a plain spoken answer. It has no markdown. Great."
        result = format_for_speech(text)
        assert "Here is a plain spoken answer" in result
