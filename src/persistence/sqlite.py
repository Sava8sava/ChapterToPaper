import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import insert, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine, RowMapping

from src.models.chapter import Chapter
from src.persistence.models import Book, ChapterRecord, EpubRecord, Job
from src.persistence.repositories import (
    BookRepository,
    ChapterRepository,
    EpubRepository,
    JobRepository,
)
from src.persistence.schema import books, chapters, create_sqlite_engine, epubs, jobs


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _book(row: RowMapping) -> Book:
    return Book(**dict(row))


def _chapter(row: RowMapping) -> ChapterRecord:
    return ChapterRecord(**dict(row))


def _job(row: RowMapping) -> Job:
    return Job(**dict(row))


def _epub(row: RowMapping) -> EpubRecord:
    return EpubRecord(**dict(row))


class SQLiteBookRepository(BookRepository):
    def __init__(self, engine: Engine):
        self.engine = engine

    def get_or_create_by_start_url(
        self,
        start_url: str,
        title: str,
        author: str,
        profile_path: str,
        start_number: int = 1,
    ) -> Book:
        if start_number < 1:
            raise ValueError("start_number must be at least 1")

        with self.engine.begin() as connection:
            row = connection.execute(
                select(books).where(books.c.start_url == start_url)
            ).mappings().first()
            if row is None:
                now = _now()
                result = connection.execute(
                    insert(books).values(
                        title=title,
                        author=author,
                        profile_path=profile_path,
                        start_url=start_url,
                        start_chapter_number=start_number,
                        last_chapter_number=start_number - 1,
                        last_chapter_url=None,
                        created_at=now,
                        updated_at=now,
                    )
                )
                row = connection.execute(
                    select(books).where(books.c.id == result.inserted_primary_key[0])
                ).mappings().one()
            else:
                connection.execute(
                    update(books)
                    .where(books.c.id == row["id"])
                    .values(
                        title=title,
                        author=author,
                        profile_path=profile_path,
                        updated_at=_now(),
                    )
                )
                row = connection.execute(
                    select(books).where(books.c.id == row["id"])
                ).mappings().one()
            return _book(row)

    def get_by_id(self, book_id: int) -> Book | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(books).where(books.c.id == book_id)
            ).mappings().first()
        return _book(row) if row else None


class SQLiteChapterRepository(ChapterRepository):
    def __init__(self, engine: Engine, data_dir: str | Path):
        self.engine = engine
        self.data_dir = Path(data_dir).resolve()

    def save(self, book_id: int, chapter: Chapter) -> ChapterRecord:
        chapter_dir = self.data_dir / "books" / str(book_id) / "chapters"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        content_path = chapter_dir / f"{chapter.number:06d}.html"
        relative_path = content_path.relative_to(self.data_dir).as_posix()
        backup_path = content_path.with_suffix(".html.backup")

        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{chapter.number:06d}.", suffix=".tmp", dir=chapter_dir
        )
        temporary_path = Path(temporary_name)
        had_previous_file = content_path.exists()

        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                handle.write(chapter.content_html)
                handle.flush()
                os.fsync(handle.fileno())

            if had_previous_file:
                os.replace(content_path, backup_path)
            os.replace(temporary_path, content_path)

            now = _now()
            statement = sqlite_insert(chapters).values(
                book_id=book_id,
                number=chapter.number,
                title=chapter.title,
                source_url=chapter.source_url,
                content_file=relative_path,
                next_chapter_url=chapter.next_chapter_url,
                downloaded_at=now,
            )
            statement = statement.on_conflict_do_update(
                index_elements=[chapters.c.book_id, chapters.c.number],
                set_={
                    "title": statement.excluded.title,
                    "source_url": statement.excluded.source_url,
                    "content_file": statement.excluded.content_file,
                    "next_chapter_url": statement.excluded.next_chapter_url,
                    "downloaded_at": statement.excluded.downloaded_at,
                },
            )

            with self.engine.begin() as connection:
                connection.execute(statement)
                connection.execute(
                    update(books)
                    .where(
                        books.c.id == book_id,
                        books.c.last_chapter_number < chapter.number,
                    )
                    .values(
                        last_chapter_number=chapter.number,
                        last_chapter_url=chapter.source_url,
                        updated_at=now,
                    )
                )
                row = connection.execute(
                    select(chapters).where(
                        chapters.c.book_id == book_id,
                        chapters.c.number == chapter.number,
                    )
                ).mappings().one()

            backup_path.unlink(missing_ok=True)
            return _chapter(row)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            content_path.unlink(missing_ok=True)
            if had_previous_file and backup_path.exists():
                os.replace(backup_path, content_path)
            raise

    def get(self, book_id: int, number: int) -> ChapterRecord | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(chapters).where(
                    chapters.c.book_id == book_id,
                    chapters.c.number == number,
                )
            ).mappings().first()
        return _chapter(row) if row else None

    def get_range(self, book_id: int, start: int, end: int) -> list[Chapter]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(chapters)
                .where(
                    chapters.c.book_id == book_id,
                    chapters.c.number.between(start, end),
                )
                .order_by(chapters.c.number)
            ).mappings().all()

        result = []
        for row in rows:
            record = _chapter(row)
            content_path = (self.data_dir / record.content_file).resolve()
            if not content_path.is_relative_to(self.data_dir):
                raise RuntimeError(f"Unsafe chapter cache path: {record.content_file}")
            try:
                content = content_path.read_text(encoding="utf-8")
            except OSError as error:
                raise RuntimeError(
                    f"Chapter {record.number} cache is unavailable: {content_path}"
                ) from error
            result.append(
                Chapter(
                    number=record.number,
                    title=record.title,
                    content_html=content,
                    source_url=record.source_url,
                    next_chapter_url=record.next_chapter_url,
                )
            )
        return result


class SQLiteJobRepository(JobRepository):
    def __init__(self, engine: Engine):
        self.engine = engine

    def interrupt_running(self, book_id: int) -> None:
        with self.engine.begin() as connection:
            running_jobs = connection.execute(
                select(jobs.c.id, jobs.c.current_chapter).where(
                    jobs.c.book_id == book_id,
                    jobs.c.status == "running",
                )
            ).mappings().all()
            for running_job in running_jobs:
                status = (
                    "partial"
                    if running_job["current_chapter"] is not None
                    else "failed"
                )
                connection.execute(
                    update(jobs)
                    .where(jobs.c.id == running_job["id"])
                    .values(
                        status=status,
                        error="Execução interrompida antes da conclusão.",
                        finished_at=_now(),
                    )
                )

    def create(self, book_id: int, start: int, target: int) -> Job:
        with self.engine.begin() as connection:
            result = connection.execute(
                insert(jobs).values(
                    book_id=book_id,
                    status="running",
                    from_chapter=start,
                    target_chapter=target,
                    current_chapter=None,
                    error=None,
                    started_at=_now(),
                    finished_at=None,
                )
            )
            row = connection.execute(
                select(jobs).where(jobs.c.id == result.inserted_primary_key[0])
            ).mappings().one()
        return _job(row)

    def update_progress(self, job_id: int, current_chapter: int) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                update(jobs)
                .where(jobs.c.id == job_id)
                .values(current_chapter=current_chapter)
            )

    def finish(self, job_id: int, status: str, error: str | None = None) -> Job:
        if status not in {"done", "failed", "partial"}:
            raise ValueError(f"Invalid final job status: {status}")
        with self.engine.begin() as connection:
            connection.execute(
                update(jobs)
                .where(jobs.c.id == job_id)
                .values(status=status, error=error, finished_at=_now())
            )
            row = connection.execute(
                select(jobs).where(jobs.c.id == job_id)
            ).mappings().one()
        return _job(row)


class SQLiteEpubRepository(EpubRepository):
    def __init__(self, engine: Engine):
        self.engine = engine

    def record(
        self,
        book_id: int,
        title: str,
        author: str,
        start: int,
        end: int,
        path: str,
    ) -> EpubRecord:
        with self.engine.begin() as connection:
            result = connection.execute(
                insert(epubs).values(
                    book_id=book_id,
                    title=title,
                    author=author,
                    from_chapter=start,
                    to_chapter=end,
                    path=str(Path(path).resolve()),
                    created_at=_now(),
                )
            )
            row = connection.execute(
                select(epubs).where(epubs.c.id == result.inserted_primary_key[0])
            ).mappings().one()
        return _epub(row)


class SQLitePersistence:
    def __init__(self, data_dir: str | Path = "data"):
        self.data_dir = Path(data_dir).resolve()
        self.engine = create_sqlite_engine(self.data_dir / "db.sqlite3")
        self.books = SQLiteBookRepository(self.engine)
        self.chapters = SQLiteChapterRepository(self.engine, self.data_dir)
        self.jobs = SQLiteJobRepository(self.engine)
        self.epubs = SQLiteEpubRepository(self.engine)

    def close(self) -> None:
        self.engine.dispose()
