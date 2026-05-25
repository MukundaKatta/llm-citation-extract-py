# llm-citation-extract-py

Extract citations and references from LLM output. Handles numbered inline refs, URLs, markdown links, and footnote-style references.

## Install

```bash
pip install llm-citation-extract-py
```

## Usage

```python
from llm_citation_extract import extract_citations, extract_urls, extract_numbered_refs, strip_citations

text = """See [OpenAI](https://openai.com) and also [1] for details.

[1] Source Title. https://source.com"""

result = extract_citations(text)
result.count            # number of citations
result.has_references   # True
result.citations        # list of Citation objects
result.urls()           # all URLs found
result.by_index(1)      # Citation with index==1

for c in result.citations:
    print(c.kind, c.index, c.url, c.text)

# Helpers
urls = extract_urls(text)            # ["https://openai.com", ...]
refs = extract_numbered_refs(text)   # [1]
clean = strip_citations(text)        # remove markers, keep prose
```

## License

MIT
