from typing import TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar("T")

class SyncRequest(BaseModel, Generic[T]):
    user_id: int
    changes: List[T]

class SyncResponse(BaseModel, Generic[T]):
    user_id: int
    acknowledged: List[T]
    rejected: List[T]