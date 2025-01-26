from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import engine, get_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # app starts here
    yield
    await engine.dispose()
    # app shuts down here

app = FastAPI(lifespan=lifespan)

@app.get("/test-db")
async def test_db_connection(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(1))
        return {"status": "success", "message": "Connected to the database", "data": result.scalar()}
    except Exception as e:
        return {"status": "error", "message": str(e)}