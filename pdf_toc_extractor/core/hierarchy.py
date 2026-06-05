"""
Hierarchy detection for TOC entries.
"""

from typing import List, Tuple
from ..types import TOCEntry

def detect_hierarchy_from_positioning(entries_with_positions: List[Tuple[str, int, float]]) -> List[TOCEntry]:
    """
    Detect hierarchy levels based on X-positions.

    Args:
        entries_with_positions: List of (title, page, x_position) tuples

    Returns:
        List of TOCEntry objects with hierarchy information
    """
    if not entries_with_positions:
        return []

    # Group by X position (rounded to nearest 5 points for consistency)
    x_positions = {}
    for title, page, x_pos in entries_with_positions:
        x = round(x_pos / 5) * 5
        if x not in x_positions:
            x_positions[x] = []
        x_positions[x].append((title, page, x_pos))

    # Sort X positions to determine hierarchy levels
    sorted_x = sorted(x_positions.keys())

    # Build hierarchical entries
    hierarchical_entries = []
    current_parent = None

    for title, page, x_pos in entries_with_positions:
        x = round(x_pos / 5) * 5
        level = sorted_x.index(x) if x in sorted_x else 0

        entry = TOCEntry(
            title=title,
            page=page,
            level=level,
            level_name=f'level_{level}',
            parent_title=None,
            parent_id=None,
            x_position=x_pos
        )

        if level == 0:
            # This is a parent entry
            entry.level_name = 'parent'
            current_parent = entry
        else:
            # This is a child entry
            entry.level_name = 'child'
            entry.parent_title = current_parent.title if current_parent else None

        hierarchical_entries.append(entry)

    return hierarchical_entries

def detect_hierarchy_from_keywords(toc_entries: List[Tuple[str, int]]) -> List[TOCEntry]:
    """
    Detect hierarchy based on keywords (PART, SECTION, etc.).

    Args:
        toc_entries: List of (title, page) tuples

    Returns:
        List of TOCEntry objects with hierarchy information
    """
    hierarchical_entries = []
    current_part = None
    current_section = None

    for title, page in toc_entries:
        entry = TOCEntry(
            title=title,
            page=page,
            level=0,
            level_name='unknown',
            parent_title=None,
            parent_id=None
        )

        title_upper = title.upper()

        if title_upper.startswith('PART '):
            entry.level = 0
            entry.level_name = 'part'
            current_part = entry
            current_section = None

        elif title_upper.startswith('SECTION '):
            entry.level = 1
            entry.level_name = 'section'
            entry.parent_title = current_part.title if current_part else None
            current_section = entry

        elif title_upper.startswith(('SERVICE AREA', 'COMBINED EVIDENCE')) and not current_section:
            # These are top-level entries only if not under a section
            entry.level = 0
            entry.level_name = 'special'
            current_part = entry
            current_section = None

        else:
            # Regular item - belongs to current section or part
            if current_section:
                entry.level = 2
                entry.level_name = 'item'
                entry.parent_title = current_section.title
            elif current_part:
                entry.level = 1
                entry.level_name = 'item'
                entry.parent_title = current_part.title
            else:
                entry.level = 0
                entry.level_name = 'orphan'

        hierarchical_entries.append(entry)

    return hierarchical_entries

def has_meaningful_positioning_hierarchy(entries: List[TOCEntry]) -> bool:
    """
    Check if positioning-based hierarchy detection found meaningful hierarchy.

    Args:
        entries: List of TOCEntry objects

    Returns:
        True if meaningful hierarchy was detected
    """
    if not entries:
        return False

    # Count unique levels
    unique_levels = len(set(entry.level for entry in entries))

    # Consider it meaningful if we have more than 1 level
    # and at least some parent-child relationships
    return unique_levels > 1 and any(entry.parent_title for entry in entries)

def assign_section_ids(entries: List[TOCEntry]) -> List[TOCEntry]:
    """
    Assign sequential IDs to sections.

    Args:
        entries: List of TOCEntry objects

    Returns:
        List of TOCEntry objects with IDs assigned
    """
    for i, entry in enumerate(entries, 1):
        entry.parent_id = str(i)

    return entries