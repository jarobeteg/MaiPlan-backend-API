from pydantic import BaseModel


class SubtaskSync(BaseModel):
    subtask_id: int
    server_id: int
    task_id: int
    title: str
    status: int
    sort_order: int
    estimated_time: int
    completed_date: int
    created_at: int
    updated_at: int
    last_modified: int
    sync_state: int
    is_deleted: int

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema