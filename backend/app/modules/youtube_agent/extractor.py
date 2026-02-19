"""Extract trading ideas and technical analysis concepts from transcript text."""

import re
from typing import List

from app.modules.youtube_agent.config import IDEA_KEYWORDS_NORM, CONCEPT_KEYWORDS_NORM


def extract_ideas_and_concepts(text: str) -> dict:
    """
    Extract trading ideas and technical concepts from transcript text.
    Returns {"ideas": [...], "concepts": [...]} with unique, lowercased matches.
    """
    if not (text or "").strip():
        return {"ideas": [], "concepts": []}
    lower = text.lower()
    ideas = set()
    concepts = set()
    for kw in IDEA_KEYWORDS_NORM:
        if kw in lower:
            ideas.add(kw)
    for kw in CONCEPT_KEYWORDS_NORM:
        if kw.strip() in lower:
            concepts.add(kw.strip())
    return {
        "ideas": sorted(ideas),
        "concepts": sorted(concepts),
    }


# Common English words that are also tickers; skip word-boundary match to avoid false positives
_SYMBOL_BLOCKLIST = frozenset(
    {
        "I",
        "A",
        "S",
        "IT",
        "WE",
        "SO",
        "NOW",
        "YOU",
        "LOW",
        "HIGH",
        "GO",
        "BE",
        "OR",
        "ALL",
    }
)


def extract_symbols_from_text(text: str, allowed_symbols: List[str]) -> List[str]:
    """
    Find mentioned ticker symbols in text: $SYMBOL (cashtag) always; word-boundary only
    for symbols not in blocklist (to avoid matching 'now', 'you', 'low', etc.).
    Returns list of symbols that appear in text, from allowed_symbols.
    """
    if not text or not allowed_symbols:
        return []
    allowed_set = {s.upper() for s in allowed_symbols if (s or "").strip()}
    if not allowed_set:
        return []
    found = []
    seen = set()
    # $SYMBOL (cashtag) — always count
    for m in re.finditer(r"\$([A-Z]{1,5})\b", text, re.IGNORECASE):
        sym = m.group(1).upper()
        if sym in allowed_set and sym not in seen:
            found.append(sym)
            seen.add(sym)
    # Word-boundary: skip 1–2 letter symbols and blocklisted common words
    for sym in allowed_set:
        if sym in seen:
            continue
        if sym in _SYMBOL_BLOCKLIST or len(sym) <= 2:
            continue
        if re.search(
            r"(?<![A-Z0-9])" + re.escape(sym) + r"(?![A-Z0-9])", text, re.IGNORECASE
        ):
            found.append(sym)
            seen.add(sym)
    return found
