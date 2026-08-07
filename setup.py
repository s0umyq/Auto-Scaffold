#!/usr/bin/env python3
"""Setup script for Auto-Scaffold CLI."""
from setuptools import setup, find_packages
import os

# Collect static files for auto_scaffold.gui
gui_files = []
gui_dir = "src/auto_scaffold/gui"
for root, dirs, files in os.walk(gui_dir):
    for f in files:
        if f.endswith(('.html', '.css', '.js')):
            rel_root = os.path.relpath(root, "src")
            gui_files.append(os.path.join(rel_root, f))

print(f"GUI files to include: {gui_files}")

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="auto-scaffold-cli",
    version="0.1.0",
    description="AI agent CLI tool for automatic test generation and fix proposals",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Soumya Sandeep Mishra, Swayam Krishna Sahu, Gourav Laxmi Sahoo, Lokesh Kumar Sahu",
    author_email="srm84762@gmail.com, swayamkrishnasahu@gmail.com, sahoogouravlaxmi@gmail.com, kumarlokeshsahu42@gmail.com",
    license="MIT",
    url="https://github.com/auto-scaffold/auto-scaffold",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    package_data={
        "auto_scaffold.gui": ["*.html", "*.css", "*.js"],
    },
    install_requires=[
        "click>=8.1.0",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
        "httpx>=0.25.0",
        "pyyaml>=6.0.0",
        "tree-sitter>=0.20.0",
        "tree-sitter-python>=0.20.0",
        "tree-sitter-javascript>=0.20.0",
        "tree-sitter-typescript>=0.20.0",
        "tree-sitter-go>=0.20.0",
        "tree-sitter-rust>=0.20.0",
        "esprima>=4.0.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "websockets>=11.0.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-mock>=3.11.0",
            "pytest-asyncio>=0.21.0",
            "ruff>=0.1.0",
            "mypy>=1.4.0",
            "black>=23.0.0",
            "pre-commit>=3.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "auto-scaffold = auto_scaffold.cli:cli",
        ],
    },
)