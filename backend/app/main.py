from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import activities, auth, availability, events, plan, profile


def _migrate(conn):
    """Lightweight additive migrations — adds new columns to existing tables."""
    is_sqlite = str(engine.url).startswith("sqlite")
    real_type = "REAL" if is_sqlite else "DOUBLE PRECISION"
    new_cols = [
        ("profile", "weekly_sessions",  "INTEGER"),
        ("profile", "weekly_hours",     real_type),
        ("profile", "weekly_km_target", real_type),
        ("profile", "schedule_notes",   "TEXT"),
    ]
    for table, col, col_type in new_cols:
        try:
            conn.execute(
                __import__("sqlalchemy").text(
                    f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"
                )
            )
            conn.commit()
        except Exception:
            conn.rollback()  # column already exists — ignore


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        _migrate(conn)
    from .services.scheduler import shutdown_scheduler, start_scheduler

    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="ripe_fitness API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "ripe_fitness", "version": "0.1.0"}


app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(availability.router)
app.include_router(events.router)
app.include_router(activities.router)
app.include_router(plan.router)
