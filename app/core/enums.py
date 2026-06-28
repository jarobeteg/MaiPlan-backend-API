import enum

class SyncAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SYNC = "SYNC"
    SYNC_UPLOAD = "SYNC_UPLOAD"
    SYNC_DOWNLOAD = "SYNC_DOWNLOAD"

class SyncResult(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    ERROR = "ERROR"
    NO_CHANGES = "NO_CHANGES"

class EntityType(str, enum.Enum):
    USER = "USER"
    REMINDER = "REMINDER"
    NOTE = "NOTE"
    LIST = "LIST"
    LIST_ITEM = "LIST_ITEM"
    HEALTH_REMINDER = "HEALTH_REMINDER"
    FINANCE = "FINANCE"
    CATEGORY = "CATEGORY"
    EVENT = "EVENT"