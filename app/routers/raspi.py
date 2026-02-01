from fastapi import APIRouter
from fastapi.responses import JSONResponse
import socket
import time

router = APIRouter()
start_time = time.time()

def format_uptime(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

@router.get("/health")
async def health_check():
    uptime_seconds = int(time.time() - start_time)
    uptime_formatted = format_uptime(uptime_seconds)
    hostname = socket.gethostname()

    return JSONResponse(
            content={
                "server" : "integration",
                "status": "healthy",
                "uptime": uptime_formatted,
                "hostname": hostname,
            }
        )
