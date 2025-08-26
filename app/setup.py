#!/usr/bin/env python3
"""Setup script for MaterialsCodeGraph-lite"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="materialscodegraph-lite",
    version="1.0.0",
    author="MaterialsCodeGraph Contributors",
    author_email="mcg@example.com",
    description="Minimal MCP implementation for materials science workflows with full lineage tracking",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/materialscodegraph/materialscodegraph",
    project_urls={
        "Bug Reports": "https://github.com/materialscodegraph/materialscodegraph/issues",
        "Documentation": "https://github.com/materialscodegraph/materialscodegraph/wiki",
        "Source": "https://github.com/materialscodegraph/materialscodegraph",
        "Discussions": "https://github.com/materialscodegraph/materialscodegraph/discussions",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.991",
        ],
        "production": [
            "lammps-python>=2023.8.15",
            "ase>=3.22.0",
            "pymatgen>=2023.7.20",
            "psycopg2-binary>=2.9.0",  # PostgreSQL backend
        ],
        "docs": [
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "myst-parser>=0.18.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "mcg=cli.mcg:main",
            "mcg-interfaces=interfaces_mcp.server:main",
            "mcg-compute=compute_mcp.server:main", 
            "mcg-memory=memory_mcp.server:main",
        ],
    },
    include_package_data=True,
    package_data={
        "examples": ["*.py"],
        "tests": ["*.py"],
        "": ["*.md", "*.txt", "*.yml", "*.yaml"],
    },
    keywords="materials science, thermal conductivity, lineage, provenance, MCP, LAMMPS, kALDo",
    zip_safe=False,
)