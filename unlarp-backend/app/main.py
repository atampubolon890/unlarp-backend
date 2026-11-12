from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine
from .routers import auth, feed, personas, posts, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fine for early development. Move to Alembic migrations once the schema settles.
    Base.metadata.create_all(bind=engine)
    yield


generated_dir = settings.media_dir / "generated"
generated_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Unlarp API", version="0.1.0", lifespan=lifespan)

# Open CORS for local development; lock this to your app's domain before launch.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Only generated images are public. Selfies stay private on disk.
app.mount("/media/generated", StaticFiles(directory=generated_dir), name="generated")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(personas.router)
app.include_router(posts.router)
app.include_router(feed.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
