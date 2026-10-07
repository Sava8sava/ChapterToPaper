from pathlib import Path

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine


metadata = MetaData()

books = Table(
    "books",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(500), nullable=False),
    Column("author", String(500), nullable=False),
    Column("profile_path", Text, nullable=False),
    Column("start_url", Text, nullable=False, unique=True),
    Column("start_chapter_number", Integer, nullable=False),
    Column("last_chapter_number", Integer, nullable=False),
    Column("last_chapter_url", Text),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    CheckConstraint("last_chapter_number >= 0", name="ck_books_last_chapter"),
    CheckConstraint("start_chapter_number > 0", name="ck_books_start_chapter"),
)

chapters = Table(
    "chapters",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("book_id", ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
    Column("number", Integer, nullable=False),
    Column("title", String(1000), nullable=False),
    Column("source_url", Text, nullable=False),
    Column("content_file", Text, nullable=False),
    Column("next_chapter_url", Text),
    Column("downloaded_at", DateTime, nullable=False),
    UniqueConstraint("book_id", "number", name="uq_chapters_book_number"),
    CheckConstraint("number > 0", name="ck_chapters_number"),
)

jobs = Table(
    "jobs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("book_id", ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
    Column("status", String(20), nullable=False),
    Column("from_chapter", Integer, nullable=False),
    Column("target_chapter", Integer, nullable=False),
    Column("current_chapter", Integer),
    Column("error", Text),
    Column("started_at", DateTime, nullable=False),
    Column("finished_at", DateTime),
    CheckConstraint(
        "status IN ('running', 'done', 'failed', 'partial')",
        name="ck_jobs_status",
    ),
)

epubs = Table(
    "epubs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("book_id", ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
    Column("title", String(500), nullable=False),
    Column("author", String(500), nullable=False),
    Column("from_chapter", Integer, nullable=False),
    Column("to_chapter", Integer, nullable=False),
    Column("path", Text, nullable=False),
    Column("created_at", DateTime, nullable=False),
)

Index("ix_jobs_book_started", jobs.c.book_id, jobs.c.started_at)
Index("ix_epubs_book_created", epubs.c.book_id, epubs.c.created_at)


def create_sqlite_engine(database_path: str | Path) -> Engine:
    path = Path(database_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    metadata.create_all(engine)
    return engine
