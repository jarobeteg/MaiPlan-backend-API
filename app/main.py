from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import engine
from routers import auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # app starts here
    yield
    await engine.dispose()
    # app shuts down here

app = FastAPI(lifespan=lifespan)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
