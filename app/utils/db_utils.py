from dataclasses import dataclass

@dataclass
class DBOperationContext:
    success: bool
    exception_type: str | None = None
    exception_message: str | None = None