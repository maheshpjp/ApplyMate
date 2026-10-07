from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from urllib.parse import urljoin

from fastapi import HTTPException, status
from httpx import Client
from playwright.async_api import Browser, Page, async_playwright

from app.core.config import settings


@dataclass(frozen=True)
class JobDetail:
    job_title: str
    company_name: str
    description: str
    requirements: str
    source_url: str
    extracted_at: str


class BrowserAutomationService:
    """Inspect job pages without submitting applications or interacting with forms."""

    def __init__(self, *, browser: Browser | None = None) -> None:
        self.browser = browser

    async def inspect(self, url: str, *, company_name: str) -> JobDetail:
        if not url:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A job URL is required")

        if self.browser is None:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=settings.browser_headless)
                try:
                    return await self._inspect_with_browser(browser, url, company_name=company_name)
                finally:
                    await browser.close()

        return await self._inspect_with_browser(self.browser, url, company_name=company_name)

    async def _inspect_with_browser(self, browser: Browser, url: str, *, company_name: str) -> JobDetail:
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=settings.request_timeout_seconds * 1000)
        title = await self._text(page, "h1") or (await page.title()) or "Job opportunity"
        description = self._clean_text(await page.locator("main, article, [role='main']").inner_text())
        requirements = self._clean_text(await self._requirements_text(page))
        if not description and not requirements:
            description = self._clean_text(await page.locator("body").inner_text())
        return JobDetail(
            job_title=title.strip(),
            company_name=company_name.strip() or "Company",
            description=description[:12000],
            requirements=requirements[:12000],
            source_url=url,
            extracted_at=page.evaluate("(new Date()).toISOString()"),
        )

    async def _text(self, page: Page, selector: str) -> str:
        locators = page.locator(selector)
        count = await locators.count()
        if count == 0:
            return ""
        candidate = "\n".join(await locators.all_inner_texts())
        return self._clean_text(candidate)

    async def _requirements_text(self, page: Page) -> str:
        selectors = [
            "section:has-text('requirements')",
            "section:has-text('qualifications')",
            "section:has-text('responsibilities')",
            "[class*='requirements']",
            "[class*='qualifications']",
        ]
        for selector in selectors:
            count = await page.locator(selector).count()
            if count:
                texts = await page.locator(selector).all_inner_texts()
                return self._clean_text("\n".join(texts))
        return ""

    @staticmethod
    def _clean_text(value: str) -> str:
        return unescape(" ".join(value.replace("\xa0", " ").split()))
