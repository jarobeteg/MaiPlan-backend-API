from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResetPassword(BaseModel):
    email: str
    password: str
    password_again: str

class UserRegister(BaseModel):
    email: str
    username: str
    password: str
    password_again: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    user_id: int
    email: str
    username: str

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema

class AuthResponse(BaseModel):
    access_token: str
    user: UserResponse

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema

class AuthSync(BaseModel):
    user_id: int
    server_id: int
    email: str
    username: str
    balance: float
    created_at: int
    updated_at: int
    password_hash: str
    last_modified: int
    sync_state: int
    is_deleted: int

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema
