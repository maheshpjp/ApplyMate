from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
from sqlalchemy import select

from app.models.job import Job
from app.services.job_discovery import JobDiscoveryService


class CareerPageHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = b"""
        <html>
          <body>
            <a href="/jobs/software-engineer">View role</a>
            <a href="/jobs/product-manager">Product Manager</a>
          </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def test_discovery_finds_singular_job_paths_and_resolves_relative_links() -> None:
    jobs = JobDiscoveryService().discover_from_html(
        '<a href="/us/en/job/R123/Software-Engineer">Software Engineer</a>',
        "https://careers.example.com/us/en/c/engineering-jobs",
    )

    assert len(jobs) == 1
    assert jobs[0].title == "Software Engineer"
    assert jobs[0].url == "https://careers.example.com/us/en/job/R123/Software-Engineer"


@pytest.mark.asyncio
async def test_company_discovery_creates_user_jobs(authenticated_client) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), CareerPageHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        response = await authenticated_client.post(
            "/api/companies/discover-careers",
            params={"company_url": f"http://127.0.0.1:{server.server_port}/careers"},
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()

    assert response.status_code == 201
    payload = response.json()
    assert payload["created_jobs"] == 2
    assert payload["jobs"][0]["job_title"] == "Software Engineer"
    assert payload["jobs"][1]["job_title"] == "Product Manager"

    rows = await authenticated_client.get("/api/jobs")
    assert rows.status_code == 200
    jobs = rows.json()
    assert len(jobs) == 2
    assert {job["job_title"] for job in jobs} == {"Software Engineer", "Product Manager"}
