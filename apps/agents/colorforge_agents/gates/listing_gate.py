"""Listing Gate — validates ListingContract before KDP submission."""

from __future__ import annotations

import re

from colorforge_agents.contracts.listing import ListingContract
from colorforge_agents.exceptions import ListingGateBlocked

# ---------------------------------------------------------------------------
# K05: Tiered trademark blocklist (expanded from ~40 to 120+ terms)
# ---------------------------------------------------------------------------

# TIER 1: Dealbreakers — guaranteed KDP rejection, account suspension risk
_TIER_DEALBREAKER: frozenset[str] = frozenset({
    "disney",
    "pixar",
    "marvel",
    "star wars",
    "pokemon",
    "pikachu",
    "harry potter",
    "lego",
    "barbie",
    "hello kitty",
    "peppa pig",
    "bluey",
    "frozen",
    "mickey",
    "minions",
    "paw patrol",
})

# TIER 2: High-risk — protected franchises/characters, almost certain rejection
_TIER_HIGH_RISK: frozenset[str] = frozenset({
    "dc comics",
    "batman",
    "superman",
    "spiderman",
    "spider-man",
    "iron man",
    "wolverine",
    "deadpool",
    "captain america",
    "avengers",
    "x-men",
    "moana",
    "encanto",
    "lilo",
    "stitch",
    "winnie the pooh",
    "snoopy",
    "garfield",
    "looney tunes",
    "sesame street",
    "dora the explorer",
    "thomas the tank",
    "nintendo",
    "mario",
    "zelda",
    "pokemon go",
    "roblox",
    "minecraft",
    "fortnite",
    "among us",
    "cocomelon",
    "minnie mouse",
    "mickey mouse",
    "elsa",
    "anna frozen",
    "olaf",
    "tinkerbell",
    "winx",
    "bratz",
    "transformers",
    "my little pony",
    "care bears",
    "strawberry shortcake",
})

# TIER 3: Medium risk — terms that need brand-name context to be infringing
_TIER_MEDIUM_RISK: frozenset[str] = frozenset({
    "playstation",
    "xbox",
    "coca-cola",
    "adidas",
    "nike",
    "gucci",
    "louis vuitton",
    "chanel",
    "hermès",
    "prada",
    "versace",
    "ferrari",
    "lamborghini",
    "nasa",
    "olympic",
    "olympics",
    "fifa",
    "nfl",
    "nba",
    "mlb",
    "nhl",
    "unicef",
    "red cross",
    "cross red",
    "google",
    "apple",
    "microsoft",
    "meta",
    "facebook",
    "instagram",
    "twitter",
    "tiktok",
    "youtube",
})

# TIER 4: Review required — borderline terms, may be fine with proper context
_TIER_REVIEW_REQUIRED: frozenset[str] = frozenset({
    "anime",
    "manga",
    "chibi",
    "kawaii brand",
    "funko",
    "bandai",
    "hasbro",
    "mattel",
    "fisher-price",
    "playmobil",
    "nerf",
    "polaroid",
    "velcro",
    "kleenex",
    "jell-o",
    "xerox",
    "jacuzzi",
    "dumpster",
    "chapstick",
    "realtor",
    "frisbee",
    "hacky sack",
    "jet ski",
    "ping pong",
    "rollerblade",
    "sharpie",
    "photoshop",
    "powerpoint",
    "post-it",
})

# Public whitelist: terms that are legitimate despite matching a trademark
# (e.g. an author whose real surname is Disney)
_WHITELIST: frozenset[str] = frozenset()

# Map tiers to severity labels for error messages
_TIER_LABELS: dict[str, str] = {
    "dealbreaker": "DEALBREAKER",
    "high_risk": "HIGH_RISK",
    "medium_risk": "MEDIUM_RISK",
    "review_required": "REVIEW_REQUIRED",
}

# Pre-compiled word-boundary patterns for each tier (case-insensitive)
# Word boundaries prevent false positives on substrings (e.g. "batman" in "bats_man")
def _compile_tier(terms: frozenset[str]) -> list[tuple[str, re.Pattern[str]]]:
    return [
        (term, re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE))
        for term in sorted(terms)
    ]


_COMPILED_DEALBREAKER = _compile_tier(_TIER_DEALBREAKER)
_COMPILED_HIGH_RISK = _compile_tier(_TIER_HIGH_RISK)
_COMPILED_MEDIUM_RISK = _compile_tier(_TIER_MEDIUM_RISK)
_COMPILED_REVIEW_REQUIRED = _compile_tier(_TIER_REVIEW_REQUIRED)

# ---------------------------------------------------------------------------
# Bestseller / superlative claim patterns (case-insensitive)
# ---------------------------------------------------------------------------
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
            "keywords": " ".join(listing.keywords),
        }
        tier_data = [
            ("dealbreaker", _COMPILED_DEALBREAKER),
            ("high_risk", _COMPILED_HIGH_RISK),
            ("medium_risk", _COMPILED_MEDIUM_RISK),
            ("review_required", _COMPILED_REVIEW_REQUIRED),
        ]

        for tier_key, compiled in tier_data:
            tier_label = _TIER_LABELS[tier_key]
            for term, pattern in compiled:
                if term in _WHITELIST:
                    continue
                for field_name, text in fields.items():
                    if pattern.search(text):
                        issues.append(
                            f"[{tier_label}] trademark term '{term}' in {field_name}"
                        )
                        break  # one issue per term is enough

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
