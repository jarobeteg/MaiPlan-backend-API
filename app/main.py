from contextlib import asynccontextmanager

from core.database import engine
from fastapi import FastAPI
from routers import auth, raspi, sync


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
app.include_router(sync.router, tags=["TIDE"])
