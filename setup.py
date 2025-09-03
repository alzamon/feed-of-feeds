from setuptools import setup, find_packages
import sys

# Specify runtime dependencies
runtime_requires = [
    "feedparser>=6.0.0,<7.0.0",
    "pyyaml>=6.0,<7.0",
    "requests>=2.20.0,<3.0.0",
    "argcomplete>=3.0.0",     # For tab completion
    "colorama>=0.4.0,<1.0.0"  # For colored terminal output
]

# Specify development/test dependencies
test_requires = [
    "pytest>=7.0.0,<9.0.0",
]

# Optional/curses dependencies for Windows
extras_require = {}

if sys.platform == "win32":
    extras_require["curses"] = ["windows-curses"]

# Group extras for test, dev, and completion
extras_require["test"] = test_requires
extras_require["dev"] = runtime_requires + test_requires
extras_require["completion"] = ["argcomplete>=3.0.0"]

# Read the long description from README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fof",
    version="0.1.0",
    packages=find_packages(),
    install_requires=runtime_requires,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "fof=fof.cli:main",
        ],
    },
    author="alzamon",
    description="""Feed of Feeds - A hierarchical feed reader with weighted
                   sampling""",
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
