"""
Data structures and types for PDF TOC extraction.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path

@dataclass
class TOCEntry:
    """A single entry from the Table of Contents"""
    title: str
    page: int
    level: int = 0
    level_name: str = "unknown"
    parent_title: Optional[str] = None
    parent_id: Optional[str] = None
    x_position: Optional[float] = None

@dataclass
class ExtractedSection:
    """A section extracted from the PDF"""
    id: str
    title: str
    content: str
    start_page: int
    end_page: int
    printed_page: int
    chars: int
    hierarchy_level: int
    level_name: str
    parent_title: Optional[str] = None
    file_path: Optional[Path] = None

@dataclass
class ExtractionResult:
    """Complete result of PDF extraction"""
    sections: List[ExtractedSection]
    toc_entries: List[TOCEntry]
    total_pages: int
    toc_start_page: int
    toc_end_page: int
    page_offset: int
    hierarchy_type: str  # "positioning" or "keyword"

@dataclass
class LLMInterface:
    """LLM-friendly interface files"""
    compact_toc: str
    selection_guide: str
    file_mapping: Dict[str, Dict[str, Any]]
    instructions: str

@dataclass
class ExtractionConfig:
    """Configuration for PDF extraction"""
    overlap_pages: int = 1
    max_scan_pages: int = 25
    output_dir: Optional[Path] = None
    create_llm_interface: bool = True
    save_sections: bool = True