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

class CategoryCreate(BaseModel):
    category_id: int
    user_id: int
    entity_type: int
    name: str
    description: str

class CategoryResponse(BaseMode):
    category_id: int
    entity_type: int
    name: str
    description: str

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema
