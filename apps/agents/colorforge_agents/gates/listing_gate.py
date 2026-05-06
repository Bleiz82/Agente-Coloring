"""Listing Gate — validates ListingContract before KDP submission."""

from __future__ import annotations

import re

from colorforge_agents.contracts.listing import ListingContract
from colorforge_agents.exceptions import ListingGateBlocked

# ---------------------------------------------------------------------------
# Trademark blocklist (hardcoded for M5; M6 will add DB-backed operator editing)
# ---------------------------------------------------------------------------
_TRADEMARK_TERMS: frozenset[str] = frozenset(
    {
        "disney",
        "marvel",
        "dc comics",
        "pokemon",
        "pikachu",
        "harry potter",
        "star wars",
        "minecraft",
        "roblox",
        "fortnite",
        "peppa pig",
        "paw patrol",
        "bluey",
        "cocomelon",
        "hello kitty",
        "barbie",
        "batman",
        "superman",
        "spiderman",
        "spider-man",
        "frozen",
        "moana",
        "encanto",
        "lilo",
        "winnie the pooh",
        "snoopy",
        "garfield",
        "looney tunes",
        "sesame street",
        "dora the explorer",
        "thomas the tank",
        "nintendo",
        "playstation",
        "xbox",
        "coca-cola",
        "adidas",
        "nike",
        "gucci",
        "louis vuitton",
        "chanel",
        "mickey mouse",
        "minnie mouse",
        "stitch",
    }
)

# Bestseller / superlative claim patterns (case-insensitive)
_CLAIM_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"#\s*1\s+best", re.IGNORECASE),
    re.compile(r"number\s+one\s+best", re.IGNORECASE),
    re.compile(r"best[\s-]?sell(ing|er)", re.IGNORECASE),
    re.compile(r"amazon'?s?\s+choice", re.IGNORECASE),
    re.compile(r"top\s+sell(ing|er)", re.IGNORECASE),
    re.compile(r"most\s+popular", re.IGNORECASE),
    re.compile(r"award[\s-]?winning", re.IGNORECASE),
    re.compile(r"#1\s+rated", re.IGNORECASE),
]

# BISAC code format: 3 uppercase letters + 6 digits (e.g. ART015000)
_BISAC_RE = re.compile(r"^[A-Z]{3}\d{6}$")

_MIN_PRICE_USD = 2.99
_MAX_PRICE_USD = 24.99
_MAX_KEYWORD_LEN = 50


class ListingGate:
    """Validates a ListingContract before KDP submission.

    Raises ListingGateBlocked if any check fails.
    Returns (True, []) on success.
    """

    def passes(self, listing: ListingContract) -> tuple[bool, list[str]]:
        failed: list[str] = []
        failed.extend(self._check_trademarks(listing))
        failed.extend(self._check_bestseller_claims(listing))
        failed.extend(self._check_lengths(listing))
        failed.extend(self._check_bisac(listing))
        failed.extend(self._check_price(listing))
        failed.extend(self._check_keywords(listing))

        if failed:
            raise ListingGateBlocked(book_id=listing.book_id, failed_checks=failed)
        return True, []

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_trademarks(self, listing: ListingContract) -> list[str]:
        issues: list[str] = []
        fields = {
            "title": listing.title,
            "subtitle": listing.subtitle or "",
            "description": listing.description_html,
        }
        keyword_text = " ".join(listing.keywords)

        for field_name, text in fields.items():
            lower = text.lower()
            for term in _TRADEMARK_TERMS:
                if term in lower:
                    issues.append(f"trademark term '{term}' in {field_name}")

        lower_kw = keyword_text.lower()
        for term in _TRADEMARK_TERMS:
            if term in lower_kw:
                issues.append(f"trademark term '{term}' in keywords")

        return issues

    def _check_bestseller_claims(self, listing: ListingContract) -> list[str]:
        issues: list[str] = []
        text = f"{listing.title} {listing.subtitle or ''} {listing.description_html}"
        for pattern in _CLAIM_PATTERNS:
            if pattern.search(text):
                issues.append(f"bestseller claim matched: {pattern.pattern!r}")
        return issues

    def _check_lengths(self, listing: ListingContract) -> list[str]:
        issues: list[str] = []
        if len(listing.title) > 200:
            issues.append(f"title too long: {len(listing.title)} chars (max 200)")
        if listing.subtitle and len(listing.subtitle) > 200:
            issues.append(f"subtitle too long: {len(listing.subtitle)} chars (max 200)")
        if len(listing.description_html) > 4000:
            issues.append(
                f"description too long: {len(listing.description_html)} chars (max 4000)"
            )
        return issues

    def _check_bisac(self, listing: ListingContract) -> list[str]:
        issues: list[str] = []
        if not listing.bisac_codes:
            issues.append("bisac_codes is empty (at least 1 required)")
        for code in listing.bisac_codes:
            if not _BISAC_RE.match(code):
                issues.append(f"invalid BISAC code format: {code!r}")
        return issues

    def _check_price(self, listing: ListingContract) -> list[str]:
        issues: list[str] = []
        if listing.price_usd < _MIN_PRICE_USD:
            issues.append(
                f"price_usd ${listing.price_usd:.2f} below minimum ${_MIN_PRICE_USD:.2f}"
            )
        if listing.price_usd > _MAX_PRICE_USD:
            issues.append(
                f"price_usd ${listing.price_usd:.2f} above maximum ${_MAX_PRICE_USD:.2f}"
            )
        return issues

    def _check_keywords(self, listing: ListingContract) -> list[str]:
        issues: list[str] = []
        for i, kw in enumerate(listing.keywords):
            if len(kw) > _MAX_KEYWORD_LEN:
                issues.append(f"keyword[{i}] too long: {len(kw)} chars (max {_MAX_KEYWORD_LEN})")
        lower_kws = [kw.lower() for kw in listing.keywords]
        if len(lower_kws) != len(set(lower_kws)):
            issues.append("duplicate keywords detected")
        return issues
