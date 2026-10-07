import logging
import random
import time
from pathlib import Path

from src.epub_builder.builder import EpubBuilder
from src.fetcher.base_fetcher import BaseFetcher
from src.fetcher.playwright_fetcher import PlaywrightFetcher
from src.models.site_profile import SiteProfile
from src.parser.config_parser import ConfigParser
from src.persistence.repositories import Persistence
from src.persistence.sqlite import SQLitePersistence
from src.storage.storage import StorageService

logger = logging.getLogger("WebnovelToKindle.Orchestrator")


class WebnovelOrchestrator:
    def __init__(
        self,
        json_profile_path: str,
        persistence: Persistence | None = None,
        fetcher: BaseFetcher | None = None,
        parser: ConfigParser | None = None,
        jitter_range: tuple[float, float] = (4.0, 8.0),
    ):
        self.profile_path = str(Path(json_profile_path).resolve())
        self.profile = SiteProfile.from_json(json_profile_path)
        self.persistence = persistence or SQLitePersistence()
        self.fetcher = fetcher or PlaywrightFetcher()
        self.parser = parser or ConfigParser()
        self.jitter_range = jitter_range
        self.last_job_id: int | None = None
        self.last_run_status: str | None = None

    def run(
        self,
        start_url: str,
        book_title: str,
        author: str,
        max_chapters: int = 100,
        start_number: int = 1,
        book_id: int | None = None,
    ) -> str:
        """Download additional chapters, checkpointing each one before continuing."""
        if max_chapters < 1:
            raise ValueError("max_chapters must be at least 1")
        if start_number < 1:
            raise ValueError("start_number must be at least 1")

        if book_id is None:
            book = self.persistence.books.get_or_create_by_start_url(
                start_url=start_url,
                title=book_title,
                author=author,
                profile_path=self.profile_path,
                start_number=start_number,
            )
        else:
            book = self.persistence.books.get_by_id(book_id)
            if book is None:
                raise ValueError(f"Book {book_id} was not found")

        chapter_number = book.last_chapter_number + 1
        first_chapter = chapter_number
        target_chapter = first_chapter + max_chapters - 1
        self.persistence.jobs.interrupt_running(book.id)
        current_url = self._resume_url(
            book.id,
            book.start_url,
            book.last_chapter_number,
            book.start_chapter_number,
        )
        job = self.persistence.jobs.create(book.id, first_chapter, target_chapter)
        self.last_job_id = job.id
        self.last_run_status = "running"
        storage = None
        error_message = None
        last_completed = first_chapter - 1

        logger.info(
            "Iniciando job %s para %s, capítulos %s a %s",
            job.id,
            book_title,
            first_chapter,
            target_chapter,
        )

        try:
            storage = StorageService(
                downloads_dir=str(
                    self.persistence.data_dir / "books" / str(book.id) / "epubs"
                )
            )
            builder = EpubBuilder(storage_service=storage)
            while chapter_number <= target_chapter:
                if not current_url:
                    error_message = (
                        f"Capítulo {last_completed} não informa URL para o próximo capítulo."
                    )
                    break

                logger.info("Processando capítulo %s -> %s", chapter_number, current_url)
                try:
                    html_content = self.fetcher.fetch(current_url)
                    chapter = self.parser.parse(
                        html_content=html_content,
                        url=current_url,
                        number=chapter_number,
                        profile=self.profile,
                    )
                    if not chapter.content_html:
                        raise RuntimeError("O seletor de conteúdo não encontrou o capítulo")
                    if len(chapter.content_html) < 100:
                        logger.warning(
                            "Capítulo %s extraído com conteúdo suspeitamente curto.",
                            chapter_number,
                        )

                    self.persistence.chapters.save(book.id, chapter)
                    self.persistence.jobs.update_progress(job.id, chapter_number)
                    last_completed = chapter_number
                    current_url = chapter.next_chapter_url
                    chapter_number += 1

                    if chapter_number <= target_chapter and current_url:
                        sleep_time = random.uniform(*self.jitter_range)
                        if sleep_time > 0:
                            time.sleep(sleep_time)
                except Exception as error:
                    error_message = str(error)
                    logger.error(
                        "Erro ao processar capítulo %s: %s", chapter_number, error
                    )
                    break

            if last_completed < first_chapter:
                message = error_message or "Nenhum capítulo pôde ser baixado."
                self.persistence.jobs.finish(job.id, "failed", message)
                self.last_run_status = "failed"
                raise RuntimeError(message)

            output_filename = self._create_epub_from_cache(
                book_id=book.id,
                start=first_chapter,
                end=last_completed,
                book_title=book_title,
                author=author,
                job_id=job.id,
                builder=builder,
            )

            status = "done" if last_completed == target_chapter else "partial"
            self.persistence.jobs.finish(job.id, status, error_message)
            self.last_run_status = status
            return output_filename
        except Exception as error:
            if self.last_run_status == "running":
                self.persistence.jobs.finish(job.id, "failed", str(error))
                self.last_run_status = "failed"
            raise
        finally:
            if storage is not None:
                storage.cleanup()

    def rebuild_epub(
        self,
        book_id: int,
        start: int,
        end: int,
        book_title: str | None = None,
        author: str | None = None,
    ) -> str:
        """Generate a new EPUB entirely from an existing chapter cache."""
        if start < 1 or end < start:
            raise ValueError("The rebuild range is invalid")
        book = self.persistence.books.get_by_id(book_id)
        if book is None:
            raise ValueError(f"Book {book_id} was not found")

        title = book_title or book.title
        epub_author = author or book.author
        self.persistence.jobs.interrupt_running(book.id)
        job = self.persistence.jobs.create(book.id, start, end)
        self.last_job_id = job.id
        self.last_run_status = "running"
        storage = None

        try:
            storage = StorageService(
                downloads_dir=str(
                    self.persistence.data_dir / "books" / str(book.id) / "epubs"
                )
            )
            builder = EpubBuilder(storage_service=storage)
            output_filename = self._create_epub_from_cache(
                book_id=book.id,
                start=start,
                end=end,
                book_title=title,
                author=epub_author,
                job_id=job.id,
                builder=builder,
            )
            self.persistence.jobs.update_progress(job.id, end)
            self.persistence.jobs.finish(job.id, "done")
            self.last_run_status = "done"
            return output_filename
        except Exception as error:
            self.persistence.jobs.finish(job.id, "failed", str(error))
            self.last_run_status = "failed"
            raise
        finally:
            if storage is not None:
                storage.cleanup()

    def _create_epub_from_cache(
        self,
        book_id: int,
        start: int,
        end: int,
        book_title: str,
        author: str,
        job_id: int,
        builder: EpubBuilder,
    ) -> str:
        cached_chapters = self.persistence.chapters.get_range(book_id, start, end)
        expected_count = end - start + 1
        if len(cached_chapters) != expected_count:
            raise RuntimeError(
                f"O cache persistido está incompleto para o intervalo {start}-{end}"
            )

        filename_stem = f"{book_title}_{start}-{end}_job-{job_id}"
        output_filename = builder.create_epub(
            book_title=book_title,
            author=author,
            chapters=cached_chapters,
            filename_stem=filename_stem,
        )
        self.persistence.epubs.record(
            book_id=book_id,
            title=book_title,
            author=author,
            start=start,
            end=end,
            path=output_filename,
        )
        return output_filename

    def _resume_url(
        self,
        book_id: int,
        start_url: str,
        last_chapter_number: int,
        start_chapter_number: int,
    ) -> str | None:
        if last_chapter_number == start_chapter_number - 1:
            baseline_chapter = self.persistence.chapters.get(
                book_id, last_chapter_number
            )
            if baseline_chapter is None:
                return start_url

        if last_chapter_number == 0:
            return start_url

        last_chapter = self.persistence.chapters.get(book_id, last_chapter_number)
        if last_chapter is None:
            raise RuntimeError(
                f"Bookmark points to missing chapter {last_chapter_number}"
            )
        return last_chapter.next_chapter_url
