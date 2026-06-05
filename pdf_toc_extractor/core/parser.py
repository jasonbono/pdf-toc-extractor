"""
TOC parsing functionality for PDF documents.
"""

import re
from typing import List, Tuple, Optional
import fitz
from ..types import TOCEntry
from .utils import normalize_text, text_similarity

# TOC line pattern: title followed by dots/leaders and page number
TOC_LINE_PATTERN = re.compile(r"^(.*?\S)\s*[\.…\u2022·•]+\s*(\d+)\s*$")

# Minimum leader-dot entries for a page to count as part of a TOC.
MIN_TOC_LINES = 3
# A single page with at least this many entries is accepted as a one-page TOC,
# for the many documents whose contents do not span multiple pages.
STRONG_SINGLE_PAGE = 8


def find_toc_block(doc: fitz.Document, max_scan_pages: int = 25) -> Tuple[int, int]:
    """
    Find the Table of Contents block in the document.

    Returns:
        Tuple of (start_page, end_page) of TOC block

    Raises:
        ValueError: If no TOC is detected
    """
    streak, start = 0, None
    best_page, best_hits = 0, 0

    for page_num in range(min(max_scan_pages, len(doc))):
        text = doc[page_num].get_text("text")
        # Count lines that match the TOC pattern
        toc_lines = sum(1 for line in text.splitlines() if TOC_LINE_PATTERN.match(line))
        if toc_lines > best_hits:
            best_page, best_hits = page_num, toc_lines
        has_toc = toc_lines >= MIN_TOC_LINES

        if has_toc:
            streak = streak + 1 if streak else 1
            start = page_num if start is None else start
        else:
            if streak >= 2:  # Prefer a run of 2+ consecutive TOC pages
                return start, page_num - 1
            streak, start = 0, None

    if streak >= 2:  # TOC runs to the end of the scanned range
        return start, min(max_scan_pages, len(doc)) - 1

    # Fall back to the single strongest page, for documents whose table of
    # contents fits on one page.
    if best_hits >= STRONG_SINGLE_PAGE:
        return best_page, best_page

    raise ValueError("No TOC detected in first pages")

def parse_toc_entries(doc: fitz.Document, start_page: int, end_page: int) -> List[Tuple[str, int]]:
    """
    Parse TOC entries from the specified page range.

    Args:
        doc: The PDF document
        start_page: Starting page of TOC (0-indexed)
        end_page: Ending page of TOC (0-indexed)

    Returns:
        List of (title, page_number) tuples
    """
    # Get all text lines for multi-line parsing
    all_lines = []
    for page_num in range(start_page, end_page + 1):
        page_lines = doc[page_num].get_text("text").splitlines()
        all_lines.extend([(line.strip(), page_num) for line in page_lines if line.strip()])

    entries = []
    i = 0

    while i < len(all_lines):
        line, page_num = all_lines[i]

        # Try single-line pattern first
        match = TOC_LINE_PATTERN.match(line)
        if match:
            title, page_str = match.groups()
            entries.append((title.strip(), int(page_str)))
            i += 1
            continue

        # Check for orphaned title (title without page number on same line)
        if (line and not re.match(r'^[\.…\u2022·•\s\d]+$', line) and
            len(line) > 10 and i + 1 < len(all_lines)):

            next_line, next_page_num = all_lines[i + 1]
            next_match = TOC_LINE_PATTERN.match(next_line)

            if next_match:
                # Next line is a proper TOC entry, current line is orphaned title
                next_title, next_page = next_match.groups()
                entries.append((line.strip(), int(next_page)))
                i += 1
                continue

        # Check for multi-line pattern
        if line and not re.match(r'^[\.…\u2022·•\s\d]+$', line):
            potential_title_parts = [line]
            j = i + 1
            found_page = False

            # Look ahead for the page number (max 4 lines)
            while j < len(all_lines) and j < i + 4:
                next_line, next_page_num = all_lines[j]

                # Check if this line contains a page number at the end
                page_match = re.search(r'\b(\d+)\s*$', next_line)
                if page_match:
                    page_number = int(page_match.group(1))

                    # Extract any title text before the page number
                    title_part = re.sub(r'\s*\b\d+\s*$', '', next_line).strip()
                    title_part = re.sub(r'^[\.…\u2022·•\s]+', '', title_part).strip()
                    title_part = re.sub(r'[\.…\u2022·•\s]+$', '', title_part).strip()

                    if title_part and len(title_part) > 2:
                        potential_title_parts.append(title_part)

                    # Combine all parts into full title
                    full_title = ' '.join(potential_title_parts).strip()
                    full_title = re.sub(r'[\.…\u2022·•\s]+$', '', full_title).strip()

                    if full_title and len(full_title) > 3:
                        entries.append((full_title, page_number))
                        found_page = True
                        i = j + 1
                        break
                else:
                    # Check if this line is a continuation of the title
                    clean_line = re.sub(r'^[\.…\u2022·•\s]+', '', next_line).strip()
                    clean_line = re.sub(r'[\.…\u2022·•\s]+$', '', clean_line).strip()

                    if clean_line and len(clean_line) > 2 and not re.match(r'^\d+$', clean_line):
                        potential_title_parts.append(clean_line)

                j += 1

            if not found_page:
                i += 1
        else:
            i += 1

    if len(entries) < 5:
        raise ValueError("TOC too small (less than 5 entries)")

    return entries

def parse_toc_with_positioning(doc: fitz.Document, start_page: int, end_page: int) -> List[Tuple[str, int, float]]:
    """
    Parse TOC entries with their X-positions for hierarchy detection.

    Returns:
        List of (title, page_number, x_position) tuples
    """
    # First get all text lines for orphaned title detection
    all_text_lines = []
    for page_num in range(start_page, end_page + 1):
        page_lines = doc[page_num].get_text("text").splitlines()
        all_text_lines.extend([(line.strip(), page_num) for line in page_lines if line.strip()])

    # Find orphaned titles
    orphaned_titles = {}  # line_text -> page_number
    i = 0
    while i < len(all_text_lines):
        line, page_num = all_text_lines[i]

        if (line and not re.match(r'^[\.…\u2022·•\s\d]+$', line) and
            len(line) > 10 and i + 1 < len(all_text_lines)):

            next_line, next_page_num = all_text_lines[i + 1]
            next_match = TOC_LINE_PATTERN.match(next_line)

            if next_match:
                next_title, next_page = next_match.groups()
                orphaned_titles[line.strip()] = int(next_page)

        i += 1

    # Extract positioned entries
    entries = []

    for page_num in range(start_page, end_page + 1):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    # Reconstruct the complete line text and bounding box
                    line_text = ""
                    line_bbox = None

                    for span in line["spans"]:
                        line_text += span["text"]
                        if line_bbox is None:
                            line_bbox = span["bbox"]
                        else:
                            # Expand bbox to include this span
                            line_bbox = [
                                min(line_bbox[0], span["bbox"][0]),  # min x0
                                min(line_bbox[1], span["bbox"][1]),  # min y0
                                max(line_bbox[2], span["bbox"][2]),  # max x1
                                max(line_bbox[3], span["bbox"][3])   # max y1
                            ]

                    line_text = line_text.strip()
                    x_position = line_bbox[0] if line_bbox else 0

                    # Check if it matches TOC pattern
                    if TOC_LINE_PATTERN.match(line_text):
                        match = TOC_LINE_PATTERN.match(line_text)
                        if match:
                            title, page_str = match.groups()
                            title = title.strip()
                            entries.append((title, int(page_str), x_position))

                    # Check if it's an orphaned title
                    elif line_text in orphaned_titles:
                        page_number = orphaned_titles[line_text]
                        entries.append((line_text, page_number, x_position))

    return entries

def find_title_in_document(doc: fitz.Document, title: str, search_start: int, search_end: int,
                          toc_end_page: int) -> Optional[int]:
    """
    Find the page where a title actually appears in the document.

    Args:
        doc: The PDF document
        title: The title to search for
        search_start: Start page for search
        search_end: End page for search
        toc_end_page: End page of TOC (to skip)

    Returns:
        Page number where title is found, or None
    """
    title_normalized = normalize_text(title)
    short_title = " ".join(title_normalized.split()[:7])  # First 7 words

    for page_num in range(search_start, min(search_end + 1, len(doc))):
        if page_num <= toc_end_page:  # Skip TOC pages
            continue

        page = doc[page_num]
        height = page.bound().height

        # Get text from top 25% of page (headers)
        header_text = " ".join(
            block[4] for block in page.get_text("blocks")
            if block[1] < 0.25 * height  # block[1] = top-Y coord
        )

        if text_similarity(short_title, header_text) >= 0.65:
            return page_num

    # Fallback: many documents carry a running header at the top of every page
    # (such as the document title), leaving the section heading lower down. Look
    # for the title as a contiguous match anywhere on the page. Newlines are
    # turned into spaces so multi-line headings survive normalization.
    if len(short_title) >= 8:
        for page_num in range(search_start, min(search_end + 1, len(doc))):
            if page_num <= toc_end_page:
                continue
            raw = " ".join(block[4] for block in doc[page_num].get_text("blocks"))
            page_text = " ".join(normalize_text(raw.replace("\n", " ")).split())
            if short_title in page_text:
                return page_num

    return None