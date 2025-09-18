#!/usr/bin/env python3
"""
Setup script for MCP AI Foundation.
For PyPI packaging when ready.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="mcp-ai-foundation",
    version="1.0.0",
    author="QD25565",
    author_email="162400468+QD25565@users.noreply.github.com",
    description="Essential MCP tools giving AIs memory, temporal grounding, and task accountability",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/QD25565/mcp-ai-foundation",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "notebook-mcp=notebook_mcp:main",
            "world-mcp=world_mcp:main",
            "task-manager-mcp=task_manager_mcp:main",
        ],
    },
)