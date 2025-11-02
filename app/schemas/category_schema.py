from pydantic import BaseModel

class CategoryCreate(BaseModel):
    user_id: int
    name: str
    description: str
    color: str
    icon: str

class CategoryResponse(BaseModel):
    category_id: int
    name: str
    description: str
    color: str
    icon: str

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema

class CategorySync(BaseModel):
    category_id: int
    server_id: int
    user_id: int
    name: str
    description: str
    color: str
    icon: str
    created_at: int
    updated_at: int
    last_modified: int
    sync_state: int
    is_deleted: int

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema
