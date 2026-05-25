"""Tests for llm-citation-extract-py."""
import pytest
from llm_citation_extract import (
    extract_citations, extract_urls, extract_numbered_refs,
    strip_citations, Citation, CitationResult,
)


def test_extract_numbered_refs_basic():
    text = "See [1] and [2] for details."
    refs = extract_numbered_refs(text)
    assert refs == [1, 2]


def test_extract_numbered_refs_no_refs():
    assert extract_numbered_refs("no refs here") == []


def test_extract_numbered_refs_unique():
    text = "[1] and [1] again."
    refs = extract_numbered_refs(text)
    assert refs == [1]


def test_extract_urls_basic():
    text = "See https://example.com for more info."
    urls = extract_urls(text)
    assert "https://example.com" in urls


def test_extract_urls_multiple():
    text = "Visit https://a.com and https://b.com"
    urls = extract_urls(text)
    assert len(urls) == 2


def test_extract_urls_none():
    assert extract_urls("no URLs here") == []


def test_extract_urls_deduped():
    text = "https://example.com is at https://example.com"
    urls = extract_urls(text)
    assert urls.count("https://example.com") == 1


def test_extract_citations_result_type():
    result = extract_citations("Hello world.")
    assert isinstance(result, CitationResult)
    assert isinstance(result.citations, list)


def test_extract_citations_no_refs():
    result = extract_citations("Plain text with no citations.")
    assert result.has_references is False
    assert result.count == 0


def test_extract_citations_numbered_inline():
    text = "This is supported [1] and also [2]."
    result = extract_citations(text)
    assert result.has_references is True
    numbered = [c for c in result.citations if c.kind == "numbered"]
    assert any(c.index == 1 for c in numbered)
    assert any(c.index == 2 for c in numbered)


def test_extract_citations_markdown_link():
    text = "Check [OpenAI](https://openai.com) for details."
    result = extract_citations(text)
    md_links = [c for c in result.citations if c.kind == "markdown_link"]
    assert len(md_links) >= 1
    assert md_links[0].url == "https://openai.com"
    assert md_links[0].label == "OpenAI"


def test_extract_citations_bare_url():
    text = "Visit https://example.com for more."
    result = extract_citations(text)
    url_cites = [c for c in result.citations if c.kind == "url"]
    assert any(c.url == "https://example.com" for c in url_cites)


def test_extract_citations_footnote():
    text = "See note [1].\n\n[1] Source Title. https://source.com"
    result = extract_citations(text)
    footnote = next((c for c in result.citations if c.index == 1), None)
    assert footnote is not None


def test_extract_citations_by_index():
    text = "See [1] and [2]."
    result = extract_citations(text)
    c1 = result.by_index(1)
    assert c1 is not None
    assert c1.index == 1


def test_extract_citations_by_index_missing():
    result = extract_citations("no refs")
    assert result.by_index(1) is None


def test_extract_citations_urls():
    text = "[Source](https://src.com) and https://other.com"
    result = extract_citations(text)
    urls = result.urls()
    assert "https://src.com" in urls


def test_strip_citations_removes_markdown_links():
    text = "Check [OpenAI](https://openai.com) for info."
    cleaned = strip_citations(text)
    assert "https://openai.com" not in cleaned
    assert "OpenAI" in cleaned


def test_strip_citations_no_change_plain():
    text = "Plain text."
    cleaned = strip_citations(text)
    assert "Plain text" in cleaned


def test_citation_count():
    result = extract_citations("See [1] and [2] and [3].")
    assert result.count >= 2


def test_citation_dataclass():
    c = Citation(index=1, text="[1]", kind="numbered")
    assert c.index == 1
    assert c.url is None


def test_citation_result_has_references_false():
    result = extract_citations("just text")
    assert result.has_references is False
