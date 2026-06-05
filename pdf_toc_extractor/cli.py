#!/usr/bin/env python3
"""
Command-line interface for PDF TOC Extractor.
"""

import argparse
import sys
from pathlib import Path
from . import extract_pdf_sections, create_llm_interface

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract Table of Contents and sections from PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract sections from PDF
  pdf-toc-extractor document.pdf

  # Extract with custom output directory
  pdf-toc-extractor document.pdf -o output/

  # Extract with 3-page overlap
  pdf-toc-extractor document.pdf --overlap 3

  # Only create LLM interface from existing JSONL
  pdf-toc-extractor --llm-only data/toc_master_complete.jsonl -o llm_output/
        """
    )

    parser.add_argument(
        'input',
        help='Input PDF file or JSONL file (for --llm-only)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output directory (default: INPUT_extracted)'
    )

    parser.add_argument(
        '--overlap',
        type=int,
        default=2,
        help='Number of overlap pages between sections (default: 2)'
    )

    parser.add_argument(
        '--no-llm',
        action='store_true',
        help='Skip LLM interface generation'
    )

    parser.add_argument(
        '--llm-only',
        action='store_true',
        help='Only generate LLM interface from existing JSONL file'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='pdf-toc-extractor 1.0.0'
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found", file=sys.stderr)
        sys.exit(1)

    try:
        if args.llm_only:
            # Generate LLM interface from existing JSONL
            print(f"Creating LLM interface from {input_path}")
            interface = create_llm_interface(str(input_path), args.output)
            print(f"LLM interface created with {len(interface.selection_guide)} chars")

        else:
            # Extract sections from PDF
            print(f"Extracting sections from {input_path}")
            result = extract_pdf_sections(
                str(input_path),
                output_dir=args.output,
                overlap_pages=args.overlap,
                create_llm_files=not args.no_llm
            )

            print(f"Extracted {len(result.sections)} sections")
            print(f"TOC: pages {result.toc_start_page+1}-{result.toc_end_page+1}")

            # Handle page_offset type safely
            try:
                if isinstance(result.page_offset, str):
                    page_offset = int(result.page_offset) if result.page_offset.lstrip('+-').isdigit() else result.page_offset
                else:
                    page_offset = result.page_offset
                print(f"Page offset: {page_offset:+d}" if isinstance(page_offset, int) else f"Page offset: {page_offset}")
            except (ValueError, TypeError):
                print(f"Page offset: {result.page_offset}")

            print(f"Hierarchy: {result.hierarchy_type}")

            if not args.no_llm:
                print("LLM interface created")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
