from sqlalchemy import Column, Integer, Numeric, String, Text, DateTime, Date, Time, Boolean, ForeignKey, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "user"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(64), unique=True, nullable=False)
    username = Column(String(32), unique=True, nullable=False)
    balance = Column(Numeric(10, 2), default=0.00)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    password_hash = Column(Text, nullable=False)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now())
    sync_state = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0)
    server_id = Column(Integer, nullable=True)

    # relationships to other tables, constraints
    reminders = relationship("Reminder", cascade="all, delete-orphan", back_populates="user")
    notes = relationship("Note", cascade="all, delete-orphan", back_populates="user")
    lists = relationship("List", cascade="all, delete-orphan", back_populates="user")
    health_reminders = relationship("HealthReminder", cascade="all, delete-orphan", back_populates="user")
    finances = relationship("Finance", cascade="all, delete-orphan", back_populates="user")
    categories = relationship("Category", cascade="all, delete-orphan", back_populates="user")
    events = relationship("Event",  cascade="all, delete-orphan", back_populates="user")

class Reminder(Base):
    __tablename__ = "reminder"

    reminder_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False)
    reminder_time = Column(DateTime, nullable=False)
    frequency = Column(Integer, default=0)
    status = Column(Integer, default=1)
    message = Column(Text)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now())
    sync_state = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0)
    server_id = Column(Integer, nullable=True)

    # indexes and other constraints
    __table_arg__ = (
        Index("idx_reminder_user", "user_id")
    )

    # relationships to other tables, constraints
    user = relationship("User", back_populates="reminders")
    finance = relationship("Finance", back_populates="reminder")
    event = relationship("Event", back_populates="reminder")
    note = relationship("Note", back_populates="reminder")

class Note(Base):
    __tablename__ = "note"

    note_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("category.category_id", ondelete="SET NULL"))
    reminder_id = Column(Integer, ForeignKey("reminder.reminder_id", ondelete="SET NULL"))
    title = Column(String(255), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now())
    sync_state = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0)
    server_id = Column(Integer, nullable=True)

    # indexes and other constraints
    __table_args__ = (
        Index("idx_note_user", "user_id"),
        Index("idx_note_category", "category_id"),
        Index("idx_note_reminder", "reminder_id")
    )

    # relationships to other tables, constraints
    user = relationship("User", back_populates="notes")
    category = relationship("Category", back_populates="note")
    reminder = relationship("Reminder", back_populates="note")

class List(Base):
    __tablename__ = "list"
    
    list_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now())
    sync_state = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0)
    server_id = Column(Integer, nullable=True)

    # indexes and other constraints
    __table_args__ = (
        UniqueConstraint("user_id", "title", name="uq_list_title"),
        Index("idx_list_user", "user_id")
    )

    # relationships to other tables, constraints
    user = relationship("User", back_populates="lists")
    list_items = relationship("ListItem", cascade="all, delete-orphan", back_populates="list")

class ListItem(Base):
    __tablename__ = "list_item"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    list_id = Column(Integer, ForeignKey("list.list_id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    quantity = Column(Integer)
    status = Column(Boolean, default=False)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now())
    sync_state = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0)
    server_id = Column(Integer, nullable=True)

    # indexes and other constraints
    __table_args__ = (
        UniqueConstraint("list_id", "name", name="uq_item_name"),
        Index("idx_list_item", "list_id")
    )

    # relationships to other tables, constraints
    list = relationship("List", back_populates="list_items")

class HealthReminder(Base):
    __tablename__ = "health_reminder"

    reminder_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False)
    type = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    frequency = Column(Integer, nullable=False)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now())
    sync_state = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0)
    server_id = Column(Integer, nullable=True)

    # indexes and other constraints
    __table_args__ = (
        CheckConstraint("type = ANY (ARRAY[1, 2, 3])", name="ck_type"),
        Index("idx_health_reminder_user", "user_id")
    )

    # relationships to other tables, constraints
    user = relationship("User", back_populates="health_reminders")

class Finance(Base):
    __tablename__ = "finance"

    finance_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("category.category_id", ondelete="SET NULL"))
    reminder_id = Column(Integer, ForeignKey("reminder.reminder_id", ondelete="SET NULL"))
    type = Column(Boolean, nullable=False)
    expense_amount = Column(Numeric(10, 2), nullable=False)
    expense_date = Column(DateTime)
    description = Column(Text)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now())
    sync_state = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0)
    server_id = Column(Integer, nullable=True)

    # indexes and other constraints
    __table_args__ = (
        Index("idx_finance_user", "user_id"),
        Index("idx_finance_category", "category_id"),
        Index("idx_finance_reminder", "reminder_id"),
        Index("idx_finance_type", "type"),
        Index("idx_finance_expense_date", "expense_date"),
        Index("idx_finance_user_date", "user_id", "expense_date")
    )

    # relationships to other tables, constraints
    user = relationship("User", back_populates="finances")
    reminder = relationship("Reminder", back_populates="finance")
    category = relationship("Category", back_populates="finance")

class Category(Base):
    __tablename__ = "category"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    color = Column(String(32), nullable=False)
    icon = Column(String(32), nullable=False)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now())
    sync_state = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0)
    server_id = Column(Integer, nullable=True)

    # indexes and other constraints
    __table_arg__ = (
        Index("idx_category_user", "user_id")
    )

    # relationships to other tables, constraints
    user = relationship("User", back_populates="categories")
    note = relationship("Note", back_populates="category")
    event = relationship("Event", back_populates="category")
    finance = relationship("Finance", back_populates="category")

class Event(Base):
    __tablename__ = "event"

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("category.category_id", ondelete="SET NULL"))
    reminder_id = Column(Integer, ForeignKey("reminder.reminder_id", ondelete="SET NULL"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    date = Column(Date, nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    priority = Column(Integer, default=0)
    location = Column(String(255))
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now())
    sync_state = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0)
    server_id = Column(Integer, nullable=True)

    # indexes and other constraints
    __table_args__ = (
        Index("idx_event_user", "user_id"),
        Index("idx_event_category", "category_id"),
        Index("idx_event_reminder", "reminder_id"),
        Index("idx_event_date", "date"),
        Index("idx_event_user_date", "user_id", "date")
    )

    # relationships to other tables, constraints
    user = relationship("User", back_populates="events")
    reminder = relationship("Reminder", back_populates="event")
    category = relationship("Category", back_populates="event")
