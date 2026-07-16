"""Single source of truth for what counts as a verbatim quote.

NORMALIZATION ONLY (whitespace collapse + case fold). Never add fuzzy matching
here: fragments joined by ellipsis, paraphrases, or "close enough" quotes must
FAIL. Fix extraction, never this module.
"""
import re


def normalize(s):
    return re.sub(r"\s+", " ", s.lower()).strip()


def contains(text, quote):
    """True iff `quote` is a contiguous verbatim excerpt of `text` (modulo whitespace/case)."""
    return normalize(quote) in normalize(text)
