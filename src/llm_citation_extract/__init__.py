"""llm-citation-extract-py — extract citations and references from LLM output."""

from __future__ import annotations

import re
from dataclasses import dataclass

__version__ = "0.1.0"

# Punctuation that commonly trails a URL when it ends a sentence or clause in
# prose, e.g. "see https://example.com." — these are not part of the URL.
_TRAILING_PUNCT = ".,;:!?"


def _trim_url(url: str) -> str:
    """Strip sentence-trailing punctuation from a bare URL.

    LLM output frequently ends a sentence with a URL ("see https://x.com."),
    leaving a stray ``.``/``!``/``?``/``,``/``;``/``:`` glued to the link. A
    single unbalanced closing parenthesis (from "(see https://x.com)") is also
    removed. URLs captured from markdown links are already delimited and are
    not passed through this helper.
    """
    while url and url[-1] in _TRAILING_PUNCT:
        url = url[:-1]
    # Drop a trailing ")" only when it has no matching "(" inside the URL,
    # i.e. it belongs to the surrounding prose rather than the URL itself.
    if url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1]
    return url


@dataclass
class Citation:
    """A single extracted citation."""

    index: int | None  # numeric reference like [1], [2]
    text: str  # the full citation text
    url: str | None = None  # extracted URL if present
    label: str | None = None  # alphanumeric label like [REF1]
    kind: str = "unknown"  # "numbered", "url", "footnote", "bracket"


@dataclass
class CitationResult:
    """Result of extracting citations from text."""

    citations: list[Citation]
    cleaned_text: str  # text with inline citation markers removed
    has_references: bool

    @property
    def count(self) -> int:
        return len(self.citations)

    def by_index(self, n: int) -> Citation | None:
        return next((c for c in self.citations if c.index == n), None)

    def urls(self) -> list[str]:
        return [c.url for c in self.citations if c.url]


def extract_citations(text: str) -> CitationResult:
    """
    Extract citations from LLM output in multiple formats.

    Handles:
    - Numbered inline refs: [1], [2], [1,2]
    - URLs in text: https://...
    - Markdown links: [label](url)
    - Footnote-style at end: [1] Source title. https://...

    Args:
        text: Raw LLM output.

    Returns:
        CitationResult with extracted citations and cleaned text.
    """
    citations: list[Citation] = []
    cleaned = text

    # 1. Markdown links [label](url)
    md_pattern = re.compile(r"\[([^\]]+)\]\((https?://[^\)]+)\)")
    for m in md_pattern.finditer(text):
        citations.append(
            Citation(
                index=None,
                text=m.group(0),
                url=m.group(2),
                label=m.group(1),
                kind="markdown_link",
            )
        )
    cleaned = md_pattern.sub(r"\1", cleaned)

    # 2. Bare URLs
    url_pattern = re.compile(r'(?<!\()(https?://[^\s\)\]\>,"\']+)', re.IGNORECASE)
    for m in url_pattern.finditer(cleaned):
        url = _trim_url(m.group(1))
        if not url:
            continue
        # Skip if already captured as part of a markdown link
        if not any(c.url == url for c in citations):
            citations.append(
                Citation(
                    index=None,
                    text=url,
                    url=url,
                    kind="url",
                )
            )

    # 3. Numbered inline refs [1], [2,3], [1-3]
    inline_pattern = re.compile(r"\[(\d[\d,\s\-]*)\](?!\()")
    # Remove inline numbered markers from the cleaned prose. Also consume a single
    # space immediately preceding the marker so "supported [1] and" collapses to
    # "supported and" rather than leaving a stray double space.
    cleaned = re.sub(r" ?\[\d[\d,\s\-]*\](?!\()", "", cleaned)
    for m in inline_pattern.finditer(text):
        # parse individual numbers
        nums_text = m.group(1)
        nums = [int(n) for n in re.findall(r"\d+", nums_text)]
        for n in nums:
            if not any(c.index == n and c.kind == "numbered" for c in citations):
                citations.append(
                    Citation(
                        index=n,
                        text=m.group(0),
                        kind="numbered",
                    )
                )

    # 4. Footnote-style at end of text: "^[1]" or lines starting with [1] Source...
    footnote_pattern = re.compile(
        r"^\s*\[(\d+)\]\s+(.+?)(?:\s+(https?://\S+))?$",
        re.MULTILINE,
    )
    for m in footnote_pattern.finditer(text):
        n = int(m.group(1))
        citation_text = m.group(2).strip()
        url = _trim_url(m.group(3)) if m.group(3) else None
        # Update existing numbered citation if found
        existing = next(
            (c for c in citations if c.index == n and c.kind == "numbered"), None
        )
        if existing:
            existing.text = citation_text
            if url:
                existing.url = url
        else:
            citations.append(
                Citation(
                    index=n,
                    text=citation_text,
                    url=url,
                    kind="footnote",
                )
            )

    # Sort: numbered first by index, then the rest
    numbered = sorted(
        [c for c in citations if c.index is not None], key=lambda c: c.index
    )
    others = [c for c in citations if c.index is None]

    return CitationResult(
        citations=numbered + others,
        cleaned_text=cleaned.strip(),
        has_references=len(citations) > 0,
    )


def extract_urls(text: str) -> list[str]:
    """Extract all URLs from ``text``.

    Bare URLs are returned with sentence-trailing punctuation removed (so
    ``"see https://x.com."`` yields ``"https://x.com"``). The result is
    deduplicated while preserving first-seen order.

    Args:
        text: Any text, typically raw LLM output.

    Returns:
        Ordered list of unique URLs.
    """
    pattern = re.compile(r'https?://[^\s\)\]\>,"\']+', re.IGNORECASE)
    urls = (_trim_url(u) for u in pattern.findall(text))
    return list(dict.fromkeys(u for u in urls if u))  # deduped, order-preserving


def extract_numbered_refs(text: str) -> list[int]:
    """Extract all unique numeric citation indices like [1], [2] from text."""
    pattern = re.compile(r"\[(\d+)\](?!\()")
    nums = set()
    for m in pattern.finditer(text):
        nums.add(int(m.group(1)))
    return sorted(nums)


def strip_citations(text: str) -> str:
    """Remove citation markers from text, returning cleaned prose."""
    result = extract_citations(text)
    return result.cleaned_text


__all__ = [
    "Citation",
    "CitationResult",
    "extract_citations",
    "extract_urls",
    "extract_numbered_refs",
    "strip_citations",
    "__version__",
]
