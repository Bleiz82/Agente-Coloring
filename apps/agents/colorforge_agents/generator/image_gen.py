"""Gemini image generation client with rate-limiting and retry."""

from __future__ import annotations

import asyncio
import base64
from typing import Any

from loguru import logger

from colorforge_agents.exceptions import ImageGenerationError

_DEFAULT_MODEL = "gemini-3.1-flash-image-generation"
_MAX_CONCURRENT = 3
_MAX_RETRIES = 3
_RETRY_BASE_S = 2.0
_RETRY_CAP_S = 30.0


class GeminiImageClient:
    """Calls Gemini image generation API with semaphore-limited concurrency."""

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        self._api_key = api_key
        self._model = model
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def generate_image(self, prompt: str) -> bytes:
        """Generate a PNG image from a text prompt. Returns raw PNG bytes."""
        async with self._semaphore:
            for attempt in range(1, _MAX_RETRIES + 1):
                try:
                    return await self._call_api(prompt)
                except ImageGenerationError:
                    if attempt == _MAX_RETRIES:
                        raise
                    wait = min(_RETRY_BASE_S * (2 ** (attempt - 1)), _RETRY_CAP_S)
                    logger.warning(
                        "Gemini attempt {}/{} failed, retrying in {:.0f}s",
                        attempt,
                        _MAX_RETRIES,
                        wait,
                    )
                    await asyncio.sleep(wait)
        raise ImageGenerationError("generate_image: unreachable code path")

    async def _call_api(self, prompt: str) -> bytes:
        """Single API call — returns PNG bytes or raises ImageGenerationError."""
        try:
            from google.genai import types

            client = self._get_client()
            response = await client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )
        except Exception as exc:
            raise ImageGenerationError(f"Gemini API error: {exc}") from exc

        try:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data is not None:
                    data = part.inline_data.data
                    # SDK may return base64-encoded string or raw bytes
                    if isinstance(data, str):
                        return base64.b64decode(data)
                    return bytes(data)
        except (IndexError, AttributeError) as exc:
            raise ImageGenerationError(f"Unexpected response structure: {exc}") from exc

        raise ImageGenerationError("No image part found in Gemini response")
