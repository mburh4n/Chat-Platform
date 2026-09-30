import logging

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppError

# Show INFO-level log messages from our own modules (e.g. "Email sent to ...")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
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
