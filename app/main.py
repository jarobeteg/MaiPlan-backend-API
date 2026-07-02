from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.database import engine
from routers import raspi, auth, categories, reminders, events, notes

@asynccontextmanager
async def lifespan(api: FastAPI):
    # app starts here
    yield
    await engine.dispose()
    # app shuts down here

app = FastAPI(lifespan=lifespan)

# API routers
app.include_router(raspi.router, prefix="/raspi", tags=["System"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(categories.router, prefix="/categories", tags=["Categories"])
app.include_router(reminders.router, prefix="/reminders", tags=["Reminders"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(notes.router, prefix="/notes", tags=["Notes"])
