from pydantic import BaseModel
from datetime import datetime, date, time

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

class ReminderCreate(BaseModel):
    reminder_id: int
    user_id: int
    reminder_time: datetime
    frequency: int
    status: int
    message: str

class ReminderResponse(BaseModel):
    reminder_id: int
    reminder_time: datetime
    frequency: int
    status: int
    message: str

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema

class EventCreate(BaseModel):
    event_id: int
    user_id: int
    category_id: int
    reminder_id: int
    title: str
    description: str
    date: date
    start_time: time
    end_time: time
    priority: int
    location: str

class EventResponse(BaseModel):
    event_id: int
    category_id: int
    reminder_id: int
    title: str
    description: str
    date: date
    start_time: time
    end_time: time
    priority: int
    location: str

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema
