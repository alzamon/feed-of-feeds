from setuptools import setup, find_packages
import sys

# Conditional dependency for Windows
extras_require = {
    "curses": ["windows-curses"]
} if sys.platform == "win32" else {}

# Add test/dev dependencies
extras_require.update({
    "dev": ["pytest>=7.0.0,<9.0.0"],
    "test": ["pytest>=7.0.0,<9.0.0"],
})

# Add argcomplete for tab completion
extras_require["completion"] = ["argcomplete>=3.0.0"]

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
        "requests>=2.20.0,<3.0.0",
        "argcomplete>=3.0.0",  # Added here for default install
    ],
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "fof=fof.cli:main",
        ],
    },
    author="alzamon",
    description="Feed of Feeds - A hierarchical feed reader with weighted sampling",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="rss, atom, feed, reader",
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)