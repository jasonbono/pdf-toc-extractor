"""
Main PDF TOC extraction engine.
"""

import json
import re
import statistics
from pathlib import Path
from typing import List, Optional, Dict, Any
import fitz

from ..types import TOCEntry, ExtractedSection, ExtractionResult, ExtractionConfig
from .parser import find_toc_block, parse_toc_entries, parse_toc_with_positioning, find_title_in_document
from .hierarchy import (detect_hierarchy_from_positioning, detect_hierarchy_from_keywords,
                       has_meaningful_positioning_hierarchy, assign_section_ids)
from .utils import normalize_text, create_slug, looks_like_top_heading

class PDFTOCExtractor:
    """Main class for extracting Table of Contents and sections from PDFs."""

    def __init__(self, config: Optional[ExtractionConfig] = None):
        """Initialize the extractor with configuration."""
        self.config = config or ExtractionConfig()

    def extract(self, pdf_path: Path) -> ExtractionResult:
        """
        Extract TOC and sections from a PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            ExtractionResult containing all extracted data
        """
        doc = fitz.open(pdf_path)

        try:
            # Step 1: Detect TOC block
            toc_start, toc_end = find_toc_block(doc, self.config.max_scan_pages)
            print(f"TOC detected: pages {toc_start+1}-{toc_end+1}")

            # Step 2: Parse TOC entries and detect hierarchy
            toc_entries = parse_toc_entries(doc, toc_start, toc_end)
            hierarchical_entries = self._detect_hierarchy(doc, toc_start, toc_end, toc_entries)

            print(f"Parsed {len(toc_entries)} TOC entries with hierarchy")

            # Step 3: Learn page offset
            page_offset = self._learn_page_offset(doc, hierarchical_entries, toc_end)

            # Handle page_offset type safely for display
            try:
                if isinstance(page_offset, str):
                    display_offset = int(page_offset) if page_offset.lstrip('+-').isdigit() else page_offset
                else:
                    display_offset = page_offset
                print(f"Inferred page offset: {display_offset:+d}" if isinstance(display_offset, int) else f"Inferred page offset: {display_offset}")
            except (ValueError, TypeError):
                print(f"Inferred page offset: {page_offset}")

            # Step 4: Extract sections
            sections = self._extract_sections(doc, hierarchical_entries, page_offset)

            # Step 5: Save sections if requested
            if self.config.save_sections and self.config.output_dir:
                self._save_sections(sections, self.config.output_dir)

            return ExtractionResult(
                sections=sections,
                toc_entries=hierarchical_entries,
                total_pages=len(doc),
                toc_start_page=toc_start,
                toc_end_page=toc_end,
                page_offset=page_offset,
                hierarchy_type=self._determine_hierarchy_type(hierarchical_entries)
            )

        finally:
            doc.close()

    def _detect_hierarchy(self, doc: fitz.Document, toc_start: int, toc_end: int,
                         toc_entries: List[tuple]) -> List[TOCEntry]:
        """Detect hierarchy using positioning or keywords."""
        # Try positioning-based hierarchy detection first
        entries_with_positions = parse_toc_with_positioning(doc, toc_start, toc_end)
        hierarchical_entries = detect_hierarchy_from_positioning(entries_with_positions)

        if has_meaningful_positioning_hierarchy(hierarchical_entries):
            print(f"Using positioning-based hierarchy ({len(set(e.level for e in hierarchical_entries))} levels)")
            return assign_section_ids(hierarchical_entries)
        else:
            print("Using keyword-based hierarchy detection")
            hierarchical_entries = detect_hierarchy_from_keywords(toc_entries)
            return assign_section_ids(hierarchical_entries)

    def _learn_page_offset(self, doc: fitz.Document, entries: List[TOCEntry], toc_end: int) -> int:
        """Learn the page offset that maps printed page numbers to PDF indices.

        First tries matching major section titles to the pages they appear on.
        If that does not yield a stable answer, falls back to reading the printed
        page numbers in the page margins, which does not depend on the TOC.
        """
        # Use major sections for offset detection
        major_sections = self._get_major_sections(entries)

        offsets = []
        probe_entries = [e for e in major_sections if looks_like_top_heading(e.title)][:15]

        for entry in probe_entries:
            match_page = find_title_in_document(
                doc, entry.title,
                max(0, entry.page - 10),  # Search window
                entry.page + 80,
                toc_end
            )
            if match_page is not None:
                offsets.append(match_page - entry.page + 1)

        # Find the most common offset (within ±1)
        offset_counts = {}
        for offset in offsets:
            rounded = round(offset)
            offset_counts[rounded] = offset_counts.get(rounded, 0) + 1

        if offset_counts:
            best_offset, hits = max(offset_counts.items(), key=lambda x: x[1])
            if hits >= 2:
                self._validate_offset(doc, probe_entries, best_offset, toc_end)
                return best_offset

        # Fall back to printed page numbers in the margins.
        offset = self._learn_offset_from_page_numbers(doc, toc_end)
        if offset is not None:
            return offset

        raise RuntimeError("Could not infer a stable page offset")

    def _learn_offset_from_page_numbers(self, doc: fitz.Document, toc_end: int,
                                        scan_pages: int = 60) -> Optional[int]:
        """Infer the page offset from printed page numbers in the page margins.

        Reads integers printed in the top or bottom margin of each page after the
        TOC and returns the offset (PDF page minus printed page) that the most
        pages agree on. Independent of section titles, so it works on documents
        whose headings are not page headers.
        """
        counts = {}
        last = min(len(doc), toc_end + 1 + scan_pages)
        for i in range(toc_end + 1, last):
            page = doc[i]
            height = page.bound().height
            for block in page.get_text("blocks"):
                y0, y1, text = block[1], block[3], block[4].strip()
                if not (y0 < 0.15 * height or y1 > 0.85 * height):
                    continue
                for token in re.findall(r"\b\d{1,4}\b", text):
                    printed = int(token)
                    if 1 <= printed <= len(doc):
                        offset = (i + 1) - printed
                        counts[offset] = counts.get(offset, 0) + 1
        if not counts:
            return None
        best_offset, hits = max(counts.items(), key=lambda kv: kv[1])
        return best_offset if hits >= 3 else None

    def _get_major_sections(self, entries: List[TOCEntry]) -> List[TOCEntry]:
        """Get major sections for offset detection."""
        # For different hierarchy types, use different criteria
        positioning_levels = [e for e in entries if e.level == 0]
        keyword_levels = [e for e in entries if e.level_name in ['part', 'section', 'special']]

        if positioning_levels:
            return positioning_levels
        elif keyword_levels:
            return keyword_levels
        else:
            # For flat documents, use orphan entries
            return [e for e in entries if e.level_name == 'orphan']

    def _validate_offset(self, doc: fitz.Document, probe_entries: List[TOCEntry],
                        offset: int, toc_end: int) -> None:
        """Validate the learned offset."""
        matches = 0

        for entry in probe_entries:
            predicted_page = entry.page + offset
            if predicted_page < 0 or predicted_page >= len(doc):
                continue

            # Search in predicted page ±2
            found = False
            for p in range(max(0, predicted_page - 2), min(len(doc), predicted_page + 3)):
                raw = " ".join(block[4] for block in doc[p].get_text("blocks"))
                page_text = " ".join(normalize_text(raw.replace("\n", " ")).split())
                needle = " ".join(normalize_text(entry.title[:50].replace("\n", " ")).split())
                if needle and needle in page_text:
                    found = True
                    break

            if found:
                matches += 1

        success_ratio = matches / len(probe_entries) if probe_entries else 0

        if success_ratio < 0.5:
            raise RuntimeError(f"Offset validation failed ({success_ratio:.1%} success rate)")
        elif success_ratio < 0.7:
            print(f"Warning: offset validation only {success_ratio:.1%} successful")

    def _extract_sections(self, doc: fitz.Document, entries: List[TOCEntry],
                         page_offset: int) -> List[ExtractedSection]:
        """Extract text content for each section."""
        sections = []

        for i, entry in enumerate(entries):
            # Calculate section boundaries with overlap
            start_page = entry.page + page_offset

            if i + 1 < len(entries):
                next_start = entries[i + 1].page + page_offset
                end_page = next_start + self.config.overlap_pages - 1
            else:
                end_page = len(doc)

            # Ensure bounds are valid
            start_page = max(1, start_page)
            end_page = min(len(doc), end_page)

            if start_page > len(doc):
                continue

            # Extract text (convert to 0-indexed for PyMuPDF)
            start_0idx = start_page - 1
            end_0idx = end_page - 1

            text_chunks = []
            for p in range(start_0idx, end_0idx + 1):
                if p < len(doc):
                    # PDF page number (1-indexed for display)
                    pdf_page_num = p + 1
                    # Printed page number (calculated from PDF page - offset)
                    # Note: The offset is typically positive, meaning PDF pages are ahead of printed pages
                    printed_page_num = p + 1 - page_offset

                    # Add page marker
                    # Format: [PDF p123 | Print p114]
                    page_marker = f"\n[PDF p{pdf_page_num} | Print p{printed_page_num}]\n"

                    # Get page text
                    page_text = doc[p].get_text("text").strip()

                    if page_text:
                        text_chunks.append(page_marker + page_text)

            content = "\n\n".join(text_chunks).strip()

            section = ExtractedSection(
                id=str(i + 1),
                title=" ".join(entry.title.split()),
                content=content,
                start_page=start_page,
                end_page=end_page,
                printed_page=entry.page,
                chars=len(content),
                hierarchy_level=entry.level,
                level_name=entry.level_name,
                parent_title=entry.parent_title
            )

            sections.append(section)

        return sections

    def _save_sections(self, sections: List[ExtractedSection], output_dir: Path) -> None:
        """Save sections to individual files and create index."""
        sections_dir = output_dir / "sections"
        sections_dir.mkdir(parents=True, exist_ok=True)

        # Save individual section files
        for section in sections:
            slug = create_slug(section.title)
            try:
                section_id = int(section.id)
                filename = f"{section_id:03d}_{slug}.txt"
            except ValueError:
                filename = f"{section.id}_{slug}.txt"
            file_path = sections_dir / filename

            file_path.write_text(section.content, encoding='utf-8')
            section.file_path = file_path

        # Save master index as JSONL
        index_file = output_dir / "toc_master_complete.jsonl"
        with index_file.open('w', encoding='utf-8') as f:
            for section in sections:
                entry = {
                    'id': int(section.id),
                    'title': section.title,
                    'file': str(section.file_path.relative_to(output_dir)),
                    'start_page': section.start_page,
                    'end_page': section.end_page,
                    'printed_page': section.printed_page,
                    'chars': section.chars,
                    'hierarchy_level': section.hierarchy_level,
                    'level_name': section.level_name,
                    'parent_title': section.parent_title
                }
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        print(f"Saved {len(sections)} sections to {sections_dir}")
        print(f"Created index: {index_file}")

    def _determine_hierarchy_type(self, entries: List[TOCEntry]) -> str:
        """Determine the type of hierarchy detection used."""
        if any(e.x_position is not None for e in entries):
            return "positioning"
        else:
            return "keyword"

def extract_pdf_toc(pdf_path: Path, config: Optional[ExtractionConfig] = None) -> ExtractionResult:
    """
    Convenience function to extract TOC from a PDF.

    Args:
        pdf_path: Path to the PDF file
        config: Optional configuration

    Returns:
        ExtractionResult containing all extracted data
    """
    extractor = PDFTOCExtractor(config)
    return extractor.extract(pdf_path)