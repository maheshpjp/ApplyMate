import threading
from unittest.mock import AsyncMock

import httpx
import pytest

from app.services.job_discovery import DiscoveredJob, JobDiscoveryService, normalize_url, parse_job_links


HTML_PAGE = """
<html>
  <head>
    <title>Engineering careers</title>
  </head>
  <body>
    <main>
      <h1>Software Engineer</h1>
      <a href="/jobs/software-engineer">View role</a>
      <a href="https://example.com/jobs/product-manager">Product Manager</a>
      <a href="https://example.com/careers">Company careers</a>
      <a href="mailto:jobs@example.com">Email us</a>
      <script>ignored script</script>
    </main>
  </body>
</html>
"""


def test_parse_job_links_skips_non_role_links() -> None:
    jobs = parse_job_links(HTML_PAGE, "https://example.com/careers")

    assert jobs == [
        "https://example.com/jobs/software-engineer",
        "https://example.com/jobs/product-manager",
    ]


def test_normalize_url_preserves_https_and_removes_fragments() -> None:
    assert normalize_url("https://example.com/jobs/role?ref=top#apply") == "https://example.com/jobs/role?ref=top"
    assert normalize_url("/jobs/role") == "/jobs/role"


def test_discovery_service_extracts_role_details() -> None:
    result = JobDiscoveryService().discover_from_html(HTML_PAGE, "https://example.com/careers")

    assert len(result) == 2
    assert result[0].title == "Software Engineer"
    assert result[0].url == "https://example.com/jobs/software-engineer"
    assert result[1].title == "Product Manager"
    assert result[1].url == "https://example.com/jobs/product-manager"


def test_discovery_service_ignores_pages_without_roles() -> None:
    result = JobDiscoveryService().discover_from_html("<html><body>No roles here</body></html>", "https://example.com")
    assert result == []


@pytest.mark.asyncio
async def test_discovery_falls_back_to_rendered_page_when_static_html_has_no_roles(monkeypatch) -> None:
    url = "https://careers.example.com/us/en/home"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            request=request,
            text="<html><body>JavaScript loads the job listings</body></html>",
        )
    )
    rendered_jobs = [
        DiscoveredJob(
            title="Software Engineer",
            url="https://careers.example.com/us/en/job/123/Software-Engineer",
        )
    ]

    async with httpx.AsyncClient(transport=transport) as client:
        service = JobDiscoveryService(client=client)
        render_fallback = AsyncMock(return_value=rendered_jobs)
        monkeypatch.setattr(service, "_discover_rendered_page", render_fallback)

        result = await service.discover_url(url)

    assert result == rendered_jobs
    render_fallback.assert_awaited_once_with(url)


@pytest.mark.asyncio
async def test_rendered_page_fallback_runs_off_the_asyncio_event_loop_thread(monkeypatch) -> None:
    service = JobDiscoveryService()
    event_loop_thread = threading.get_ident()
    worker_threads = []

    def render(url: str) -> list[DiscoveredJob]:
        worker_threads.append(threading.get_ident())
        return []

    monkeypatch.setattr(service, "_discover_rendered_page_sync", render)

    result = await service._discover_rendered_page("https://careers.example.com/jobs")

    assert result == []
    assert worker_threads
    assert worker_threads[0] != event_loop_thread
