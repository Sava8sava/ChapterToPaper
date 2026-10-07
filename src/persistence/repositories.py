from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol

from src.models.chapter import Chapter
from src.persistence.models import Book, ChapterRecord, EpubRecord, Job


class BookRepository(ABC):
    @abstractmethod
    def get_or_create_by_start_url(
        self,
        start_url: str,
        title: str,
        author: str,
        profile_path: str,
        start_number: int = 1,
    ) -> Book:
        pass

    @abstractmethod
    def get_by_id(self, book_id: int) -> Book | None:
        pass


class ChapterRepository(ABC):
    @abstractmethod
    def save(self, book_id: int, chapter: Chapter) -> ChapterRecord:
        """Persist a chapter and advance the book bookmark as one checkpoint."""
        pass

    @abstractmethod
    def get(self, book_id: int, number: int) -> ChapterRecord | None:
        pass

    @abstractmethod
    def get_range(self, book_id: int, start: int, end: int) -> list[Chapter]:
        pass


class JobRepository(ABC):
    @abstractmethod
    def interrupt_running(self, book_id: int) -> None:
        pass

    @abstractmethod
    def create(self, book_id: int, start: int, target: int) -> Job:
        pass

    @abstractmethod
    def update_progress(self, job_id: int, current_chapter: int) -> None:
        pass

    @abstractmethod
    def finish(self, job_id: int, status: str, error: str | None = None) -> Job:
        pass


class EpubRepository(ABC):
    @abstractmethod
    def record(
        self,
        book_id: int,
        title: str,
        author: str,
        start: int,
        end: int,
        path: str,
    ) -> EpubRecord:
        pass


class Persistence(Protocol):
    data_dir: Path
    books: BookRepository
    chapters: ChapterRepository
    jobs: JobRepository
    epubs: EpubRepository
