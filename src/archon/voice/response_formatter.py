"""
Voice Response Formatter.

Converts AI-generated markdown text into clean, spoken-friendly prose
suitable for text-to-speech output.

Rules applied:
  1. Strip markdown syntax (bold, italic, headers, code spans, lists)
  2. Expand code fences into a verbal description
  3. Cap response length at MAX_SENTENCES (unless user asks for full detail)
  4. Normalise whitespace
"""

import re

# Maximum number of sentences to speak by default.
# The caller can pass full_detail=True to bypass this limit.
MAX_SENTENCES = 4


def _strip_bold_italic(text: str) -> str:
    """Remove **bold** and *italic* markers."""
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.*?)_{1,3}", r"\1", text)
    return text


def _strip_headers(text: str) -> str:
    """Turn '## Header text' → 'Header text'."""
    return re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)


def _strip_code_spans(text: str) -> str:
    """Replace `inline code` with just the code text."""
    return re.sub(r"`([^`\n]+)`", r"\1", text)


def _expand_code_fences(text: str) -> str:
    """
    Replace fenced code blocks with a spoken description.

    ```python
    def foo(): ...
    ```
    becomes:
    "Here's the code: def foo(): ..."
    """

    def _replace(m: re.Match) -> str:
        lang = (m.group(1) or "code").strip() or "code"
        body = m.group(2).strip()
        # Take only first two non-empty lines to keep TTS brief
        lines = [l for l in body.splitlines() if l.strip()][:2]
        snippet = " ".join(lines)
        return f"Here's the {lang} — {snippet}"

    return re.sub(r"```(\w+)?\n(.*?)```", _replace, text, flags=re.DOTALL)


def _strip_markdown_links(text: str) -> str:
    """Turn [label](url) → 'label'."""
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)


def _list_to_prose(text: str) -> str:
    """
    Convert leading bullet / numbered list lines to comma-separated prose.

    - item one       →  "item one, item two, and item three"
    * item two
    1. item three
    """
    bullet_re = re.compile(r"^(?:[-*•]|\d+\.) +(.+)$", re.MULTILINE)
    items = bullet_re.findall(text)
    if not items:
        return text
    # Build comma-separated sentence
    if len(items) == 1:
        prose = items[0]
    elif len(items) == 2:
        prose = f"{items[0]} and {items[1]}"
    else:
        prose = ", ".join(items[:-1]) + f", and {items[-1]}"
    # Remove the original list block and insert the prose
    cleaned = bullet_re.sub("", text).strip()
    return f"{cleaned} {prose}".strip() if cleaned else prose


def _normalise_whitespace(text: str) -> str:
    """Collapse excess blank lines and trailing spaces."""
    text = re.sub(r" +", " ", text)  # multiple spaces → one
    text = re.sub(r"\n{3,}", "\n\n", text)  # 3+ newlines → 2
    return text.strip()


def _cap_sentences(text: str, max_sentences: int) -> str:
    """
    Heuristically cap to the first *max_sentences* sentences.
    Sentence boundary = '. ' | '? ' | '! ' | end of string.
    """
    # Split on sentence-ending punctuation followed by whitespace or EOS
    parts = re.split(r"(?<=[.?!])\s+", text)
    if len(parts) <= max_sentences:
        return text
    capped = " ".join(parts[:max_sentences])
    return capped + "."


def format_for_speech(text: str, full_detail: bool = False) -> str:
    """
    Transform AI markdown output into spoken-friendly prose.

    Args:
        text:        Raw markdown string from the model.
        full_detail: If True, skip sentence-count cap.

    Returns:
        Clean, readable string suitable for TTS.
    """
    text = _expand_code_fences(text)
    text = _strip_headers(text)
    text = _strip_bold_italic(text)
    text = _strip_code_spans(text)
    text = _strip_markdown_links(text)
    text = _list_to_prose(text)
    text = _normalise_whitespace(text)

    if not full_detail:
        text = _cap_sentences(text, MAX_SENTENCES)

    return text
