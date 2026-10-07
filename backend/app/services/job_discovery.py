from __future__ import annotations

import asyncio
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from app.core.config import settings


JOB_KEYWORDS = (
    "engineer",
    "developer",
    "software",
    "product",
    "data",
    "design",
    "research",
    "analyst",
    "operations",
    "intern",
    "contract",
    "part-time",
    "full-time",
    "associate",
)


@dataclass(frozen=True)
class DiscoveredJob:
    title: str
    url: str


def normalize_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if not parsed.scheme and not parsed.netloc:
        return raw_url
    if not parsed.scheme:
        return raw_url

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            "",
        )
    )


def parse_job_links(html: str, base_url: str) -> list[str]:
    class JobLinkParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.links: list[str] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag != "a":
                return
            attributes = dict(attrs)
            href = attributes.get("href")
            if not href or href.startswith(("mailto:", "tel:")):
                return

            absolute_url = urljoin(base_url, href)
            normalized_url = normalize_url(absolute_url)
            path = urlparse(normalized_url).path.lower()
            is_job_link = normalized_url.startswith("http") and ("/jobs/" in path or "/job/" in path)
            is_careers_link = normalized_url.startswith("http") and normalized_url != base_url and "/careers" in normalized_url
            if is_job_link and normalized_url not in self.links:
                self.links.append(normalized_url)
            elif is_careers_link and normalized_url not in self.links:
                self.links.append(normalized_url)

    parser = JobLinkParser()
    parser.feed(html)
    return parser.links


class JobDiscoveryService:
    def __init__(self, client: httpx.Client | httpx.AsyncClient | None = None) -> None:
        self.client = client

    def discover_from_html(self, html: str, base_url: str) -> list[DiscoveredJob]:
        links = parse_job_links(html, base_url)
        jobs: list[DiscoveredJob] = []

        parser = _JobTitleParser(base_url)
        parser.feed(html)
        titles_by_url = parser.titles_by_url

        for link in links:
            title = titles_by_url.get(link)
            if title is None or _is_generic_link_text(title):
                title = _infer_title_from_url(link)
            if not title or not _looks_like_job_title(title):
                continue
            jobs.append(DiscoveredJob(title=title, url=link))

        return jobs

    async def discover_url(self, url: str) -> list[DiscoveredJob]:
        client = self.client or httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0))
        try:
            response = await client.get(url)
            response.raise_for_status()
        finally:
            if self.client is None:
                await client.aclose()

        jobs = self.discover_from_html(response.text, str(response.url))
        if jobs:
            return jobs

        return await self._discover_rendered_page(url)

    async def _discover_rendered_page(self, url: str) -> list[DiscoveredJob]:
        return await asyncio.to_thread(self._discover_rendered_page_sync, url)

    def _discover_rendered_page_sync(self, url: str) -> list[DiscoveredJob]:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=settings.browser_headless)
                try:
                    page = browser.new_page()
                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=settings.request_timeout_seconds * 1000,
                    )
                    page.wait_for_timeout(1500)
                    jobs = self.discover_from_html(page.content(), page.url)
                    if jobs:
                        return jobs

                    search_pages = page.locator("a[href]").evaluate_all(
                        """links => links
                            .map(link => new URL(link.href, location.href))
                            .filter(link => link.origin === location.origin
                                && /search|jobs|careers|career|openings/i.test(link.pathname))
                            .map(link => link.href)
                            .filter((href, index, all) => href !== location.href && all.indexOf(href) === index)
                            .slice(0, 3)"""
                    )
                    for search_url in search_pages:
                        page.goto(
                            search_url,
                            wait_until="domcontentloaded",
                            timeout=settings.request_timeout_seconds * 1000,
                        )
                        page.wait_for_timeout(1500)
                        jobs = self.discover_from_html(page.content(), page.url)
                        if jobs:
                            return jobs

                    return []
                finally:
                    browser.close()
        except PlaywrightError as exc:
            message = str(exc).strip() or "Playwright could not start or use Chromium."
            if "Executable doesn't exist" in message:
                message += " Install the browser with `python -m playwright install chromium`."
            raise RuntimeError(f"Browser-based careers-page check failed: {message}") from exc
        except NotImplementedError as exc:
            raise RuntimeError(
                "The browser could not start in this Windows environment. Restart the backend "
                "after installing Chromium with `python -m playwright install chromium`."
            ) from exc


class _JobTitleParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self._current_link: tuple[str, str] | None = None
        self._current_text: list[str] = []
        self.titles_by_url: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attributes = dict(attrs)
        href = attributes.get("href")
        if not href:
            return

        absolute_url = normalize_url(urljoin(self.base_url, href))
        self._current_link = (absolute_url, href)
        self._current_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_link is None:
            return

        url, _ = self._current_link
        text = " ".join(part.strip() for part in self._current_text if part.strip())
        if text:
            self.titles_by_url[url] = text
        self._current_link = None
        self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_link is not None:
            self._current_text.append(data)


def _infer_title_from_url(url: str) -> str | None:
    path = urlparse(url).path.strip("/")
    if not path:
        return None

    segments = [segment for segment in path.split("/") if segment and segment != "jobs"]
    title = " ".join(segment.replace("-", " ") for segment in segments)
    words = [word for word in title.split() if word]
    if not words:
        return None
    return " ".join(words).title() if _looks_like_job_title(title) else None


def _looks_like_job_title(title: str) -> bool:
    normalized = title.lower()
    return any(keyword in normalized for keyword in JOB_KEYWORDS) or any(word.isupper() for word in title.split())


def _is_generic_link_text(title: str) -> bool:
    normalized = title.lower().strip()
    return normalized in {"view role", "apply", "learn more", "more details", "read more"}
