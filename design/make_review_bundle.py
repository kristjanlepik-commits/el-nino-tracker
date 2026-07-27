"""Regenerate design/REVIEW_BUNDLE.md.

The visual-language chat can fetch raw file URLs but not GitHub's
directory or compare pages, so it cannot discover files by browsing.
This concatenates everything reviewable into one file it can fetch with
a single request. Run after any change to tokens.py or PUBLIC_CSS.
"""
