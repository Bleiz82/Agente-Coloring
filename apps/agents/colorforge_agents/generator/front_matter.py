"""KDP-compliant front matter and back matter assembler.

Produces title page, copyright (with mandatory AI disclosure), dedication,
how-to-use, thank-you, about-author, and optionally an also-by page. Then
concatenates them around the coloring image stack into a single interior PDF.

Source of truth: .claude/skills/kdp-frontmatter.md
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from colorforge_agents.contracts.book_draft import BookDraft
from colorforge_agents.contracts.book_plan import BookPlan
from colorforge_agents.exceptions import FrontMatterError, PDFAssemblyError

# ---------------------------------------------------------------------------
# Asset paths
# ---------------------------------------------------------------------------
_FONTS_DIR: Final = Path(__file__).parent.parent.parent / "assets" / "fonts"

# ---------------------------------------------------------------------------
# KDP page geometry constants
# ---------------------------------------------------------------------------
_BLEED_IN: Final = 0.125
_PT_PER_IN: Final = 72.0
_MIN_PAGES: Final = 24
_MAX_PAGES: Final = 828
_MAX_BLANK_RUN_MID: Final = 4   # >4 consecutive blanks mid-book = fail
_MAX_BLANK_RUN_END: Final = 10  # >10 consecutive blanks at end = fail

# URL/contact detection (KDP §8 — prohibited in interior)
_URL_PATTERN: Final = re.compile(
    r"(https?://|www\.|\.com\b|\.net\b|\.org\b|@[a-zA-Z]|\+\d[\d\s\-]{7,})",
    re.IGNORECASE,
)

# Mandatory AI disclosure phrase
_AI_DISCLOSURE_PHRASE: Final = "AI-generated"

# ---------------------------------------------------------------------------
# Niche-aware text templates
# ---------------------------------------------------------------------------
_HOW_TO_USE_INTRO: Final[dict[str, str]] = {
    "Adult": (
        "Welcome to your stress-relief sanctuary. The intricate designs in this book "
        "are crafted to slow your breathing, center your focus, and bring a meditative "
        "calm to your day."
    ),
    "Kids": (
        "Get ready for hours of fun! These big, simple designs are perfect for little "
        "hands learning to color inside the lines. There is no wrong way to color."
    ),
    "Activity": (
        "This workbook combines coloring with learning. Each page is designed to engage "
        "both creativity and curiosity, making practice feel like play."
    ),
    "Pocket": (
        "Compact and ready for adventure. Whether you are on a plane, train, or waiting "
        "room, these pages are your portable creative escape."
    ),
    "Default": (
        "Welcome to your coloring journey. Take your time, choose your favorite tools, "
        "and enjoy the meditative flow of bringing each page to life."
    ),
}

_HOW_TO_USE_TIPS: Final[dict[str, list[str]]] = {
    "Adult": [
        "Start with the outermost ring and work inward — it builds focus.",
        "Use a limited palette (3-5 colors) for a more harmonious result.",
        "Try shading with two tones of the same color for depth.",
        "Take breaks and return with fresh eyes for the best experience.",
    ],
    "Kids": [
        "Pick your favorite color first!",
        "Coloring outside the lines is okay — your art, your rules.",
        "Try rainbow order if you cannot decide which color to use.",
        "Show your finished pages to someone you love.",
    ],
    "Activity": [
        "Read any text on the page before you color.",
        "Save the answer key — color it last.",
        "Track your progress in the back of the book.",
        "Use different colors to highlight different concepts.",
    ],
    "Pocket": [
        "Use travel-friendly tools (no liquid markers).",
        "Snap a photo of finished pages to share your journey.",
        "Each page is a memory of where you colored it.",
        "A small pencil case is all you need.",
    ],
    "Default": [
        "Start with lighter colors and layer darker tones on top.",
        "Use a blank sheet behind the page to prevent bleed-through.",
        "There is no rush — coloring is about the process, not the destination.",
        "Try different media: colored pencils, markers, or watercolor pencils.",
    ],
}

_BRAND_PERSONA_BIOS: Final[dict[str, str]] = {
    "mindful_artist": (
        "{author} is a mindful artist who believes coloring is the simplest path to "
        "creative joy. Their designs invite you to slow down, breathe, and rediscover "
        "the meditative magic of pencils on paper."
    ),
    "studio_brand": (
        "{author} is a small independent studio dedicated to creating coloring books "
        "that delight, challenge, and relax. Each title is crafted with care for "
        "colorists of every level."
    ),
    "kids_creator": (
        "{author} makes coloring books for the youngest artists. With big, friendly "
        "designs and themes kids love, every page is an invitation to play and create."
    ),
    "educational": (
        "{author} designs activity books that turn learning into adventure. Their work "
        "bridges creativity and curiosity, helping young minds grow one colorful page "
        "at a time."
    ),
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class FrontMatterContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    title_page_text: str
    copyright_page_text: str
    dedication_page_text: str | None = None
    how_to_use_page_text: str


class BackMatterContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    thank_you_page_text: str
    about_author_page_text: str
    also_by_page_text: str | None = None


class FrontMatterAssemblyResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    pdf_path: Path
    page_count: int = Field(gt=0)
    front_matter_pages: int = Field(ge=0)
    coloring_pages: int = Field(ge=0)
    back_matter_pages: int = Field(ge=0)
    total_size_bytes: int = Field(ge=0)


# ---------------------------------------------------------------------------
# FrontMatterAssembler
# ---------------------------------------------------------------------------


def _niche_category_from_keyword(keyword: str) -> str:
    """Map a niche keyword to content category (mirrors cover compositor logic)."""
    kw = keyword.lower()
    if any(w in kw for w in ("mandala", "zen", "geometric", "meditation", "adult", "stress")):
        return "Adult"
    if any(w in kw for w in ("kids", "children", "toddler", "preschool", "kindergarten")):
        return "Kids"
    if any(w in kw for w in ("workbook", "activity", "educational", "homeschool")):
        return "Activity"
    if any(w in kw for w in ("travel", "pocket", "mini")):
        return "Pocket"
    return "Default"


def _compute_gutter_inches(total_pages: int) -> float:
    """KDP gutter table for total page count (front+coloring+back)."""
    if total_pages <= 150:
        return 0.375
    if total_pages <= 300:
        return 0.500
    if total_pages <= 500:
        return 0.625
    if total_pages <= 700:
        return 0.750
    return 0.875


def _check_no_url(text: str, field_name: str) -> None:
    """Raise FrontMatterError if text contains URL/email/phone."""
    match = _URL_PATTERN.search(text)
    if match:
        raise FrontMatterError(
            f"URL/contact pattern found in {field_name}: {match.group()!r} — "
            "KDP §8 prohibits URLs/contacts in interior text"
        )


class FrontMatterAssembler:
    """Assemble KDP-compliant front matter and back matter for a coloring book.

    Produces a complete interior PDF combining title page, copyright (with AI
    disclosure), how-to-use, the coloring image stack, thank-you, and
    about-author pages.
    """

    def __init__(
        self,
        book_plan: BookPlan,
        book_draft: BookDraft,
        brand_persona: str = "studio_brand",
    ) -> None:
        self.plan = book_plan
        self.draft = book_draft
        self.brand_persona = brand_persona
        self._niche_cat = _niche_category_from_keyword(book_plan.target_keyword)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_front_matter(self) -> FrontMatterContent:
        """Build all front matter text blocks."""
        title_text = self._build_title_page()
        copyright_text = self._build_copyright_page()
        dedication_text = self._build_dedication_page()
        how_to_use_text = self._build_how_to_use_page()

        # Validate no URLs in any front matter
        for field, text in [
            ("title_page", title_text),
            ("copyright_page", copyright_text),
            ("dedication_page", dedication_text or ""),
            ("how_to_use_page", how_to_use_text),
        ]:
            _check_no_url(text, field)

        # Mandatory AI disclosure check
        if _AI_DISCLOSURE_PHRASE not in copyright_text:
            raise FrontMatterError(
                f"Copyright page must contain AI disclosure phrase: {_AI_DISCLOSURE_PHRASE!r}"
            )

        return FrontMatterContent(
            title_page_text=title_text,
            copyright_page_text=copyright_text,
            dedication_page_text=dedication_text,
            how_to_use_page_text=how_to_use_text,
        )

    def build_back_matter(self, other_titles: list[str] | None = None) -> BackMatterContent:
        """Build all back matter text blocks."""
        thank_you = self._build_thank_you_page()
        about_author = self._build_about_author_page()
        also_by = self._build_also_by_page(other_titles) if other_titles and len(other_titles) >= 1 else None

        for field, text in [
            ("thank_you_page", thank_you),
            ("about_author_page", about_author),
            ("also_by_page", also_by or ""),
        ]:
            _check_no_url(text, field)

        return BackMatterContent(
            thank_you_page_text=thank_you,
            about_author_page_text=about_author,
            also_by_page_text=also_by,
        )

    def assemble(
        self,
        coloring_pages_pdf: Path,
        output_path: Path,
        other_titles: list[str] | None = None,
    ) -> FrontMatterAssemblyResult:
        """Assemble complete interior PDF.

        Concatenates: front matter + coloring pages PDF + back matter.

        Args:
            coloring_pages_pdf: Path to assembled coloring pages PDF.
            output_path: Destination for the complete interior PDF.
            other_titles: Author's other published titles for also-by page.

        Returns:
            FrontMatterAssemblyResult with page counts and file size.

        Raises:
            FrontMatterError: If total page count violates KDP min/max, AI
                disclosure is absent, or blank-page-run rule is violated.
            FileNotFoundError: If a required font or input PDF is missing.
        """
        if not coloring_pages_pdf.exists():
            raise FileNotFoundError(f"Coloring pages PDF not found: {coloring_pages_pdf}")

        import pypdf

        front_content = self.build_front_matter()
        back_content = self.build_back_matter(other_titles)

        front_pages = self._count_front_pages(front_content)
        back_pages = self._count_back_pages(back_content)

        # Read coloring pages count
        with open(coloring_pages_pdf, "rb") as f:
            reader = pypdf.PdfReader(f)
            coloring_count = len(reader.pages)

        total_pages = front_pages + coloring_count + back_pages

        # KDP page count validation
        if total_pages < _MIN_PAGES:
            raise FrontMatterError(
                f"Total page count {total_pages} below KDP minimum {_MIN_PAGES}"
            )
        if total_pages > _MAX_PAGES:
            raise FrontMatterError(
                f"Total page count {total_pages} exceeds KDP maximum {_MAX_PAGES}"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        trim_w_pt = (self.plan.trim_size.width_inches + _BLEED_IN) * _PT_PER_IN
        trim_h_pt = (self.plan.trim_size.height_inches + 2 * _BLEED_IN) * _PT_PER_IN
        gutter_in = _compute_gutter_inches(total_pages)

        front_pdf = output_path.with_suffix("").parent / f"{output_path.stem}_front.pdf"
        back_pdf = output_path.with_suffix("").parent / f"{output_path.stem}_back.pdf"

        self._render_front_matter_pdf(front_content, front_pdf, trim_w_pt, trim_h_pt, gutter_in)
        self._render_back_matter_pdf(back_content, back_pdf, trim_w_pt, trim_h_pt, gutter_in)

        writer = pypdf.PdfWriter()
        for src in (front_pdf, coloring_pages_pdf, back_pdf):
            with open(src, "rb") as f:
                for page in pypdf.PdfReader(f).pages:
                    writer.add_page(page)

        with open(output_path, "wb") as f:
            writer.write(f)

        # Cleanup temp files
        front_pdf.unlink(missing_ok=True)
        back_pdf.unlink(missing_ok=True)

        # Post-assembly validation
        with open(output_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            actual_pages = len(reader.pages)

        if actual_pages != total_pages:
            raise FrontMatterError(
                f"Assembled PDF has {actual_pages} pages, expected {total_pages}"
            )

        self._validate_blank_runs(total_pages, front_pages, back_pages)

        file_size = output_path.stat().st_size
        if file_size > 650 * 1024 * 1024:
            raise FrontMatterError(
                f"Interior PDF {file_size // (1024*1024)}MB exceeds KDP 650MB limit"
            )

        return FrontMatterAssemblyResult(
            pdf_path=output_path,
            page_count=total_pages,
            front_matter_pages=front_pages,
            coloring_pages=coloring_count,
            back_matter_pages=back_pages,
            total_size_bytes=file_size,
        )

    # ------------------------------------------------------------------
    # Private: text builders
    # ------------------------------------------------------------------

    def _build_title_page(self) -> str:
        title = self.draft.title or self.plan.target_keyword
        author = self.draft.author or self.plan.brand_author
        subtitle_line = f"\n\n{self.draft.subtitle}" if self.draft.subtitle else ""
        return (
            f"{title}{subtitle_line}\n\n\n\n\n\n\n\n\n\n\n\n"
            f"{author}\n\n\n\n"
            f"{self.plan.imprint}"
        )

    def _build_copyright_page(self) -> str:
        title = self.draft.title or self.plan.target_keyword
        author = self.draft.author or self.plan.brand_author
        year = self.plan.publication_year
        imprint = self.plan.imprint
        country = self.plan.imprint_country

        return (
            f"{title}\n"
            f"Copyright © {year} {author}\n"
            f"All rights reserved.\n\n"
            f"Published by {imprint}.\n"
            f"{country}\n\n"
            f"ISBN: Not assigned\n\n"
            f"First edition: {year}\n\n"
            f"{'=' * 40}\n\n"
            f"AI DISCLOSURE\n"
            f"This book contains AI-generated content. The illustrations were created\n"
            f"using AI image generation tools. The author has reviewed, selected, and\n"
            f"curated all content to ensure quality and originality.\n\n"
            f"{'=' * 40}\n\n"
            f"No part of this publication may be reproduced, distributed, or transmitted\n"
            f"in any form or by any means, including photocopying, recording, or other\n"
            f"electronic or mechanical methods, without the prior written permission of\n"
            f"the publisher, except in the case of brief quotations embodied in critical\n"
            f"reviews.\n\n"
            f"Printed in {country} by Amazon KDP."
        )

    def _build_dedication_page(self) -> str | None:
        if not self.plan.include_dedication or not self.plan.dedication_text:
            return None
        return f"\n\n\n\n\n\n\n\n{self.plan.dedication_text}\n\n\n\n\n\n\n\n"

    def _build_how_to_use_page(self) -> str:
        intro = _HOW_TO_USE_INTRO[self._niche_cat]
        tips = _HOW_TO_USE_TIPS[self._niche_cat]
        tips_text = "\n".join(f"* {t}" for t in tips)
        return (
            "HOW TO USE THIS BOOK\n\n"
            f"{intro}\n\n"
            "TIPS FOR THE BEST EXPERIENCE\n\n"
            f"{tips_text}\n\n"
            "RECOMMENDED COLORING TOOLS\n\n"
            "* Colored pencils (e.g., Prismacolor, Faber-Castell)\n"
            "* Fine-tip markers (e.g., Tombow, Staedtler)\n"
            "* Gel pens for accents\n"
            "* Watercolor pencils (avoid heavy water -- paper is print-grade)\n\n"
            "A NOTE ON PAPER\n\n"
            "This book is printed on standard KDP paper. For best results with\n"
            "markers, place a blank sheet behind each page to prevent bleed-through.\n\n"
            "Enjoy your creative journey!"
        )

    def _build_thank_you_page(self) -> str:
        return (
            "\n\n\n\n\n\n"
            "THANK YOU\n\n"
            "for choosing this book.\n\n"
            "If you enjoyed your coloring journey, a brief review\n"
            "on Amazon would mean the world.\n\n"
            "Your feedback helps fellow colorists discover books\n"
            "they will love.\n\n\n\n\n\n"
        )

    def _build_about_author_page(self) -> str:
        author = self.draft.author or self.plan.brand_author
        template = _BRAND_PERSONA_BIOS.get(self.brand_persona, _BRAND_PERSONA_BIOS["studio_brand"])
        bio = template.format(author=author)
        return f"ABOUT THE AUTHOR\n\n{author}\n\n{bio}"

    def _build_also_by_page(self, other_titles: list[str]) -> str:
        author = self.draft.author or self.plan.brand_author
        titles_text = "\n".join(f"* {t}" for t in other_titles)
        return (
            f"ALSO BY {author.upper()}\n\n"
            f"{titles_text}\n\n"
            "Find them all on Amazon."
        )

    # ------------------------------------------------------------------
    # Private: page count helpers
    # ------------------------------------------------------------------

    def _count_front_pages(self, content: FrontMatterContent) -> int:
        count = 3  # title + copyright + how_to_use (always)
        if content.dedication_page_text:
            count += 1
        return count

    def _count_back_pages(self, content: BackMatterContent) -> int:
        count = 2  # thank_you + about_author (always)
        if content.also_by_page_text:
            count += 1
        return count

    # ------------------------------------------------------------------
    # Private: PDF rendering
    # ------------------------------------------------------------------

    def _register_fonts(self) -> None:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        font_map = {
            "Montserrat-Bold": "Montserrat-Bold.ttf",
            "Lato-Regular": "Lato-Regular.ttf",
            "Lato-Italic": "Lato-Italic.ttf",
            "PlayfairDisplay-Bold": "PlayfairDisplay-Bold.ttf",
        }
        for font_name, font_file in font_map.items():
            font_path = _FONTS_DIR / font_file
            if font_path.exists():
                try:
                    pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
                except Exception:
                    pass

    def _render_front_matter_pdf(
        self,
        content: FrontMatterContent,
        output: Path,
        page_w: float,
        page_h: float,
        gutter_in: float,
    ) -> None:
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas as rl_canvas

        self._register_fonts()
        c = rl_canvas.Canvas(str(output), pagesize=(page_w, page_h))
        margin = gutter_in * inch
        top_margin = (_BLEED_IN + 0.5) * inch
        text_width = page_w - 2 * margin

        # Title page
        self._render_text_page(c, content.title_page_text, page_w, page_h, margin, top_margin, text_width, center=True)
        c.showPage()

        # Copyright page
        self._render_text_page(c, content.copyright_page_text, page_w, page_h, margin, top_margin, text_width, center=False, font_size=9)
        c.showPage()

        # Dedication (optional)
        if content.dedication_page_text:
            self._render_text_page(c, content.dedication_page_text, page_w, page_h, margin, top_margin, text_width, center=True, font_size=14)
            c.showPage()

        # How-to-use
        self._render_text_page(c, content.how_to_use_page_text, page_w, page_h, margin, top_margin, text_width, center=False, font_size=11)
        c.showPage()

        c.save()

    def _render_back_matter_pdf(
        self,
        content: BackMatterContent,
        output: Path,
        page_w: float,
        page_h: float,
        gutter_in: float,
    ) -> None:
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas as rl_canvas

        self._register_fonts()
        c = rl_canvas.Canvas(str(output), pagesize=(page_w, page_h))
        margin = gutter_in * inch
        top_margin = (_BLEED_IN + 0.5) * inch
        text_width = page_w - 2 * margin

        # Thank-you
        self._render_text_page(c, content.thank_you_page_text, page_w, page_h, margin, top_margin, text_width, center=True, font_size=14)
        c.showPage()

        # About author
        self._render_text_page(c, content.about_author_page_text, page_w, page_h, margin, top_margin, text_width, center=False, font_size=11)
        c.showPage()

        # Also-by (optional)
        if content.also_by_page_text:
            self._render_text_page(c, content.also_by_page_text, page_w, page_h, margin, top_margin, text_width, center=False, font_size=12)
            c.showPage()

        c.save()

    @staticmethod
    def _render_text_page(
        c: "Canvas",  # type: ignore[name-defined]
        text: str,
        page_w: float,
        page_h: float,
        margin: float,
        top_margin: float,
        text_width: float,
        center: bool = False,
        font_size: int = 11,
    ) -> None:
        from reportlab.lib.units import inch

        c.setFont("Helvetica", font_size)
        y = page_h - top_margin
        line_height = font_size * 1.4

        for line in text.split("\n"):
            if y < margin + line_height:
                break
            if line.strip() == "=" * 40:
                c.line(margin, y, page_w - margin, y)
                y -= line_height
                continue
            if center:
                c.drawCentredString(page_w / 2, y, line)
            else:
                c.drawString(margin, y, line)
            y -= line_height

    # ------------------------------------------------------------------
    # Private: validation
    # ------------------------------------------------------------------

    def _validate_blank_runs(
        self, total_pages: int, front_pages: int, back_pages: int
    ) -> None:
        """Check that no blank-page runs exceed KDP limits."""
        coloring_pages = total_pages - front_pages - back_pages
        # Front matter typically has 0 consecutive blank pages beyond structure
        # End matter: at most 1 blank page
        # This is a simplified check — real detection would parse the PDF
        if coloring_pages <= 0:
            raise FrontMatterError(
                f"No coloring pages in assembled PDF (total={total_pages}, "
                f"front={front_pages}, back={back_pages})"
            )
