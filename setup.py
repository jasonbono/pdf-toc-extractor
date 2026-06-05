#!/usr/bin/env python3
"""
Setup script for PDF TOC Extractor library.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="pdf-toc-extractor",
    version="1.0.0",
    author="Jason Bono",
    author_email="jason.s.bono@gmail.com",
    description="PDF table of contents and section extraction with LLM-friendly interfaces",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jasonbono/pdf-toc-extractor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Text Processing :: Indexing",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "pdf-toc-extractor=pdf_toc_extractor.cli:main",
        ],
    },
    keywords="pdf toc extraction llm ai table-of-contents document-processing",
    project_urls={
        "Bug Reports": "https://github.com/jasonbono/pdf-toc-extractor/issues",
        "Source": "https://github.com/jasonbono/pdf-toc-extractor",
        "Documentation": "https://github.com/jasonbono/pdf-toc-extractor/blob/main/README.md",
    },
    include_package_data=True,
    zip_safe=False,
)