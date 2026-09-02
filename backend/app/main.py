"""Application entry point."""
import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.config import get_settings
from app.db import SessionLocal
from app.routers import auth, dispatch, reports
from app.services.dispatch import escalation_sweep

settings = get_settings()
log = logging.getLogger("aidly.escalation")

# How often the timer looks for overdue incidents. Deliberately shorter than
# the escalation interval itself, so an incident cannot sit a whole extra
# period past its deadline before anybody is told.
SWEEP_SECONDS = max(5, settings.escalation_seconds // 4)


async def _escalation_timer() -> None:
    """FR 12: an unacknowledged high severity incident escalates on its own.

    Runs in the application rather than in a separate scheduler so that a
    single process is enough to satisfy the requirement. One failed pass must
    never stop the timer, because the pass that matters is usually the one
    during an incident, which is exactly when things are going wrong.
    """
    while True:
        await asyncio.sleep(SWEEP_SECONDS)
        db = SessionLocal()
        try:
            escalated = await asyncio.to_thread(escalation_sweep, db)
            for incident in escalated:
                log.warning("escalated incident %s", incident.id)
        except Exception:
            log.exception("escalation sweep failed, continuing")
        finally:
            db.close()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_escalation_timer())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="Aidly",
    description="Venue operations layer for crowd emergencies",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(dispatch.router)

STATIC = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
@app.get("/login", include_in_schema=False)
def login_page() -> FileResponse:
    """The control room sign in screen, served by the same application that
    owns the endpoint, so the module can be demonstrated end to end."""
    return FileResponse(STATIC / "login.html")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
