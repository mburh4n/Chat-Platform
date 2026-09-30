import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.core.exceptions import AppError
from app.documents import service as documents_service
from app.documents import storage
from app.documents.router import router as documents_router
from app.users.router import router as users_router

# Show INFO-level log messages from our own modules (e.g. "Email sent to ...")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts."""
    storage.ensure_upload_dir()
    # Background tasks die with the process: mark their documents as failed
    with SessionLocal() as db:
        interrupted = documents_service.fail_interrupted_documents(db)
    if interrupted:
        logger.warning("Marked %s interrupted document(s) as failed", interrupted)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# Allow the React frontend (a different origin) to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # we send the JWT in a header, not in cookies
    allow_methods=["*"],
    allow_headers=["*"],
)


# Turn any AppError raised in a service into a JSON error response
@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(documents_router)


@app.get("/", tags=["Root"])
def root():
    return {"message": f"{settings.app_name} API is running"}


# Plain "def" (not "async def") because the database session is synchronous.
@app.get("/api/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable",
        )
    return {"status": "ok", "database": "connected"}
