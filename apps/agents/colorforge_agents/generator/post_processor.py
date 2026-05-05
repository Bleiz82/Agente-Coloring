"""Pillow-based image post-processor: grayscale, contrast, 300 DPI, artifact detection."""

from __future__ import annotations

import io
import random
from dataclasses import dataclass

from colorforge_agents.exceptions import ImageGenerationError

_TARGET_DPI = 300
_PAGE_W_PX = 2550   # 8.5" × 300 DPI
_PAGE_H_PX = 3300   # 11.0" × 300 DPI
_ARTIFACT_PATCH_SIZE = 50
_ARTIFACT_NUM_PATCHES = 10
_ARTIFACT_STD_THRESHOLD = 5.0   # near-solid patch if std-dev < this value
_CONTRAST_LOW = 10
_CONTRAST_HIGH = 245


@dataclass
class ProcessedImage:
    """Result of post-processing a generated page."""

    data: bytes
    artifact_detected: bool
    width_px: int
    height_px: int


class ImagePostProcessor:
    """Convert generated PNG to KDP-compliant grayscale 300-DPI image."""

    def process(self, image_bytes: bytes) -> ProcessedImage:
        """Full pipeline: decode → grayscale → contrast → resize → artifact check → encode."""
        try:
            from PIL import Image, ImageOps  # type: ignore[import]
        except ImportError as exc:
            raise ImageGenerationError("Pillow not installed") from exc

        try:
            img = Image.open(io.BytesIO(image_bytes))
        except Exception as exc:
            raise ImageGenerationError(f"Cannot open image: {exc}") from exc

        img = self._to_grayscale(img)
        img = self._normalize_contrast(img)
        img = self._resize_to_target(img)

        artifact = self._detect_artifacts(img)

        buf = io.BytesIO()
        img.save(buf, format="PNG", dpi=(_TARGET_DPI, _TARGET_DPI))
        return ProcessedImage(
            data=buf.getvalue(),
            artifact_detected=artifact,
            width_px=img.width,
            height_px=img.height,
        )

    def _to_grayscale(self, img: object) -> object:
        from PIL import Image  # type: ignore[import]

        pil_img: Image.Image = img  # type: ignore[assignment]
        if pil_img.mode != "L":
            pil_img = pil_img.convert("L")
        return pil_img

    def _normalize_contrast(self, img: object) -> object:
        from PIL import Image  # type: ignore[import]

        pil_img: Image.Image = img  # type: ignore[assignment]
        # Linear stretch: map current min/max to [_CONTRAST_LOW, _CONTRAST_HIGH]
        import numpy as np

        arr = np.array(pil_img, dtype=np.float32)
        lo, hi = float(arr.min()), float(arr.max())
        if hi - lo < 1.0:
            return pil_img  # already uniform; skip to avoid divide-by-zero
        stretched = (arr - lo) / (hi - lo) * (_CONTRAST_HIGH - _CONTRAST_LOW) + _CONTRAST_LOW
        stretched = np.clip(stretched, 0, 255).astype(np.uint8)
        return Image.fromarray(stretched, mode="L")

    def _resize_to_target(self, img: object) -> object:
        from PIL import Image  # type: ignore[import]

        pil_img: Image.Image = img  # type: ignore[assignment]
        if pil_img.width != _PAGE_W_PX or pil_img.height != _PAGE_H_PX:
            pil_img = pil_img.resize((_PAGE_W_PX, _PAGE_H_PX), Image.LANCZOS)
        return pil_img

    def _detect_artifacts(self, img: object) -> bool:
        """Return True if any 50×50 random patch has std-dev below threshold (near-solid)."""
        import numpy as np
        from PIL import Image  # type: ignore[import]

        pil_img: Image.Image = img  # type: ignore[assignment]
        arr = np.array(pil_img, dtype=np.float32)
        h, w = arr.shape

        if h < _ARTIFACT_PATCH_SIZE or w < _ARTIFACT_PATCH_SIZE:
            return False

        rng = random.Random(42)
        for _ in range(_ARTIFACT_NUM_PATCHES):
            y = rng.randint(0, h - _ARTIFACT_PATCH_SIZE)
            x = rng.randint(0, w - _ARTIFACT_PATCH_SIZE)
            patch = arr[y : y + _ARTIFACT_PATCH_SIZE, x : x + _ARTIFACT_PATCH_SIZE]
            if float(patch.std()) < _ARTIFACT_STD_THRESHOLD:
                return True
        return False
