from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    sync_id: UUID
    email: str
    username: str
    password: str
    password_again: str
    device_id: UUID

class UserLogin(BaseModel):
    email: str
    password: str
    device_id: UUID


class RefreshTokenRequest(BaseModel):
    refresh_token: str
    device_id: UUID

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sync_id: UUID
    email: str
    username: str
    server_version: int = Field(validation_alias="version")
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

class AuthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    session_id: UUID
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    user: UserResponse
