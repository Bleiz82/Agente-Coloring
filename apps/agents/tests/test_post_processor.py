"""Tests for ImagePostProcessor."""

from __future__ import annotations

import io

import pytest

from colorforge_agents.generator.post_processor import (
    _PAGE_H_PX,
    _PAGE_W_PX,
    ImagePostProcessor,
    ProcessedImage,
)


def _white_png(width: int = 100, height: int = 100, color: int = 255) -> bytes:
    """Return a grayscale PNG of given size and fill color."""
    try:
        from PIL import Image

        img = Image.new("L", (width, height), color=color)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        pytest.skip("Pillow not installed")


def _rgb_png(width: int = 100, height: int = 100) -> bytes:
    """Return an RGB PNG."""
    try:
        from PIL import Image

        img = Image.new("RGB", (width, height), color=(200, 150, 100))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        pytest.skip("Pillow not installed")


processor = ImagePostProcessor()


class TestGrayscaleConversion:
    def test_rgb_becomes_grayscale(self) -> None:
        from PIL import Image

        result = processor.process(_rgb_png())
        img = Image.open(io.BytesIO(result.data))
        assert img.mode == "L"

    def test_already_grayscale_stays_grayscale(self) -> None:
        from PIL import Image

        result = processor.process(_white_png())
        img = Image.open(io.BytesIO(result.data))
        assert img.mode == "L"


class TestDimensions:
    def test_output_is_target_size(self) -> None:
        from PIL import Image

        result = processor.process(_white_png(200, 300))
        img = Image.open(io.BytesIO(result.data))
        assert img.width == _PAGE_W_PX
        assert img.height == _PAGE_H_PX

    def test_result_reports_correct_dimensions(self) -> None:
        result = processor.process(_white_png())
        assert result.width_px == _PAGE_W_PX
        assert result.height_px == _PAGE_H_PX

    def test_output_png_bytes_nonempty(self) -> None:
        result = processor.process(_white_png())
        assert len(result.data) > 100


class TestArtifactDetection:
    def test_solid_white_page_is_artifact(self) -> None:
        # A completely white page (all pixels = 255) should be flagged
        result = processor.process(_white_png(2550, 3300, color=255))
        assert result.artifact_detected is True

    def test_solid_black_page_is_artifact(self) -> None:
        result = processor.process(_white_png(2550, 3300, color=0))
        assert result.artifact_detected is True

    def test_noisy_image_not_artifact(self) -> None:
        try:
            import numpy as np
            from PIL import Image
        except ImportError:
            pytest.skip("numpy/Pillow not installed")

        # Random noise — std-dev will be high in every patch
        rng = np.random.default_rng(42)
        arr = rng.integers(0, 256, size=(_PAGE_H_PX, _PAGE_W_PX), dtype=np.uint8)
        img = Image.fromarray(arr, mode="L")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = processor.process(buf.getvalue())
        assert result.artifact_detected is False


class TestContrastNormalization:
    def test_uniform_image_unchanged(self) -> None:
        # Uniform image: lo == hi → skip normalization
        result = processor.process(_white_png(color=128))
        assert isinstance(result, ProcessedImage)

    def test_low_contrast_image_processed(self) -> None:
        try:
            import numpy as np
            from PIL import Image
        except ImportError:
            pytest.skip("numpy/Pillow not installed")

        # Image with pixel values in range 100-110 (low contrast)
        arr = np.full((_PAGE_H_PX, _PAGE_W_PX), 100, dtype=np.uint8)
        arr[0, 0] = 110
        img = Image.fromarray(arr, mode="L")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = processor.process(buf.getvalue())
        # Should not raise
        assert result.data


class TestProcessedImageDataclass:
    def test_dataclass_fields(self) -> None:
        pi = ProcessedImage(data=b"abc", artifact_detected=True, width_px=100, height_px=200)
        assert pi.artifact_detected is True
        assert pi.width_px == 100
        assert pi.height_px == 200

    def test_invalid_image_bytes_raises(self) -> None:
        from colorforge_agents.exceptions import ImageGenerationError

        with pytest.raises(ImageGenerationError):
            processor.process(b"not a png")
