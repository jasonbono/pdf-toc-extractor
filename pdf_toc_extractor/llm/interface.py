"""
LLM interface generation for extracted PDF sections.
"""

from typing import List, Dict, Any
from ..types import ExtractedSection, LLMInterface
from ..core.utils import get_section_type, format_section_size


def create_compact_toc(sections: List[ExtractedSection]) -> str:
    """Create a compact, indented table of contents for LLM use."""
    lines = ["TABLE OF CONTENTS", "=" * 40, ""]

    for section in sections:
        indent = "  " * section.hierarchy_level
        title = section.title
        if len(title) > 60:
            title = title[:57] + "..."
        size_info = format_section_size(section.chars)
        lines.append(f"{indent}[{int(section.id):03d}] {title} (p.{section.printed_page}, {size_info})")

    return "\n".join(lines)


def create_selection_guide(sections: List[ExtractedSection]) -> str:
    """Create a selection guide that labels each section by type."""
    lines = [
        "SECTION SELECTION GUIDE",
        "=" * 40,
        "",
        "Each section is labeled by type so you can choose what to load:",
        "  ORG     = organizational, structure or overview",
        "  CONTENT = a focused topic",
        "  LARGE   = a long section you may want to filter",
        "",
    ]

    first_top_level = True
    for section in sections:
        level = section.hierarchy_level
        title = section.title
        section_type = get_section_type(title, level, section.chars)
        size_info = format_section_size(section.chars)

        if level == 0:
            if not first_top_level:
                lines.append("")
            first_top_level = False

        display = title[:55] + "..." if len(title) > 55 else title
        indent = "  " * level
        lines.append(f"{indent}[{int(section.id):03d}] {display} ({size_info}, {section_type})")

    org_count = sum(1 for s in sections if get_section_type(s.title, s.hierarchy_level, s.chars) == "ORG")
    content_count = sum(1 for s in sections if get_section_type(s.title, s.hierarchy_level, s.chars) == "CONTENT")
    large_count = sum(1 for s in sections if get_section_type(s.title, s.hierarchy_level, s.chars) == "LARGE")

    lines.append("")
    lines.append(f"SUMMARY: {content_count} content, {org_count} organizational, {large_count} large")
    lines.append("")
    lines.append("Request sections by id, for example: [001], [023], [045]")

    return "\n".join(lines)


def create_file_mapping(sections: List[ExtractedSection]) -> Dict[str, Dict[str, Any]]:
    """Create a simple id to file mapping for reference."""
    mapping = {}
    for section in sections:
        mapping[section.id] = {
            'file': str(section.file_path.name) if section.file_path else f"{section.id:03d}_{section.title[:20]}.txt",
            'title': section.title,
            'chars': section.chars
        }
    return mapping


def create_instructions(sections: List[ExtractedSection], compact_toc: str, selection_guide: str) -> str:
    """Create usage instructions for the generated interface files."""
    instructions = f"""LLM INTERFACE FOR PDF EXTRACTION
================================

This directory holds the sections extracted from a PDF with a hierarchical
table of contents.

Files:
1. toc_selection.txt - selection guide with a type label per section (start here)
2. toc_compact.txt   - hierarchical table of contents
3. file_mapping.json - section id to filename mapping

Section types:
  CONTENT - a focused topic, usually what you want
  ORG     - organizational, structure or overview, useful for context
  LARGE   - a long section you may want to filter

Workflow:
1. Read toc_selection.txt ({len(selection_guide)} chars).
2. Pick the relevant section ids by topic and type.
3. Request them, for example: analyze sections [001], [023], [045].
4. Load the matching files from the sections/ directory.

Sections: {len(sections)} total.
The compact view is about {len(compact_toc) // 4} tokens, versus the full JSONL metadata.

Example prompts:
"Which CONTENT sections relate to [topic]?"
"Which ORGANIZATIONAL sections give an overview of [area]?"
"Load sections [001], [023], [045]."
"""

    return instructions


def generate_llm_interface(sections: List[ExtractedSection]) -> LLMInterface:
    """
    Generate the complete LLM interface from extracted sections.

    Args:
        sections: List of extracted sections

    Returns:
        LLMInterface object with all generated content
    """
    compact_toc = create_compact_toc(sections)
    selection_guide = create_selection_guide(sections)
    file_mapping = create_file_mapping(sections)
    instructions = create_instructions(sections, compact_toc, selection_guide)

    return LLMInterface(
        compact_toc=compact_toc,
        selection_guide=selection_guide,
        file_mapping=file_mapping,
        instructions=instructions
    )
