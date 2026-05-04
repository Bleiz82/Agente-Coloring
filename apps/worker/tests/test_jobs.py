"""Smoke tests for job handler signatures and imports."""

from __future__ import annotations

from colorforge_worker.jobs.publish import handle_publish_job
from colorforge_worker.jobs.scrape import handle_scrape_job


def test_publish_job_is_callable() -> None:
    import inspect

    sig = inspect.signature(handle_publish_job)
    params = list(sig.parameters)
    assert "book_id" in params
    assert "account_id" in params
    assert "listing_data" in params


def test_scrape_job_is_callable() -> None:
    import inspect

    sig = inspect.signature(handle_scrape_job)
    params = list(sig.parameters)
    assert "category_url" in params
    assert "niche_id" in params
