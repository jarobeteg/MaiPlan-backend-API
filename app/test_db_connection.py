import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def test_connection():
    engine = create_async_engine(DATABASE_URL, echo=True)

    try:
        async with engine.connect() as connection:
            print("Successfully connected to the database!")
            result = await connection.execute(text("SELECT 1"))
            print("Query result:", result.scalar())
    except Exception as e:
        print("Failed to connect to the database.")
        print("Error:", str(e))
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection())