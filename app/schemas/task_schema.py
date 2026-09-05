from pydantic import BaseModel


class TaskSync(BaseModel):
    task_id: int
    server_id: int
    user_id: int
    category_id: int
    reminder_id: int
    title: str
    description: str
    status: int
    scheduled_date: int
    estimated_time: int
    completed_date: int
    series_id: str
    occurrence_number: int
    repeat_unit: int
    repeat_interval: int
    repeat_weekdays: int
    repeat_end_date: int
    repeat_anchor_date: int
    created_at: int
    updated_at: int
    last_modified: int
    sync_state: int
    is_deleted: int

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema