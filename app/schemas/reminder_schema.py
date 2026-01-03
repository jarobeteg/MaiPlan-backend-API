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

class ReminderSync(BaseModel):
    reminder_id: int
    server_id: int
    user_id: int
    reminder_time: int
    frequency: int
    status: int
    message: str
    created_at: int
    updated_at: int
    last_modified: int
    sync_state: int
    is_deleted: int

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema