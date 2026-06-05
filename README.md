# pdf-toc-extractor

We will probably have superintelligence before we can reliably parse a PDF. I built this out of pure necessity: I needed to feed long, structured documents (benefit booklets, government standards, tax guides) to an LLM without spending the whole context window on the pages that did not matter.

It reads a document's table of contents, works out how the printed page numbers map to the actual PDF pages, splits the document into its real sections, and writes a compact, token-efficient index that an LLM can use to pick the handful of sections it actually needs.

## What it does

- Detects the table of contents from the document text, whether it sits on one page or spans several.
- Learns the page offset (printed "page 47" versus the real PDF page) two ways: by matching section titles to the pages they start on, and, when a document carries a running header that hides those titles, by reading the printed page numbers in the margins.
- Rebuilds the section hierarchy from either leader keywords (PART / SECTION / CHAPTER) or the x-positions of the TOC entries.
- Writes each section to its own text file, a JSONL index, and a compact selection guide sized for an LLM to choose from.

## Worked example

The repo ships a public-domain sample, NIST Special Publication 800-53 Rev. 5 (492 pages):

```
pip install -e .
pdf-toc-extractor sample_nist_sp800-53.pdf
```

```
TOC detected: pages 15-15
Inferred page offset: +27
Extracted 39 sections
```

The generated selection guide (trimmed):

```
[002] CHAPTER ONE INTRODUCTION (p.1, 12K)
  [003] 1.1 PURPOSE AND APPLICABILITY (p.2, 12K)
  [005] 1.3 ORGANIZATIONAL RESPONSIBILITIES (p.3, 13K)
[015] CHAPTER THREE THE CONTROLS (p.16, 11K)
  [016] 3.1 ACCESS CONTROL (p.18, 162K)
  [018] 3.3 AUDIT AND ACCOUNTABILITY (p.65, 69K)
  [031] 3.16 RISK ASSESSMENT (p.238, 48K)
[037] APPENDIX A GLOSSARY (p.394, 92K)
```

A page offset of +27 means printed page 1 is the 28th page of the PDF. The tool worked that out on its own by reading the page numbers in the margins, since every NIST page repeats the same title in its header.

## Library usage

```python
from pdf_toc_extractor import extract_pdf_sections

result = extract_pdf_sections("document.pdf")
print(len(result.sections), "sections, offset", result.page_offset)

for s in result.sections[:5]:
    print(s.id, s.title, s.start_page, "-", s.end_page)
```

`extract_pdf_sections` writes a `<name>_extracted/` directory containing `sections/`, `toc_master_complete.jsonl`, and the LLM interface files (`toc_selection.txt`, `toc_compact.txt`, `file_mapping.json`).

## How it works

The pipeline lives in `pdf_toc_extractor/core/`:

- `parser.py` finds the TOC block and parses entries, including multi-line and orphaned-title cases.
- `hierarchy.py` assigns levels, from leader keywords or x-position.
- `extractor.py` learns the page offset, validates it, and slices the document into sections.
- `llm/interface.py` builds the compact, token-efficient views.

`PDFTOCExtractor.extract()` in `extractor.py` is the place to start reading.

## Scope and limits

This works on documents that have a real, text-based table of contents with leader-dot page references: policy and benefit booklets, government standards, tax guides, technical manuals. It is not an OCR tool, and it does not invent structure for a document that has no contents page. Scanned PDFs with no text layer are out of scope.

## Notes

The bundled sample is NIST SP 800-53 Rev. 5, a public-domain US government publication, included only to demonstrate extraction. The tool reads documents; it never modifies them.

## License

MIT. See [LICENSE](LICENSE).
