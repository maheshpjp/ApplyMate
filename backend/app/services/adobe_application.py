from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from app.core.config import settings
from app.services.application_answers import find_resume_answer, is_private_question


@dataclass(frozen=True)
class SubmissionResult:
    submitted: bool
    message: str


class ApplicationAutomationService:
    @staticmethod
    def value_for_field(label: str, profile: dict[str, Any]) -> str | None:
        normalized = re.sub(r"[^a-z0-9]+", " ", label.casefold()).strip()
        first_name, _, last_name = str(profile.get("name") or "").strip().partition(" ")
        values = (
            (("full name",), profile.get("name")),
            (("given name", "first name"), first_name),
            (("family name", "last name", "surname"), last_name),
            (("email",), profile.get("email")),
            (("phone", "telephone", "mobile"), profile.get("phone")),
            (("linkedin",), profile.get("linkedin")),
            (("github",), profile.get("github")),
            (("portfolio", "website"), profile.get("portfolio")),
            (("work authorization", "authorized to work"), profile.get("work_authorization")),
        )
        for labels, value in values:
            if value and any(key in normalized for key in labels):
                return str(value)

        location = str(profile.get("location") or "")
        parts = [part.strip() for part in location.split(",") if part.strip()]
        if parts and "city" in normalized:
            return parts[0]
        if len(parts) > 1 and ("state" in normalized or "province" in normalized):
            return parts[1]
        return None

    async def submit(
        self,
        job_url: str,
        *,
        resume_path: str,
        profile: dict[str, Any],
        resume_text: str = "",
        auto_submit_authorized: bool,
    ) -> SubmissionResult:
        if not auto_submit_authorized:
            return SubmissionResult(False, "Automatic submission was not authorized for this schedule.")
        if urlparse(job_url).scheme not in {"http", "https"}:
            return SubmissionResult(False, "The job page URL must use HTTP or HTTPS.")
        if not Path(resume_path).is_file():
            return SubmissionResult(False, "The selected resume file is not available on disk.")

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=settings.browser_headless)
            try:
                page = await browser.new_page()
                response = await page.goto(
                    job_url,
                    wait_until="domcontentloaded",
                    timeout=settings.request_timeout_seconds * 1000,
                )
                if response and response.status >= 400:
                    return SubmissionResult(False, f"The job page returned HTTP {response.status}.")

                apply_link = page.get_by_role("link", name=re.compile(r"\bapply\b", re.I)).first
                if await apply_link.count():
                    await apply_link.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                elif await page.locator("form").count() == 0:
                    return SubmissionResult(False, "Could not find an application link or form on the job page.")

                file_attached = False

                for _ in range(6):
                    blocker = await self._blocking_message(page)
                    if blocker:
                        return SubmissionResult(False, blocker)

                    if not file_attached:
                        file_input = page.locator("input[type='file']").first
                        if await file_input.count() and not await file_input.is_disabled():
                            await file_input.set_input_files(resume_path)
                            file_attached = True
                            await page.wait_for_timeout(1000)

                    unresolved = await self._fill_visible_fields(page, profile, resume_text)
                    if unresolved:
                        return SubmissionResult(
                            False,
                            "Automatic submission stopped because required fields need your answer: "
                            + ", ".join(unresolved[:8]),
                        )

                    submit_button = page.get_by_role("button", name=re.compile(r"submit application|submit your application|^submit$", re.I)).last
                    if await submit_button.count():
                        if not file_attached:
                            return SubmissionResult(False, "The selected resume could not be attached to the application form.")
                        await submit_button.click()
                        await page.wait_for_timeout(2500)
                        confirmation = (await page.locator("body").inner_text()).casefold()
                        if any(text in confirmation for text in ("application submitted", "thank you for applying", "successfully submitted", "application received", "submission complete")):
                            return SubmissionResult(True, "The careers site confirmed the application was submitted.")
                        return SubmissionResult(
                            False,
                            "The final submit step was attempted, but no confirmation appeared. Check the careers site before retrying.",
                        )

                    next_button = page.get_by_role("button", name=re.compile(r"^next$|continue", re.I)).last
                    if not await next_button.count():
                        return SubmissionResult(False, "The application form has an unsupported layout or no safe next action.")
                    await next_button.click()
                    await page.wait_for_timeout(1000)

                return SubmissionResult(False, "The application has more steps than the supported flow can safely complete.")
            except Exception as exc:
                return SubmissionResult(False, f"Application automation stopped: {exc}")
            finally:
                await browser.close()

    async def _fill_visible_fields(self, page, profile: dict[str, Any], resume_text: str) -> list[str]:
        fields = page.locator("input:not([type='hidden']), select, textarea")
        unresolved: list[str] = []
        for index in range(await fields.count()):
            field = fields.nth(index)
            if not await field.is_visible() or await field.is_disabled():
                continue

            description = await field.evaluate(
                "element => ({tag: element.tagName.toLowerCase(), type: element.type || '', "
                "required: element.required || element.getAttribute('aria-required') === 'true', "
                "value: element.value || '', checked: element.checked || false, label: [element.getAttribute('aria-label'), element.getAttribute('placeholder'), "
                "element.name, element.id, ...(element.labels ? Array.from(element.labels).map(label => label.innerText) : [])] "
                ".filter(Boolean).join(' ')})"
            )
            label = description["label"].strip() or f"required {description['type'] or description['tag']} field"
            normalized_label = label.casefold()

            if description["type"] == "file":
                continue
            if description["type"] in {"checkbox", "radio"}:
                if is_private_question(label) or any(
                    word in normalized_label for word in ("privacy", "consent", "certify", "accurate", "terms")
                ):
                    unresolved.append(label)
                elif description["required"] and not description["checked"]:
                    unresolved.append(label)
                continue
            if description["value"]:
                continue

            value = self.value_for_field(label, profile)
            if value is None and description["tag"] == "textarea":
                value = find_resume_answer(label, resume_text)
            if value:
                if description["tag"] == "select":
                    try:
                        options = await field.locator("option").evaluate_all(
                            "elements => elements.map(option => ({value: option.value, label: option.label}))"
                        )
                        option = next(
                            (
                                item for item in options
                                if value.casefold() in item["label"].casefold()
                                and item["value"]
                            ),
                            None,
                        )
                        if option:
                            await field.select_option(value=option["value"])
                        elif description["required"]:
                            unresolved.append(label)
                    except Exception:
                        if description["required"]:
                            unresolved.append(label)
                else:
                    await field.fill(value)
            elif description["required"] or is_private_question(label):
                unresolved.append(label)

        return unresolved

    async def _blocking_message(self, page) -> str | None:
        current_url = page.url.casefold()
        body = (await page.locator("body").inner_text()).casefold()
        if any(word in current_url for word in ("login", "signin", "sign-in")):
            return "The careers site requires sign-in. ApplyMate will not use or store the site's password."
        if await page.locator("iframe[src*='captcha'], [id*='captcha'], [class*='captcha']").count():
            return "The careers site presented a CAPTCHA; automatic submission stopped for manual completion."
        if "verify you are human" in body or "security challenge" in body:
            return "The careers site presented a security challenge; automatic submission stopped."
        return None