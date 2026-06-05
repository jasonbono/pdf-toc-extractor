"""
Utility functions for PDF TOC extraction.
"""

import re
from slugify import slugify
from rapidfuzz import fuzz

def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()

def create_slug(title: str, max_length: int = 60) -> str:
    """Create a URL-safe slug from a title"""
    return slugify(title)[:max_length]

def looks_like_top_heading(title: str) -> bool:
    """Check if a title looks like a major section heading"""
    t = title.strip()

    # Original patterns for hierarchical documents
    if (t.upper().startswith(("SECTION", "PART", "ARTICLE", "CHAPTER")) or
        re.match(r"^\d+[\.\‑ ]", t) is not None):
        return True

    # Additional patterns for flat documents
    major_keywords = ['introduction', 'summary', 'overview', 'benefits', 'coverage', 'definitions']
    if any(keyword in t.lower() for keyword in major_keywords):
        return True

    return False

def text_similarity(text1: str, text2: str) -> float:
    """Calculate text similarity using fuzzy matching"""
    return fuzz.token_set_ratio(normalize_text(text1), normalize_text(text2)) / 100.0

def format_section_size(chars: int) -> str:
    """Format section size for display"""
    if chars < 1000:
        return f"{chars}B"
    elif chars < 10000:
        return f"{chars//1000}K"
    else:
        return f"{chars//1000}K"

def get_section_type(title: str, level: int, chars: int) -> str:
    """Determine section type for LLM guidance"""
    title_upper = title.upper()

    # Level 0 entries are generally organizational structure
    if level == 0:
        if title_upper.startswith(('PART ', 'SECTION ')):
            return "ORG"  # Organizational structure
        if title_upper in ['TABLE OF CONTENTS', 'INTRODUCTION']:
            return "ORG"  # Organizational structure
        if chars > 15000:
            return "LARGE"  # Large organizational content

    # Large sections regardless of level
    if chars > 15000:
        return "LARGE"

    return "CONTENT"  # Regular content section