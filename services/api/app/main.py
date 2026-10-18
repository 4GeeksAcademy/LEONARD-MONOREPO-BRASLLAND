import io
import sys
import threading
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages"))

from incident_analysis import AnalysisError, RULES, analyze_csv, results_csv
from services.api.auth import (
    CurrentUser, auth_router, configure_auth, open_auth_database, profiles_router,
    public_router, require_authentication, users_router,
)
from services.api.database import open_database
from services.api.routers.suppliers import router as suppliers_router
from services.api.routers.incidents import router as incidents_router
from services.api.routers.inventory import router as inventory_router
from services.api.app.database import engine
from services.api.app import models as inventory_models
from sqlmodel import SQLModel
from services.api.seed import seed_database


MAX_UPLOAD_BYTES = 256 * 1024 * 1024
SESSION_TTL = 3600
MAX_SESSIONS = 128
analyses = OrderedDict()
cache_lock = threading.Lock()


class UploadLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length", b"0")
        if content_length.isdigit() and int(content_length) > MAX_UPLOAD_BYTES:
            return await JSONResponse(
                status_code=413, content={"detail": "Upload exceeds the 256 MiB limit."}
            )(scope, receive, send)
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Upload exceeds the 256 MiB limit.")
            return message

        await self.app(scope, limited_receive, send)


@asynccontextmanager
async def lifespan(app):
    configure_auth(app)
    if engine is not None:
        SQLModel.metadata.create_all(engine)
    with open_database() as database, open_auth_database() as auth_database:
        seed_database(database)
        app.state.suppliers_db = database
        app.state.auth_db = auth_database
        yield


app = FastAPI(
    title="Brasaland Digital API", version="1.1.0", lifespan=lifespan,
    dependencies=[Depends(require_authentication)],
)
app.add_middleware(UploadLimitMiddleware)
app.include_router(public_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(suppliers_router)
app.include_router(incidents_router)
app.include_router(inventory_router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError):
    fields = [
        {
            "field": ".".join(str(part) for part in issue["loc"][1:]) or "request",
            "message": issue["msg"],
        }
        for issue in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": fields})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, error: Exception):
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})


def expire_cache() -> None:
    now = time.monotonic()
    for token, (created, _) in list(analyses.items()):
        if now - created >= SESSION_TTL:
            del analyses[token]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/incidents/analyze")
def analyze_incidents(current: CurrentUser, response: Response, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(415, "Select a .csv file encoded as UTF-8.")
    source = io.TextIOWrapper(file.file, encoding="utf-8-sig", newline="")
    try:
        summary = analyze_csv(source)
    except AnalysisError as error:
        raise HTTPException(400, str(error)) from error
    finally:
        source.detach()
    with cache_lock:
        expire_cache()
        analyses[current.id] = (time.monotonic(), summary)
        analyses.move_to_end(current.id)
        while len(analyses) > MAX_SESSIONS:
            analyses.popitem(last=False)
    response.headers["Cache-Control"] = "no-store"
    return {**summary, "rule_labels": RULES}


@app.get("/api/incidents/results/export")
def export_results(current: CurrentUser):
    with cache_lock:
        expire_cache()
        cached = analyses.get(current.id)
    if cached is None:
        raise HTTPException(404, "No analysis is available for this user. Upload a CSV first; results expire after one hour.")
    return Response(
        content=results_csv(cached[1]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="results.csv"', "Cache-Control": "no-store"},
    )


@app.get("/")
def home():
    return RedirectResponse("/backoffice/")


frontend = ROOT / "uis" / "backoffice" / "public"
if frontend.exists():
    app.mount("/backoffice", StaticFiles(directory=frontend, html=True), name="backoffice")