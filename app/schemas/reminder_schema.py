from pydantic import BaseModel

class ReminderCreate(BaseModel):
    user_id: int
    reminder_time: int
    frequency: int
    status: int
    message: str

class ReminderResponse(BaseModel):
    reminder_id: int
    reminder_time: int
    frequency: int
    status: int
    message: str

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema
