# llm-citation-extract-py

[![CI](https://github.com/MukundaKatta/llm-citation-extract-py/actions/workflows/ci.yml/badge.svg)](https://github.com/MukundaKatta/llm-citation-extract-py/actions/workflows/ci.yml)

Extract citations and references from LLM output. Handles numbered inline refs,
bare URLs, markdown links, and footnote-style references — with zero runtime
dependencies (standard library only).

## Install

```bash
pip install llm-citation-extract-py
```

## Usage

```python
from llm_citation_extract import (
    extract_citations,
    extract_urls,
    extract_numbered_refs,
    strip_citations,
)

text = """See [OpenAI](https://openai.com) and also [1] for details.

[1] Source Title. https://source.com"""

result = extract_citations(text)
result.count            # number of citations
result.has_references   # True
result.citations        # list[Citation]
result.urls()           # all URLs found (None entries skipped)
result.by_index(1)      # the Citation whose index == 1, or None

for c in result.citations:
    print(c.kind, c.index, c.url, c.text)

# Standalone helpers
extract_urls(text)            # ['https://openai.com', 'https://source.com']
extract_numbered_refs(text)   # [1]
strip_citations(text)         # prose with inline markers removed
```

## API

### `extract_citations(text: str) -> CitationResult`

Parse `text` and return a `CitationResult`. Recognises:

- **Markdown links** — `[label](https://...)` → `kind="markdown_link"`
- **Bare URLs** — `https://...` → `kind="url"`
- **Numbered inline refs** — `[1]`, `[1,2]`, `[1-3]` → `kind="numbered"`
- **Footnote definitions** — a line like `[1] Source Title. https://...`
  → `kind="footnote"` (or it enriches an existing numbered citation).

Numbered citations are returned first, sorted by index, followed by the rest in
discovery order.

### `extract_urls(text: str) -> list[str]`

Return all URLs, deduplicated and in first-seen order. Sentence-trailing
punctuation is stripped, so `"see https://x.com."` yields `"https://x.com"`.

### `extract_numbered_refs(text: str) -> list[int]`

Return the sorted, unique set of numeric inline reference indices (e.g. `[1]`,
`[2]`). Markdown links such as `[1](url)` are not treated as numbered refs.

### `strip_citations(text: str) -> str`

Return the prose with inline citation markers removed. Markdown links collapse
to their label text; numbered markers are deleted along with a single preceding
space so no double spaces are left behind.

### `Citation`

Dataclass with fields: `index` (`int | None`), `text` (`str`), `url`
(`str | None`), `label` (`str | None`), `kind` (`str`).

### `CitationResult`

Dataclass with `citations` (`list[Citation]`), `cleaned_text` (`str`), and
`has_references` (`bool`). Convenience members: `count` (property),
`by_index(n)`, and `urls()`.

## Development

Run the test suite with the standard library only:

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT
