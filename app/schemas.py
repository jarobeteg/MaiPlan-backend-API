from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class UserRegister(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    user_id: int
    email: str
    username: str

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema
