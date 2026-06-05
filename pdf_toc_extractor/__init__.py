"""
PDF TOC Extractor - A library for extracting Table of Contents and sections from PDFs.

Main features:
- Table of contents extraction (keyword-based or position-based hierarchies)
- Automatic page offset detection
- Hierarchy detection
- Section boundary calculation with overlap handling
- Compact, token-efficient LLM interface generation

Basic usage:
    from pdf_toc_extractor import extract_pdf_sections, create_llm_interface

    # Extract sections from PDF
    result = extract_pdf_sections("document.pdf", output_dir="output/")

    # Create LLM interface
    llm_interface = create_llm_interface(result.sections)
"""

from .core.extractor import extract_pdf_toc, PDFTOCExtractor
from .llm.interface import generate_llm_interface
from .types import ExtractionConfig, ExtractionResult, LLMInterface, ExtractedSection, TOCEntry
from pathlib import Path
from typing import Optional
import json

def extract_pdf_sections(pdf_path: str, output_dir: Optional[str] = None,
                        overlap_pages: int = 2, create_llm_files: bool = True) -> ExtractionResult:
    """
    Extract sections from a PDF with TOC.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Output directory (default: same as PDF name)
        overlap_pages: Number of overlap pages between sections
        create_llm_files: Whether to create LLM interface files

    Returns:
        ExtractionResult with all extracted data

    Example:
        result = extract_pdf_sections("document.pdf", "output/")
        print(f"Extracted {len(result.sections)} sections")
    """
    pdf_path = Path(pdf_path)

    if output_dir is None:
        output_dir = pdf_path.stem + "_extracted"

    output_path = Path(output_dir)

    config = ExtractionConfig(
        overlap_pages=overlap_pages,
        output_dir=output_path,
        create_llm_interface=create_llm_files,
        save_sections=True
    )

    result = extract_pdf_toc(pdf_path, config)

    if create_llm_files:
        # Generate and save LLM interface files
        llm_interface = generate_llm_interface(result.sections)
        save_llm_interface(llm_interface, output_path)

    return result

def create_llm_interface(sections, save_to: Optional[str] = None) -> LLMInterface:
    """
    Create LLM-friendly interface from extracted sections.

    Args:
        sections: List of ExtractedSection objects or path to JSONL file
        save_to: Optional directory to save interface files

    Returns:
        LLMInterface object with generated content

    Example:
        interface = create_llm_interface(result.sections, "llm_output/")
        print(f"Compact TOC: {len(interface.compact_toc)} chars")
    """
    # Handle both section objects and JSONL file path
    if isinstance(sections, (str, Path)):
        sections = load_sections_from_jsonl(sections)

    llm_interface = generate_llm_interface(sections)

    if save_to:
        save_llm_interface(llm_interface, Path(save_to))

    return llm_interface

def load_sections_from_jsonl(jsonl_path: str) -> list:
    """Load sections from a JSONL file."""
    sections = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line.strip())
            section = ExtractedSection(
                id=str(data['id']),
                title=data['title'],
                content="",  # Content not stored in JSONL
                start_page=data['start_page'],
                end_page=data['end_page'],
                printed_page=data['printed_page'],
                chars=data['chars'],
                hierarchy_level=data['hierarchy_level'],
                level_name=data['level_name'],
                parent_title=data.get('parent_title'),
                file_path=Path(data['file']) if 'file' in data else None
            )
            sections.append(section)
    return sections

def save_llm_interface(interface: LLMInterface, output_dir: Path) -> None:
    """Save LLM interface files to directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save interface files
    (output_dir / "toc_selection.txt").write_text(interface.selection_guide, encoding='utf-8')
    (output_dir / "toc_compact.txt").write_text(interface.compact_toc, encoding='utf-8')
    (output_dir / "file_mapping.json").write_text(
        json.dumps(interface.file_mapping, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    (output_dir / "LLM_INSTRUCTIONS.txt").write_text(interface.instructions, encoding='utf-8')

    print(f"LLM interface files saved to {output_dir}")

# Version info
__version__ = "1.0.0"
__author__ = "Auto-TOC Team"

# Main exports
__all__ = [
    'extract_pdf_sections',
    'create_llm_interface',
    'PDFTOCExtractor',
    'ExtractionConfig',
    'ExtractionResult',
    'LLMInterface',
    'ExtractedSection',
    'TOCEntry'
]