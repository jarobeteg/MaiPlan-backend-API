from typing import Annotated

from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from schemas.tide_schema import TideSyncRequest, TideSyncResponse
from services.tide_service import exchange_tide
from sqlalchemy.ext.asyncio import AsyncSession
from utils.auth_utils import AuthContext, get_auth_context

router = APIRouter()


@router.post("/sync", response_model=TideSyncResponse)
async def sync_exchange(
    request: TideSyncRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
) -> TideSyncResponse:
    if request.device_id != auth_context.session.device_id:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "AUTH_REQUIRED",
                "message": "The TIDE device ID does not match the authenticated session",
            },
        )
    return await exchange_tide(db=db, current_user=auth_context.user, request=request)
