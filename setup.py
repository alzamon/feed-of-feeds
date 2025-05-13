from setuptools import setup, find_packages
import sys

# Conditional dependency for Windows
extras_require = {"curses": ["windows-curses"]} if sys.platform == "win32" else {}

# Read the long description from README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fof",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "feedparser>=6.0.0,<7.0.0",
        "pyyaml>=6.0,<7.0",
        "requests>=2.20.0,<3.0.0",  # Added requests dependency
    ],
    extras_require=extras_require,  # Conditional curses dependency for Windows
    entry_points={
        "console_scripts": [
            "fof=fof.cli:main",
        ],
    },
    author="alzamon",
    description="Feed of Feeds - A hierarchical feed reader with weighted sampling",
    long_description=long_description,  # Added long description
    long_description_content_type="text/markdown",  # Markdown content type
    keywords="rss, atom, feed, reader",
    python_requires=">=3.7",
    classifiers=[  # Added classifiers for clarity
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
