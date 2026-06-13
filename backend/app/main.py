from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import activities, auth, availability, events, plan, profile


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup. (For schema changes later, switch to Alembic.)
    Base.metadata.create_all(bind=engine)
    yield


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
