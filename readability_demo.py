#!/usr/bin/env python3
"""
Demonstration of readability issues found in the Feed of Feeds codebase.

This script shows specific examples of hard-to-read code patterns found during
the analysis, along with improved versions for comparison.
"""

import re
from typing import List, Optional


def demonstrate_readability_issues():
    """Show concrete examples of readability problems and solutions."""
    
    print("=== Feed of Feeds (FoF) Readability Issues Demo ===\n")
    
    # Issue 1: Multi-line f-string formatting from control_loop.py (lines 20-24)
    print("1. PROBLEMATIC MULTI-LINE F-STRING FORMATTING:")
    print("   From: fof/control_loop.py lines 20-24")
    print("   Problem: F-strings broken across lines in confusing way\n")
    
    # Simulate the problematic pattern
    class MockArticle:
        def __init__(self):
            self.title = "Example Article Title"
            self.link = "https://example.com/article"
            self.author = "John Doe"
            self.published_date = "2024-01-15"
    
    current_article = MockArticle()
    
    print("   BEFORE (Confusing):")
    print("   ```python")
    print("   lines = [")
    print("       f\"Title: {")
    print("           self.current_article.title}\", f\"Link: {")
    print("           self.current_article.link}\", f\"Author: {")
    print("           self.current_article.author or 'Unknown'}\", f\"Published: {")
    print("           self.current_article.published_date or 'Unknown date'}\", ]")
    print("   ```\n")
    
    print("   AFTER (Clear):")
    print("   ```python")
    print("   lines = [")
    print("       f\"Title: {self.current_article.title}\",")
    print("       f\"Link: {self.current_article.link}\",")
    print("       f\"Author: {self.current_article.author or 'Unknown'}\",")
    print("       f\"Published: {self.current_article.published_date or 'Unknown date'}\",")
    print("   ]")
    print("   ```\n")
    
    # Issue 2: Nested functions in config_comparator.py
    print("2. NESTED FUNCTION DEFINITIONS:")
    print("   From: fof/config_comparator.py")
    print("   Problem: Functions defined inside methods make code hard to follow\n")
    
    print("   BEFORE (Nested):")
    print("   ```python")
    print("   def identify_changed_feeds(self, root_feed, old_dir, new_dir):")
    print("       def collect_feeds_with_paths(feed, current_path=\"\"):")
    print("           # 35+ lines of complex logic here")
    print("           pass")
    print("       ")
    print("       def configs_equal(old_path, new_path):")
    print("           # More nested logic here")
    print("           pass")
    print("       ")
    print("       # Main logic using nested functions")
    print("   ```\n")
    
    print("   AFTER (Extracted):")
    print("   ```python")
    print("   def _collect_feeds_with_paths(self, feed, current_path=\"\"):")
    print("       # Clear method with single responsibility")
    print("       pass")
    print("   ")
    print("   def _configs_equal(self, old_path, new_path):")
    print("       # Clear method with single responsibility")
    print("       pass")
    print("   ")
    print("   def identify_changed_feeds(self, root_feed, old_dir, new_dir):")
    print("       feeds_with_paths = self._collect_feeds_with_paths(root_feed)")
    print("       # Main logic is now clear and readable")
    print("   ```\n")
    
    # Issue 3: Duck typing vs polymorphism
    print("3. DUCK TYPING VS POLYMORPHISM:")
    print("   From: fof/feed_manager.py lines 213-232")
    print("   Problem: hasattr checks instead of proper polymorphism\n")
    
    print("   BEFORE (Duck typing):")
    print("   ```python")
    print("   if hasattr(base_feed, \"weight\") and hasattr(base_feed, \"feed\"):")
    print("       # WeightedFeed handling")
    print("   elif hasattr(base_feed, \"feeds\"):")
    print("       # UnionFeed handling")
    print("   elif hasattr(base_feed, \"source_feed\"):")
    print("       # FilterFeed handling")
    print("   ```\n")
    
    print("   AFTER (Visitor pattern):")
    print("   ```python")
    print("   class FeedVisitor:")
    print("       def visit_weighted_feed(self, feed): pass")
    print("       def visit_union_feed(self, feed): pass") 
    print("       def visit_filter_feed(self, feed): pass")
    print("   ")
    print("   # Each feed type implements:")
    print("   def accept(self, visitor):")
    print("       visitor.visit_union_feed(self)  # Or appropriate type")
    print("   ```\n")
    
    # Issue 4: Large method example
    print("4. LARGE METHOD ISSUE:")
    print("   From: fof/control_loop.py _handle_key_input method")
    print("   Problem: 185+ lines in a single method\n")
    
    print("   BEFORE (Monolithic):")
    print("   ```python")
    print("   def _handle_key_input(self, stdscr):")
    print("       # Setup code...")
    print("       while True:")
    print("           key = stdscr.getch()")
    print("           if key == ord('n'):")
    print("               # 50+ lines of 'next' logic")
    print("           elif key == ord('p'):")
    print("               # 40+ lines of 'previous' logic")
    print("           elif key == ord('o'):")
    print("               # 30+ lines of 'open' logic")
    print("           # ... more key handlers")
    print("   ```\n")
    
    print("   AFTER (Extracted methods):")
    print("   ```python")
    print("   def _handle_key_input(self, stdscr):")
    print("       # Setup code...")
    print("       key_handlers = {")
    print("           ord('n'): self._handle_next_article,")
    print("           ord('p'): self._handle_previous_article,")
    print("           ord('o'): self._handle_open_link,")
    print("       }")
    print("       ")
    print("       while True:")
    print("           key = stdscr.getch()")
    print("           handler = key_handlers.get(key)")
    print("           if handler:")
    print("               handler(stdscr)")
    print("   ```\n")
    
    # Issue 5: Line length violations
    print("5. LINE LENGTH VIOLATIONS:")
    print("   From: Multiple files, over 79 characters")
    print("   Problem: Long lines hurt readability\n")
    
    print("   Examples found by flake8:")
    examples = [
        "max_y - 2, 0, \"Moved to previous read article.\".ljust(max_x))",
        "if most_recent and self.current_article and most_recent.id == self.current_article.id:",
        "\"Increased weights along feedpath and saved configuration.\".ljust(max_x))"
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"   {i}. {example} ({len(example)} chars)")
    
    print("\n   Fix: Break long lines appropriately:")
    print("   ```python")
    print("   # Long conditional")
    print("   if (most_recent and self.current_article and")
    print("           most_recent.id == self.current_article.id):")
    print("   ")
    print("   # Long string")
    print("   message = (\"Increased weights along feedpath and \"")
    print("             \"saved configuration.\")")
    print("   stdscr.addstr(max_y - 3, 0, message.ljust(max_x))")
    print("   ```\n")


def show_metrics():
    """Display the readability metrics found."""
    print("=== READABILITY METRICS ===\n")
    
    files_analyzed = [
        ("article_manager.py", 377, "Large class, mixed concerns, database coupling"),
        ("feed_manager.py", 328, "God class, duck typing, complex traversal"),
        ("cli.py", 281, "Mixed concerns, complex argument handling"),
        ("control_loop.py", 276, "Massive method, deep nesting, formatting issues"),
        ("config_comparator.py", 158, "Nested functions, complex recursive logic"),
    ]
    
    print("Files with significant readability issues:")
    print("File".ljust(25) + "Lines".ljust(8) + "Primary Issues")
    print("-" * 80)
    
    for filename, lines, issues in files_analyzed:
        print(f"{filename:<25} {lines:<8} {issues}")
    
    total_lines = sum(lines for _, lines, _ in files_analyzed)
    print(f"\nTotal lines analyzed: {total_lines}")
    print(f"Files with issues: {len(files_analyzed)}")
    print("Most critical: control_loop.py _handle_key_input method (185+ lines)")


if __name__ == "__main__":
    demonstrate_readability_issues()
    print("\n" + "=" * 60 + "\n")
    show_metrics()
    print("\nFor complete analysis, see READABILITY_ANALYSIS.md")