from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import auth, users, resumes, companies, jobs, applications, scheduler, schedules
from app.core.config import settings
from app.core.logging import setup_logging
from app.database.database import check_database_connection, initialize_database
from app.services.scheduler import SchedulerService

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_database()
    scheduler_service = SchedulerService()
    app.state.scheduler = scheduler_service
    await scheduler_service.start()
    try:
        yield
    finally:
        await scheduler_service.stop()


app = FastAPI(
    title="AI Job Application Automation Platform",
    version="0.1.0",
    description="Secure, human-reviewed job application automation for job seekers.",
    docs_url="/docs" if settings.environment.casefold() != "production" else None,
    redoc_url="/redoc" if settings.environment.casefold() != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth.router, users.router, resumes.router, companies.router, jobs.router, applications.router, scheduler.router, schedules.router):
    app.include_router(router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness() -> dict[str, str]:
    await check_database_connection()
    return {"status": "ready"}
