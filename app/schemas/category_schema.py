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