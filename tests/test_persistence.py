import tempfile
import unittest
from pathlib import Path

from sqlalchemy import select

from src.fetcher.base_fetcher import BaseFetcher
from src.models.chapter import Chapter
from src.orchestrator import WebnovelOrchestrator
from src.persistence.schema import epubs, jobs
from src.persistence.sqlite import SQLitePersistence
from src.storage.storage import StorageService


PROFILE_PATH = "config/sites/allnovel.json"


def chapter_html(number: int, next_number: int | None) -> str:
    next_link = (
        f'<a id="next_chap" href="/{next_number}">Next</a>'
        if next_number is not None
        else ""
    )
    return (
        "<html><body>"
        f'<h1 class="chapter-title">Chapter {number}</h1>'
        f'<div id="chapter-content"><p>{"content " * 20}</p></div>'
        f"{next_link}</body></html>"
    )


class FakeFetcher(BaseFetcher):
    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.calls: list[str] = []

    def fetch(self, url: str) -> str:
        self.calls.append(url)
        if url not in self.pages:
            raise RuntimeError(f"No fixture for {url}")
        return self.pages[url]


class PersistenceIntegrationTests(unittest.TestCase):
    def test_partial_run_resumes_from_persisted_next_url(self):
        with tempfile.TemporaryDirectory() as directory:
            persistence = SQLitePersistence(directory)
            first_fetcher = FakeFetcher(
                {"https://example.test/1": chapter_html(1, 2)}
            )
            first_run = WebnovelOrchestrator(
                PROFILE_PATH,
                persistence=persistence,
                fetcher=first_fetcher,
                jitter_range=(0, 0),
            )

            partial_epub = first_run.run(
                "https://example.test/1", "Example", "Author", max_chapters=2
            )

            self.assertEqual(first_run.last_run_status, "partial")
            self.assertTrue(Path(partial_epub).is_file())
            book = persistence.books.get_or_create_by_start_url(
                "https://example.test/1", "Example", "Author", PROFILE_PATH
            )
            self.assertEqual(book.last_chapter_number, 1)
            self.assertTrue(
                (Path(directory) / "books" / str(book.id) / "chapters" / "000001.html").is_file()
            )

            resumed_persistence = SQLitePersistence(directory)
            resumed_fetcher = FakeFetcher(
                {
                    "https://example.test/2": chapter_html(2, 3),
                    "https://example.test/3": chapter_html(3, None),
                }
            )
            resumed_run = WebnovelOrchestrator(
                PROFILE_PATH,
                persistence=resumed_persistence,
                fetcher=resumed_fetcher,
                jitter_range=(0, 0),
            )
            completed_epub = resumed_run.run(
                "https://example.test/1", "Example", "Author", max_chapters=2
            )

            self.assertEqual(resumed_run.last_run_status, "done")
            self.assertEqual(
                resumed_fetcher.calls,
                ["https://example.test/2", "https://example.test/3"],
            )
            self.assertTrue(Path(completed_epub).is_file())
            resumed_book = resumed_persistence.books.get_by_id(book.id)
            self.assertEqual(resumed_book.last_chapter_number, 3)

            rebuilt_epub = resumed_run.rebuild_epub(book.id, 1, 3)
            self.assertTrue(Path(rebuilt_epub).is_file())
            self.assertEqual(
                resumed_fetcher.calls,
                ["https://example.test/2", "https://example.test/3"],
            )

            with resumed_persistence.engine.connect() as connection:
                job_statuses = connection.execute(
                    select(jobs.c.status).order_by(jobs.c.id)
                ).scalars().all()
                epub_count = len(connection.execute(select(epubs.c.id)).all())
            self.assertEqual(job_statuses, ["partial", "done", "done"])
            self.assertEqual(epub_count, 3)
            persistence.close()
            resumed_persistence.close()

    def test_non_default_start_number_is_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            persistence = SQLitePersistence(directory)
            fetcher = FakeFetcher(
                {"https://example.test/50": chapter_html(50, None)}
            )
            orchestrator = WebnovelOrchestrator(
                PROFILE_PATH,
                persistence=persistence,
                fetcher=fetcher,
                jitter_range=(0, 0),
            )

            orchestrator.run(
                "https://example.test/50",
                "Example",
                "Author",
                max_chapters=1,
                start_number=50,
            )

            book = persistence.books.get_or_create_by_start_url(
                "https://example.test/50",
                "Example",
                "Author",
                PROFILE_PATH,
            )
            self.assertEqual(book.start_chapter_number, 50)
            self.assertEqual(book.last_chapter_number, 50)
            persistence.close()

    def test_failed_checkpoint_removes_new_cache_file(self):
        with tempfile.TemporaryDirectory() as directory:
            persistence = SQLitePersistence(directory)
            chapter = Chapter(
                number=1,
                title="Chapter 1",
                content_html="<p>content</p>",
                source_url="https://example.test/1",
                next_chapter_url=None,
            )

            with self.assertRaises(Exception):
                persistence.chapters.save(999, chapter)

            cache_file = Path(directory) / "books" / "999" / "chapters" / "000001.html"
            self.assertFalse(cache_file.exists())
            persistence.close()

    def test_final_epub_path_is_safe_and_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = StorageService(directory)
            try:
                output = storage.save_final_epub(
                    "../../Unsafe Book",
                    lambda path: Path(path).write_bytes(b"epub data"),
                )
            finally:
                storage.cleanup()

            output_path = Path(output)
            self.assertEqual(output_path.parent, Path(directory).resolve())
            self.assertEqual(output_path.name, "unsafe_book.epub")
            self.assertEqual(output_path.read_bytes(), b"epub data")
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_running_jobs_are_marked_interrupted(self):
        with tempfile.TemporaryDirectory() as directory:
            persistence = SQLitePersistence(directory)
            book = persistence.books.get_or_create_by_start_url(
                "https://example.test/1", "Example", "Author", PROFILE_PATH
            )
            interrupted = persistence.jobs.create(book.id, 1, 3)
            persistence.jobs.update_progress(interrupted.id, 1)

            persistence.jobs.interrupt_running(book.id)

            with persistence.engine.connect() as connection:
                row = connection.execute(
                    select(jobs).where(jobs.c.id == interrupted.id)
                ).mappings().one()
            self.assertEqual(row["status"], "partial")
            self.assertIsNotNone(row["finished_at"])
            persistence.close()


if __name__ == "__main__":
    unittest.main()
