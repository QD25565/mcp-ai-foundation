#!/usr/bin/env python3
"""
Setup script for MCP AI Foundation
"""

from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="mcp-ai-foundation",
    version="1.0.0",
    author="Claude Opus 4.1 & QD25565",
    description="Production-ready MCP tools for AI assistants",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/QD25565/mcp-ai-foundation",
    project_urls={
        "Bug Tracker": "https://github.com/QD25565/mcp-ai-foundation/issues",
        "Source": "https://github.com/QD25565/mcp-ai-foundation",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "notebook-mcp=src.notebook_mcp:main",
            "task-manager-mcp=src.task_manager_mcp:main",
            "teambook-mcp=src.teambook_mcp:main",
            "world-mcp=src.world_mcp:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)