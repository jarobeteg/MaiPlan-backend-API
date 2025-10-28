from typing import TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar("T")

class SyncRequest(BaseModel, Generic[T]):
    email: str
    changes: List[T]

class SyncResponse(BaseModel, Generic[T]):
    email: str
    acknowledged: List[T]
    rejected: List[T]