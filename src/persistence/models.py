from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Book:
    id: int
    title: str
    author: str
    profile_path: str
    start_url: str
    start_chapter_number: int
    last_chapter_number: int
    last_chapter_url: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ChapterRecord:
    id: int
    book_id: int
    number: int
    title: str
    source_url: str
    content_file: str
    next_chapter_url: str | None
    downloaded_at: datetime


@dataclass(frozen=True)
class Job:
    id: int
    book_id: int
    status: str
    from_chapter: int
    target_chapter: int
    current_chapter: int | None
    error: str | None
    started_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True)
class EpubRecord:
    id: int
    book_id: int
    title: str
    author: str
    from_chapter: int
    to_chapter: int
    path: str
    created_at: datetime
