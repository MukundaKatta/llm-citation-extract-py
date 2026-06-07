"""llm-citation-extract-py — extract citations and references from LLM output."""

from __future__ import annotations

import re
from dataclasses import dataclass


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
        # Skip if already captured as part of a markdown link
        if not any(c.url == m.group(1) for c in citations):
            citations.append(
                Citation(
                    index=None,
                    text=m.group(1),
                    url=m.group(1),
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
        url = m.group(3)
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
    """Extract all URLs from text."""
    pattern = re.compile(r'https?://[^\s\)\]\>,"\']+', re.IGNORECASE)
    return list(dict.fromkeys(pattern.findall(text)))  # deduplicated, order-preserving


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
]
