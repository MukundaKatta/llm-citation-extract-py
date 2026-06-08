"""Tests for llm-citation-extract-py.

These tests use only the Python standard library (``unittest``) so they run
with::

    python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

# Make ``src/`` importable when tests are run from the repo root without an
# editable install. Harmless if the package is already installed.
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from llm_citation_extract import (  # noqa: E402
    Citation,
    CitationResult,
    extract_citations,
    extract_numbered_refs,
    extract_urls,
    strip_citations,
)


class ExtractNumberedRefsTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(extract_numbered_refs("See [1] and [2] for details."), [1, 2])

    def test_no_refs(self):
        self.assertEqual(extract_numbered_refs("no refs here"), [])

    def test_unique(self):
        self.assertEqual(extract_numbered_refs("[1] and [1] again."), [1])

    def test_sorted(self):
        self.assertEqual(extract_numbered_refs("[3] then [1] then [2]"), [1, 2, 3])

    def test_ignores_markdown_links(self):
        # "[1](url)" is a link, not a numbered ref.
        self.assertEqual(extract_numbered_refs("[1](https://x.com)"), [])


class ExtractUrlsTests(unittest.TestCase):
    def test_basic(self):
        self.assertIn(
            "https://example.com", extract_urls("See https://example.com for info.")
        )

    def test_multiple(self):
        self.assertEqual(
            len(extract_urls("Visit https://a.com and https://b.com")), 2
        )

    def test_none(self):
        self.assertEqual(extract_urls("no URLs here"), [])

    def test_deduped(self):
        urls = extract_urls("https://example.com is at https://example.com")
        self.assertEqual(urls.count("https://example.com"), 1)

    def test_order_preserved(self):
        self.assertEqual(
            extract_urls("https://b.com then https://a.com"),
            ["https://b.com", "https://a.com"],
        )

    def test_trailing_period_stripped(self):
        # Regression: a URL ending a sentence must not keep the period.
        self.assertEqual(extract_urls("See https://example.com."), ["https://example.com"])

    def test_trailing_question_mark_stripped(self):
        self.assertEqual(extract_urls("Q https://example.com?"), ["https://example.com"])

    def test_trailing_exclamation_stripped(self):
        self.assertEqual(extract_urls("Wow https://example.com!"), ["https://example.com"])

    def test_trailing_semicolon_and_colon_stripped(self):
        self.assertEqual(
            extract_urls("a https://example.com; b https://other.com:"),
            ["https://example.com", "https://other.com"],
        )

    def test_url_path_preserved(self):
        self.assertEqual(
            extract_urls("Path https://example.com/a/b/c end."),
            ["https://example.com/a/b/c"],
        )

    def test_unbalanced_trailing_paren_stripped(self):
        self.assertEqual(
            extract_urls("(see https://example.com)"), ["https://example.com"]
        )


class ExtractCitationsTests(unittest.TestCase):
    def test_result_type(self):
        result = extract_citations("Hello world.")
        self.assertIsInstance(result, CitationResult)
        self.assertIsInstance(result.citations, list)

    def test_no_refs(self):
        result = extract_citations("Plain text with no citations.")
        self.assertFalse(result.has_references)
        self.assertEqual(result.count, 0)

    def test_empty_string(self):
        result = extract_citations("")
        self.assertEqual(result.count, 0)
        self.assertFalse(result.has_references)
        self.assertEqual(result.cleaned_text, "")

    def test_numbered_inline(self):
        result = extract_citations("This is supported [1] and also [2].")
        self.assertTrue(result.has_references)
        numbered = [c for c in result.citations if c.kind == "numbered"]
        self.assertTrue(any(c.index == 1 for c in numbered))
        self.assertTrue(any(c.index == 2 for c in numbered))

    def test_markdown_link(self):
        result = extract_citations("Check [OpenAI](https://openai.com) for details.")
        md_links = [c for c in result.citations if c.kind == "markdown_link"]
        self.assertGreaterEqual(len(md_links), 1)
        self.assertEqual(md_links[0].url, "https://openai.com")
        self.assertEqual(md_links[0].label, "OpenAI")

    def test_bare_url(self):
        result = extract_citations("Visit https://example.com for more.")
        url_cites = [c for c in result.citations if c.kind == "url"]
        self.assertTrue(any(c.url == "https://example.com" for c in url_cites))

    def test_bare_url_trailing_period(self):
        # Regression: bare URL citation should not include trailing punctuation.
        result = extract_citations("Visit https://example.com.")
        url_cites = [c for c in result.citations if c.kind == "url"]
        self.assertEqual([c.url for c in url_cites], ["https://example.com"])

    def test_footnote(self):
        text = "See note [1].\n\n[1] Source Title. https://source.com"
        result = extract_citations(text)
        footnote = result.by_index(1)
        self.assertIsNotNone(footnote)

    def test_footnote_url_trailing_period(self):
        text = "See note [1].\n\n[1] Source Title. https://source.com."
        result = extract_citations(text)
        self.assertEqual(result.by_index(1).url, "https://source.com")

    def test_by_index(self):
        result = extract_citations("See [1] and [2].")
        c1 = result.by_index(1)
        self.assertIsNotNone(c1)
        self.assertEqual(c1.index, 1)

    def test_by_index_missing(self):
        self.assertIsNone(extract_citations("no refs").by_index(1))

    def test_urls_collects_all(self):
        result = extract_citations("[Source](https://src.com) and https://other.com")
        self.assertIn("https://src.com", result.urls())
        self.assertIn("https://other.com", result.urls())

    def test_grouped_indices(self):
        result = extract_citations("See [1,2] and [3-4].")
        indices = sorted(c.index for c in result.citations if c.kind == "numbered")
        self.assertEqual(indices, [1, 2, 3, 4])

    def test_numbered_sorted_first(self):
        result = extract_citations("https://a.com then [2] then [1]")
        numbered = [c.index for c in result.citations if c.index is not None]
        self.assertEqual(numbered, [1, 2])

    def test_count(self):
        self.assertGreaterEqual(extract_citations("See [1] and [2] and [3].").count, 2)


class StripCitationsTests(unittest.TestCase):
    def test_removes_markdown_links(self):
        cleaned = strip_citations("Check [OpenAI](https://openai.com) for info.")
        self.assertNotIn("https://openai.com", cleaned)
        self.assertIn("OpenAI", cleaned)

    def test_no_change_plain(self):
        self.assertIn("Plain text", strip_citations("Plain text."))

    def test_removes_numbered_markers(self):
        cleaned = strip_citations("This is supported [1] and also [2].")
        self.assertNotIn("[1]", cleaned)
        self.assertNotIn("[2]", cleaned)
        self.assertIn("supported", cleaned)
        self.assertIn("also", cleaned)

    def test_no_double_spaces(self):
        cleaned = strip_citations("a [1] b [2] c")
        self.assertNotIn("  ", cleaned)
        self.assertEqual(cleaned, "a b c")

    def test_removes_grouped_markers(self):
        cleaned = strip_citations("See refs [1,2] and [3-4] here.")
        self.assertNotIn("[", cleaned)
        self.assertIn("refs", cleaned)
        self.assertIn("here", cleaned)


class CitationResultTests(unittest.TestCase):
    def test_has_references_false(self):
        self.assertFalse(extract_citations("just text").has_references)

    def test_cleaned_text_keeps_markdown_label(self):
        result = extract_citations("Check [OpenAI](https://openai.com) for info.")
        self.assertIn("OpenAI", result.cleaned_text)
        self.assertNotIn("https://openai.com", result.cleaned_text)

    def test_urls_skips_none(self):
        # Numbered-only citations have no URL; urls() must not include None.
        result = extract_citations("See [1] and [2].")
        self.assertEqual(result.urls(), [])


class CitationDataclassTests(unittest.TestCase):
    def test_defaults(self):
        c = Citation(index=1, text="[1]", kind="numbered")
        self.assertEqual(c.index, 1)
        self.assertIsNone(c.url)
        self.assertIsNone(c.label)

    def test_url_field(self):
        c = Citation(index=None, text="x", url="https://x.com", kind="url")
        self.assertEqual(c.url, "https://x.com")


if __name__ == "__main__":
    unittest.main()
