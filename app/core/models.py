from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Interval,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    sync_id = Column(PGUUID(as_uuid=True), nullable=False, default=uuid4)
    email = Column(String(64), unique=True, nullable=False)
    username = Column(String(32), unique=True, nullable=False)
    balance = Column(Numeric(10, 2), default=0.00)
    version = Column(BigInteger, nullable=False, default=1, server_default="1")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    password_hash = Column(Text, nullable=False)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now())
    sync_state = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0)
    server_id = Column(Integer, nullable=True)

    # indexes and other constraints
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_users_version_positive"),
        Index("idx_users_sync_id", "sync_id", unique=True),
        Index("idx_users_deleted_at", "deleted_at"),
        Index("idx_user_last_modified", "last_modified"),
        Index("idx_user_sync_state", "sync_state"),
        Index("idx_user_server_id", "server_id"),
        Index("idx_user_active", "user_id", postgresql_where=text("is_deleted = 0"))
    )

    # relationships to other tables, constraints
    reminders = relationship("Reminder", cascade="all, delete-orphan", back_populates="user")
    notes = relationship("Note", cascade="all, delete-orphan", back_populates="user")
    tasks = relationship("Task", cascade="all, delete-orphan", back_populates="user")
    categories = relationship("Category", cascade="all, delete-orphan", back_populates="user")
    events = relationship("Event",  cascade="all, delete-orphan", back_populates="user")

class Reminder(Base):
    __tablename__ = "reminder"

    reminder_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    sync_id = Column(PGUUID(as_uuid=True), nullable=False, default=uuid4)
    version = Column(BigInteger, nullable=False, default=1, server_default="1")
    reminder_time = Column(DateTime(timezone=True), nullable=False)
    zone_id = Column(String(255), nullable=False, default="UTC", server_default="UTC")
    frequency = Column(Integer, nullable=False, default=0, server_default="0")
    status = Column(Integer, nullable=False, default=1, server_default="1")
    message = Column(Text)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now())
    sync_state = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0)
    server_id = Column(Integer, nullable=True)

    # indexes and other constraints
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_reminder_version_positive"),
        UniqueConstraint("user_id", "sync_id", name="uq_reminder_user_sync_id"),
        Index("idx_reminder_deleted_at", "deleted_at"),
        Index("idx_reminder_user", "user_id"),
        Index("idx_reminder_last_modified", "last_modified"),
        Index("idx_reminder_sync_state", "sync_state"),
        Index("idx_reminder_server_id", "server_id"),
        Index("idx_reminder_active", "reminder_id", postgresql_where=text("is_deleted = 0"))
    )

    # relationships to other tables, constraints
    user = relationship("User", back_populates="reminders")
    event = relationship("Event", back_populates="reminder")
    note = relationship("Note", back_populates="reminder")
    task = relationship("Task", back_populates="reminder")

class Note(Base):
    __tablename__ = "note"

    note_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )

    sync_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        default=uuid4
    )

    version: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=1,
        server_default="1"
    )

    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("category.category_id", ondelete="SET NULL"),
        nullable=True
    )

    reminder_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("reminder.reminder_id", ondelete="SET NULL"),
        nullable=True
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    last_modified: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    sync_state: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    is_deleted: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    server_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false"
    )

    # indexes and other constraints
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_note_version_positive"),
        UniqueConstraint("user_id", "sync_id", name="uq_note_user_sync_id"),
        Index("idx_note_deleted_at", "deleted_at"),
        Index("idx_note_user", "user_id"),
        Index("idx_note_category", "category_id"),
        Index("idx_note_reminder", "reminder_id"),
        Index("idx_note_last_modified", "last_modified"),
        Index("idx_note_sync_state", "sync_state"),
        Index("idx_note_server_id", "server_id"),
        Index("idx_note_active", "note_id", postgresql_where=text("is_deleted = 0"))
    )

    # relationships to other tables, constraints
    user = relationship("User", back_populates="notes")
    category = relationship("Category", back_populates="note")
    reminder = relationship("Reminder", back_populates="note")

class Task(Base):
    __tablename__ = "task"

    task_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )

    sync_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        default=uuid4
    )

    version: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=1,
        server_default="1"
    )

    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("category.category_id", ondelete="SET NULL"),
        nullable=True
    )

    reminder_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("reminder.reminder_id", ondelete="SET NULL"),
        nullable=True
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    status: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    scheduled_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    estimated_time: Mapped[timedelta | None] = mapped_column(
        Interval,
        nullable=True
    )

    completed_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    series_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    occurrence_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    repeat_unit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    repeat_interval: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    repeat_weekdays: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    repeat_end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    repeat_anchor_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    last_modified: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    sync_state: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    is_deleted: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    server_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    # indexes and other constraints
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_task_version_positive"),
        UniqueConstraint("user_id", "sync_id", name="uq_task_user_sync_id"),
        Index("idx_task_deleted_at", "deleted_at"),
        Index("idx_task_user", "user_id"),
        Index("idx_task_category", "category_id"),
        Index("idx_task_reminder", "reminder_id"),
        Index("idx_task_sync_state", "sync_state"),
        Index("idx_task_server_id", "server_id"),
        Index("idx_task_series_occurrence", "series_id", "occurrence_number"),
        Index("idx_task_active", "task_id", postgresql_where=text("is_deleted = 0"))
    )

    # relationships to other tables, constraints
    subtasks = relationship("Subtask", cascade="all, delete-orphan", back_populates="task")
    user = relationship("User", back_populates="tasks")
    category = relationship("Category", back_populates="task")
    reminder = relationship("Reminder", back_populates="task")

class Subtask(Base):
    __tablename__ = "subtask"

    subtask_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )

    sync_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        default=uuid4
    )

    version: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=1,
        server_default="1"
    )

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("task.task_id", ondelete="CASCADE"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    status: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    sort_order: Mapped[int] = mapped_column(
        Integer
    )

    estimated_time: Mapped[timedelta | None] = mapped_column(
        Interval,
        nullable=True
    )

    completed_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    last_modified: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    sync_state: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    is_deleted: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    server_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    # indexes and other constraints
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_subtask_version_positive"),
        UniqueConstraint("user_id", "sync_id", name="uq_subtask_user_sync_id"),
        Index("idx_subtask_deleted_at", "deleted_at"),
        Index("idx_subtask_user", "user_id"),
        Index("idx_subtask_task_id", "task_id"),
        Index("idx_subtask_sync_state", "sync_state"),
        Index("idx_subtask_server_id", "server_id"),
        Index("idx_subtask_active", "task_id", postgresql_where=text("is_deleted = 0"))
    )

    # relationships to other tables, constraints
    task = relationship("Task", back_populates="subtasks")

class Category(Base):
    __tablename__ = "category"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    sync_id = Column(PGUUID(as_uuid=True), nullable=False, default=uuid4)
    version = Column(BigInteger, nullable=False, default=1, server_default="1")
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    color = Column(String(32), nullable=False)
    icon = Column(String(32), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now())
    sync_state = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0)
    server_id = Column(Integer, nullable=True)

    # indexes and other constraints
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_category_version_positive"),
        UniqueConstraint("user_id", "sync_id", name="uq_category_user_sync_id"),
        Index("idx_category_deleted_at", "deleted_at"),
        Index("idx_category_user", "user_id"),
        Index("idx_category_last_modified", "last_modified"),
        Index("idx_category_sync_state", "sync_state"),
        Index("idx_category_server_id", "server_id"),
        Index("idx_category_active", "category_id", postgresql_where=text("is_deleted = 0"))
    )

    # relationships to other tables, constraints
    user = relationship("User", back_populates="categories")
    note = relationship("Note", back_populates="category")
    task = relationship("Task", back_populates="category")
    event = relationship("Event", back_populates="category")

class Event(Base):
    __tablename__ = "event"

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    sync_id = Column(PGUUID(as_uuid=True), nullable=False, default=uuid4)
    version = Column(BigInteger, nullable=False, default=1, server_default="1")
    category_id = Column(Integer, ForeignKey("category.category_id", ondelete="SET NULL"))
    reminder_id = Column(Integer, ForeignKey("reminder.reminder_id", ondelete="SET NULL"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    date = Column(Date, nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    zone_id = Column(String(255), nullable=False, default="UTC", server_default="UTC")
    priority = Column(Integer, nullable=False, default=0, server_default="0")
    location = Column(String(255))
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now())
    sync_state = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0)
    server_id = Column(Integer, nullable=True)

    # indexes and other constraints
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_event_version_positive"),
        UniqueConstraint("user_id", "sync_id", name="uq_event_user_sync_id"),
        Index("idx_event_deleted_at", "deleted_at"),
        Index("idx_event_user", "user_id"),
        Index("idx_event_category", "category_id"),
        Index("idx_event_reminder", "reminder_id"),
        Index("idx_event_date", "date"),
        Index("idx_event_user_date", "user_id", "date"),
        Index("idx_event_last_modified", "last_modified"),
        Index("idx_event_sync_state", "sync_state"),
        Index("idx_event_server_id", "server_id"),
        Index("idx_event_active", "event_id", postgresql_where=text("is_deleted = 0"))
    )

    # relationships to other tables, constraints
    user = relationship("User", back_populates="events")
    reminder = relationship("Reminder", back_populates="event")
    category = relationship("Category", back_populates="event")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    refresh_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_auth_session_user_device", "user_id", "device_id"),
        Index("idx_auth_session_refresh_expires", "refresh_expires_at"),
        Index("idx_auth_session_active", "session_id", postgresql_where=text("revoked_at IS NULL")),
    )


class SyncLog(Base):
    __tablename__ = "sync_log"

    sync_log_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    entity_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    old_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    new_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    result: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    exception_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    exception_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    request_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    response_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    device_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    input_cursor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_cursor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acknowledged_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rejected_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conflict_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    returned_change_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # indexes and other constraints
    __table_args__ = (
        Index("idx_sync_log_user_id", "user_id"),
        Index("idx_sync_log_timestamp", "timestamp"),
        Index("idx_sync_log_result", "result"),
        Index("idx_sync_log_entity", "entity_type", "entity_id"),
        Index("idx_sync_log_request_id", "request_id")
    )


class ProcessedMutation(Base):
    __tablename__ = "processed_mutations"

    processed_mutation_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    mutation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    device_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_sync_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    result_version: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    server_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "mutation_id", name="uq_processed_mutation_user_id"),
        CheckConstraint(
            "operation IN ('CREATE', 'UPDATE', 'DELETE')",
            name="ck_processed_mutation_operation",
        ),
        CheckConstraint(
            "outcome IN ('ACKNOWLEDGED', 'REJECTED', 'CONFLICT')",
            name="ck_processed_mutation_outcome",
        ),
        Index("idx_processed_mutation_entity", "user_id", "entity_type", "entity_sync_id"),
        Index("idx_processed_mutation_processed_at", "processed_at"),
    )


class SyncChangeLog(Base):
    __tablename__ = "sync_change_log"

    sequence: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_sync_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    entity_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    origin_device_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    origin_mutation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint("entity_version > 0", name="ck_sync_change_version_positive"),
        CheckConstraint(
            "operation IN ('CREATE', 'UPDATE', 'DELETE')",
            name="ck_sync_change_operation",
        ),
        Index("idx_sync_change_user_sequence", "user_id", "sequence"),
        Index("idx_sync_change_entity", "user_id", "entity_type", "entity_sync_id"),
        Index("idx_sync_change_changed_at", "changed_at"),
    )
