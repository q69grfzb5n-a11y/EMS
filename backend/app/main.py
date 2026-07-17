from fastapi import APIRouter, FastAPI
from sqlalchemy import text

from app.db.session import SessionLocal

api_router = APIRouter(prefix="/api/v1")


def create_app() -> FastAPI:
    app = FastAPI(title="EMS API")
    app.include_router(api_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        db_status = "connected"
        try:
            with SessionLocal() as session:
                session.execute(text("SELECT 1"))
        except Exception:
            db_status = "unavailable"
        return {"status": "ok", "db": db_status}

    return app


app = create_app()
