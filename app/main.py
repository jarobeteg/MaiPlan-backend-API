from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import engine
from routers import auth, categories, reminders, events

@asynccontextmanager
async def lifespan(app: FastAPI):
    # app starts here
    yield
    await engine.dispose()
    # app shuts down here

app = FastAPI(lifespan=lifespan)

# API routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(categories.router, prefix="/categories", tags=["Categories"])
app.include_router(reminders.router, prefix="/reminders", tags=["Reminders"])
app.include_router(events.router, prefix="/events", tags=["Events"])
