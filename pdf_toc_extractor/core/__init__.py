"""Core PDF extraction functionality."""

from .extractor import PDFTOCExtractor, extract_pdf_toc
from .parser import find_toc_block, parse_toc_entries, parse_toc_with_positioning
from .hierarchy import detect_hierarchy_from_positioning, detect_hierarchy_from_keywords
from .utils import normalize_text, create_slug, looks_like_top_heading, text_similarity

__all__ = [
    'PDFTOCExtractor',
    'extract_pdf_toc',
    'find_toc_block',
    'parse_toc_entries',
    'parse_toc_with_positioning',
    'detect_hierarchy_from_positioning',
    'detect_hierarchy_from_keywords',
    'normalize_text',
    'create_slug',
    'looks_like_top_heading',
    'text_similarity'
]