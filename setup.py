from setuptools import setup, find_packages

setup(
    name="fof",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "feedparser>=6.0.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "fof=fof.cli:main",
        ],
    },
    author="alzamon",
    description="Feed of Feeds - A hierarchical feed reader with weighted sampling",
    keywords="rss, atom, feed, reader",
    python_requires=">=3.7",
)
