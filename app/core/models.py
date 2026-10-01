from datetime import date, datetime, time, timedelta
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Interval,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

TIDE_ENTITY_TYPES = "'user', 'category', 'reminder', 'event', 'note', 'task', 'subtask'"


class Base(DeclarativeBase):
    pass


class TideEntityMixin:
    sync_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    version: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=1,
        server_default="1",
    )
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class User(TideEntityMixin, Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(64), nullable=False)
    username: Mapped[str] = mapped_column(String(32), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("sync_id", name="uq_users_sync_id"),
        CheckConstraint("version > 0", name="ck_users_version_positive"),
        CheckConstraint("length(btrim(email)) > 0", name="ck_users_email_not_blank"),
        CheckConstraint(
            "length(btrim(username)) > 0",
            name="ck_users_username_not_blank",
        ),
        CheckConstraint(
            "length(btrim(password_hash)) > 0",
            name="ck_users_password_hash_not_blank",
        ),
        Index("idx_users_deleted_at", "deleted_at"),
        Index(
            "idx_users_active",
            "user_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class Category(TideEntityMixin, Base):
    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(String(32), nullable=False)
    icon: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "sync_id", name="uq_categories_user_sync_id"),
        CheckConstraint("version > 0", name="ck_categories_version_positive"),
        CheckConstraint("length(btrim(name)) > 0", name="ck_categories_name_not_blank"),
        CheckConstraint(
            "length(btrim(description)) > 0",
            name="ck_categories_description_not_blank",
        ),
        CheckConstraint("length(btrim(color)) > 0", name="ck_categories_color_not_blank"),
        CheckConstraint("length(btrim(icon)) > 0", name="ck_categories_icon_not_blank"),
        Index("idx_categories_user", "user_id"),
        Index("idx_categories_deleted_at", "deleted_at"),
        Index(
            "idx_categories_active",
            "user_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class Reminder(TideEntityMixin, Base):
    __tablename__ = "reminders"

    reminder_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    reminder_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    zone_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="UTC",
        server_default="UTC",
    )
    frequency: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "sync_id", name="uq_reminders_user_sync_id"),
        CheckConstraint("version > 0", name="ck_reminders_version_positive"),
        CheckConstraint(
            "length(btrim(zone_id)) > 0",
            name="ck_reminders_zone_not_blank",
        ),
        Index("idx_reminders_user", "user_id"),
        Index("idx_reminders_deleted_at", "deleted_at"),
        Index(
            "idx_reminders_active",
            "user_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class Task(TideEntityMixin, Base):
    __tablename__ = "tasks"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.category_id", ondelete="SET NULL"),
        nullable=True,
    )
    reminder_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("reminders.reminder_id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_time: Mapped[timedelta | None] = mapped_column(Interval, nullable=True)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    series_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurrence_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repeat_unit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repeat_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repeat_weekdays: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repeat_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    repeat_anchor_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "sync_id", name="uq_tasks_user_sync_id"),
        CheckConstraint("version > 0", name="ck_tasks_version_positive"),
        CheckConstraint("length(btrim(title)) > 0", name="ck_tasks_title_not_blank"),
        CheckConstraint(
            "estimated_time IS NULL OR estimated_time >= INTERVAL '0 seconds'",
            name="ck_tasks_estimated_time_nonnegative",
        ),
        CheckConstraint(
            "occurrence_number IS NULL OR occurrence_number >= 0",
            name="ck_tasks_occurrence_nonnegative",
        ),
        CheckConstraint(
            "repeat_interval IS NULL OR repeat_interval > 0",
            name="ck_tasks_repeat_interval_positive",
        ),
        CheckConstraint(
            "repeat_weekdays IS NULL OR repeat_weekdays >= 0",
            name="ck_tasks_repeat_weekdays_nonnegative",
        ),
        Index("idx_tasks_user", "user_id"),
        Index("idx_tasks_category", "category_id"),
        Index("idx_tasks_reminder", "reminder_id"),
        Index("idx_tasks_deleted_at", "deleted_at"),
        Index("idx_tasks_series_occurrence", "series_id", "occurrence_number"),
        Index(
            "idx_tasks_active",
            "user_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class Subtask(TideEntityMixin, Base):
    __tablename__ = "subtasks"

    subtask_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tasks.task_id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_time: Mapped[timedelta | None] = mapped_column(Interval, nullable=True)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "sync_id", name="uq_subtasks_user_sync_id"),
        CheckConstraint("version > 0", name="ck_subtasks_version_positive"),
        CheckConstraint("length(btrim(title)) > 0", name="ck_subtasks_title_not_blank"),
        CheckConstraint(
            "estimated_time IS NULL OR estimated_time >= INTERVAL '0 seconds'",
            name="ck_subtasks_estimated_time_nonnegative",
        ),
        Index("idx_subtasks_user", "user_id"),
        Index("idx_subtasks_task", "task_id"),
        Index("idx_subtasks_deleted_at", "deleted_at"),
        Index(
            "idx_subtasks_active",
            "user_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class Note(TideEntityMixin, Base):
    __tablename__ = "notes"

    note_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.category_id", ondelete="SET NULL"),
        nullable=True,
    )
    reminder_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("reminders.reminder_id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "sync_id", name="uq_notes_user_sync_id"),
        CheckConstraint("version > 0", name="ck_notes_version_positive"),
        CheckConstraint("length(btrim(title)) > 0", name="ck_notes_title_not_blank"),
        Index("idx_notes_user", "user_id"),
        Index("idx_notes_category", "category_id"),
        Index("idx_notes_reminder", "reminder_id"),
        Index("idx_notes_deleted_at", "deleted_at"),
        Index(
            "idx_notes_active",
            "user_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class Event(TideEntityMixin, Base):
    __tablename__ = "events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.category_id", ondelete="SET NULL"),
        nullable=True,
    )
    reminder_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("reminders.reminder_id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    recurrence_frequency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    recurrence_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recurrence_weekdays: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recurrence_monthly_mode: Mapped[str | None] = mapped_column(
        String(24), nullable=True
    )
    recurrence_until_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reminder_offset_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reminder_lead_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reminder_minute_of_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    relative_reminder_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    zone_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="UTC",
        server_default="UTC",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "sync_id", name="uq_events_user_sync_id"),
        CheckConstraint("version > 0", name="ck_events_version_positive"),
        CheckConstraint("length(btrim(title)) > 0", name="ck_events_title_not_blank"),
        CheckConstraint("length(btrim(zone_id)) > 0", name="ck_events_zone_not_blank"),
        CheckConstraint("end_date >= start_date", name="ck_events_start_date_range"),
        CheckConstraint("(start_time IS NULL) = (end_time IS NULL)", name="ck_events_time_pair"),
        CheckConstraint(
            "reminder_offset_minutes IS NULL OR "
            "(start_time IS NOT NULL AND reminder_offset_minutes BETWEEN 0 AND 10080)",
            name="ck_events_timed_reminder",
        ),
        CheckConstraint(
            "(reminder_lead_days IS NULL AND reminder_minute_of_day IS NULL) OR "
            "(start_time IS NULL AND reminder_lead_days IS NOT NULL AND "
            "reminder_minute_of_day IS NOT NULL AND reminder_lead_days BETWEEN 0 AND 7 AND "
            "reminder_minute_of_day BETWEEN 0 AND 1439)",
            name="ck_events_date_reminder",
        ),
        CheckConstraint(
            "num_nonnulls(reminder_id, reminder_offset_minutes, reminder_lead_days) <= 1",
            name="ck_events_one_reminder_mode",
        ),
        CheckConstraint(
            "recurrence_frequency IS NULL OR reminder_id IS NULL",
            name="ck_events_absolute_only_one_off",
        ),
        CheckConstraint(
            "relative_reminder_message IS NULL OR reminder_offset_minutes IS NOT NULL "
            "OR reminder_lead_days IS NOT NULL",
            name="ck_events_relative_message",
        ),
        CheckConstraint(
            "COALESCE(("
            "(recurrence_frequency IS NULL AND recurrence_interval IS NULL AND "
            "recurrence_weekdays IS NULL AND recurrence_monthly_mode IS NULL AND "
            "recurrence_until_date IS NULL) OR "
            "(recurrence_frequency = 'DAILY' AND recurrence_interval BETWEEN 1 AND 365 "
            "AND recurrence_weekdays IS NULL AND recurrence_monthly_mode IS NULL) OR "
            "(recurrence_frequency = 'WEEKLY' AND recurrence_interval BETWEEN 1 AND 52 "
            "AND recurrence_weekdays BETWEEN 1 AND 127 AND recurrence_monthly_mode IS NULL) OR "
            "(recurrence_frequency = 'MONTHLY' AND recurrence_interval BETWEEN 1 AND 24 "
            "AND recurrence_weekdays IS NULL AND recurrence_monthly_mode IN "
            "('DAY_OF_MONTH', 'LAST_DAY', 'NTH_WEEKDAY', 'LAST_WEEKDAY'))"
            "), FALSE)",
            name="ck_events_recurrence_shape",
        ),
        CheckConstraint(
            "recurrence_until_date IS NULL OR recurrence_until_date >= start_date",
            name="ck_events_recurrence_until",
        ),
        CheckConstraint(
            "recurrence_monthly_mode IS NULL OR recurrence_monthly_mode IN "
            "('DAY_OF_MONTH', 'NTH_WEEKDAY') OR "
            "(recurrence_monthly_mode = 'LAST_DAY' AND start_date = "
            "(date_trunc('month', start_date::timestamp) + interval '1 month - 1 day')::date) OR "
            "(recurrence_monthly_mode = 'LAST_WEEKDAY' AND "
            "extract(month from start_date + 7) <> extract(month from start_date))",
            name="ck_events_monthly_anchor",
        ),
        Index("idx_events_user", "user_id"),
        Index("idx_events_category", "category_id"),
        Index("idx_events_reminder", "reminder_id"),
        Index("idx_events_start_date", "start_date"),
        Index("idx_events_user_start_date", "user_id", "start_date"),
        Index("idx_events_deleted_at", "deleted_at"),
        Index(
            "idx_events_active",
            "user_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
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
        UniqueConstraint(
            "refresh_token_hash",
            name="uq_auth_sessions_refresh_token_hash",
        ),
        CheckConstraint(
            "refresh_token_hash ~ '^[0-9a-f]{64}$'",
            name="ck_auth_sessions_refresh_hash",
        ),
        CheckConstraint(
            "refresh_expires_at > created_at",
            name="ck_auth_sessions_refresh_after_creation",
        ),
        Index("idx_auth_sessions_user_device", "user_id", "device_id"),
        Index("idx_auth_sessions_refresh_expires", "refresh_expires_at"),
        Index(
            "idx_auth_sessions_active",
            "session_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
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
        UniqueConstraint(
            "user_id",
            "mutation_id",
            name="uq_processed_mutations_user_mutation",
        ),
        CheckConstraint(
            "operation IN ('CREATE', 'UPDATE', 'DELETE')",
            name="ck_processed_mutations_operation",
        ),
        CheckConstraint(
            "outcome IN ('ACKNOWLEDGED', 'REJECTED', 'CONFLICT')",
            name="ck_processed_mutations_outcome",
        ),
        CheckConstraint(
            f"entity_type IN ({TIDE_ENTITY_TYPES})",
            name="ck_processed_mutations_entity_type",
        ),
        CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_processed_mutations_request_hash",
        ),
        CheckConstraint(
            "result_version IS NULL OR result_version > 0",
            name="ck_processed_mutations_result_version_positive",
        ),
        CheckConstraint(
            "(outcome = 'ACKNOWLEDGED' AND result_version IS NOT NULL "
            "AND error_code IS NULL) OR "
            "(outcome = 'CONFLICT' AND result_version IS NOT NULL "
            "AND error_code = 'VERSION_CONFLICT') OR "
            "(outcome = 'REJECTED' AND result_version IS NULL "
            "AND error_code IS NOT NULL)",
            name="ck_processed_mutations_outcome_shape",
        ),
        Index(
            "idx_processed_mutations_entity",
            "user_id",
            "entity_type",
            "entity_sync_id",
        ),
        Index("idx_processed_mutations_processed_at", "processed_at"),
    )


class SyncChangeLog(Base):
    __tablename__ = "sync_change_log"

    sequence: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
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
        CheckConstraint(
            "entity_version > 0",
            name="ck_sync_change_log_version_positive",
        ),
        CheckConstraint(
            "operation IN ('CREATE', 'UPDATE', 'DELETE')",
            name="ck_sync_change_log_operation",
        ),
        CheckConstraint(
            f"entity_type IN ({TIDE_ENTITY_TYPES})",
            name="ck_sync_change_log_entity_type",
        ),
        CheckConstraint(
            "(operation = 'DELETE' AND data IS NULL) OR "
            "(operation IN ('CREATE', 'UPDATE') AND data IS NOT NULL)",
            name="ck_sync_change_log_data_shape",
        ),
        Index("idx_sync_change_log_user_sequence", "user_id", "sequence"),
        Index(
            "idx_sync_change_log_entity",
            "user_id",
            "entity_type",
            "entity_sync_id",
        ),
        Index("idx_sync_change_log_changed_at", "changed_at"),
    )


class SyncLog(Base):
    __tablename__ = "sync_log"

    sync_log_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    request_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    response_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    device_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    input_cursor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_cursor: Mapped[str] = mapped_column(String(255), nullable=False)
    received_count: Mapped[int] = mapped_column(Integer, nullable=False)
    acknowledged_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    conflict_count: Mapped[int] = mapped_column(Integer, nullable=False)
    returned_change_count: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint("received_count >= 0", name="ck_sync_log_received_nonnegative"),
        CheckConstraint(
            "acknowledged_count >= 0",
            name="ck_sync_log_acknowledged_nonnegative",
        ),
        CheckConstraint("rejected_count >= 0", name="ck_sync_log_rejected_nonnegative"),
        CheckConstraint("conflict_count >= 0", name="ck_sync_log_conflict_nonnegative"),
        CheckConstraint(
            "returned_change_count >= 0",
            name="ck_sync_log_returned_nonnegative",
        ),
        CheckConstraint(
            "acknowledged_count + rejected_count + conflict_count = received_count",
            name="ck_sync_log_outcome_counts_match",
        ),
        CheckConstraint("result IN ('SUCCESS', 'FAILURE')", name="ck_sync_log_result"),
        Index("idx_sync_log_user_completed", "user_id", "completed_at"),
        Index("idx_sync_log_request", "request_id"),
    )
