from contextlib import asynccontextmanager

from core.database import engine
from fastapi import FastAPI
from routers import auth, categories, events, notes, raspi, reminders, subtasks, tasks


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
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
app.include_router(subtasks.router, prefix="/subtasks", tags=["Subtasks"])