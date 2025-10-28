from pydantic import BaseModel

class EventCreate(BaseModel):
    user_id: int
    category_id: int
    reminder_id: int
    title: str
    description: str
    date: int
    start_time: int
    end_time: int
    priority: int
    location: str

class EventResponse(BaseModel):
    event_id: int
    category_id: int
    reminder_id: int
    title: str
    description: str
    date: int
    start_time: int
    end_time: int
    priority: int
    location: str

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema
