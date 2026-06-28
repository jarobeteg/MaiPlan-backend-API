from pydantic import BaseModel

class NoteSync(BaseModel):
    note_id: int
    server_id: int
    user_id: int
    category_id: int
    reminder_id: int
    title: str
    content: str
    created_at: int
    updated_at: int
    last_modified: int
    sync_state: int
    is_deleted: int
    is_pinned: int

    class Config:
        from_attributes = True # auto conversion from ORM model to pydantic schema