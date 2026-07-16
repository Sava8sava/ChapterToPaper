# src/orchestrator.py

import os
import time
import random
import logging
from src.models.site_profile import SiteProfile
from src.fetcher.playwright_fetcher import PlaywrightFetcher
from src.parser.config_parser import ConfigParser
from src.epub_builder.builder import EpubBuilder

logger = logging.getLogger("WebnovelToKindle.Orchestrator")

class WebnovelOrchestrator:
    def __init__(self, json_profile_path: str):
        # 1. Instancia as dependências respeitando o RNF3 (SOLID)
        self.profile = SiteProfile.from_json(json_profile_path)
        self.fetcher = PlaywrightFetcher()
        self.parser = ConfigParser()
        self.builder = EpubBuilder()

    def run(self, start_url: str, book_title: str, author: str, max_chapters: int = 100) -> str:
        """
        Executa o fluxo completo de raspagem em corrente e 
        salva o arquivo final na pasta de downloads.
        Retorna o caminho do arquivo gerado.
        """
        chapters_list = []
        current_url = start_url
        chapter_number = 1

        logger.info(f"Iniciando orquestração para: {book_title}")

        while current_url and chapter_number <= max_chapters:
            logger.info(f"Processando Capítulo {chapter_number} -> URL: {current_url}")

            try:
                # Download dinâmico via Playwright
                html_content = self.fetcher.fetch(current_url)

                # Extração semântica com o parser baseado em perfil JSON
                chapter = self.parser.parse(
                    html_content=html_content,
                    url=current_url,
                    number=chapter_number,
                    profile=self.profile
                )

                if not chapter.content_html or len(chapter.content_html) < 100:
                    logger.warning(f"Capítulo {chapter_number} extraído com conteúdo suspeitamente curto.")

                chapters_list.append(chapter)
                logger.info(f"Capítulo {chapter_number} ('{chapter.title}') processado com sucesso.")

                # Avança o ponteiro de navegação
                current_url = chapter.next_chapter_url
                chapter_number += 1

                # Jitter protetivo antes de ir para a próxima página
                if current_url and chapter_number <= max_chapters:
                    sleep_time = random.uniform(4.0, 8.0)
                    logger.info(f"Aplicando jitter. Aguardando {sleep_time:.2f} segundos...")
                    time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Erro ao processar capítulo {chapter_number}: {e}")
                logger.info("Encerrando captura antecipadamente para preservar o progresso atual.")
                break

        if not chapters_list:
            raise RuntimeError("Nenhum capítulo pôde ser baixado. O e-book não será gerado.")

        # Alinhando com o MD: Salvar na pasta "downloads" na raiz do projeto
        downloads_dir = os.path.abspath("downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        
        safe_title = book_title.lower().replace(" ", "_")
        output_filename = os.path.join(downloads_dir, f"{safe_title}.epub")

        logger.info(f"Gerando arquivo físico EPUB em: {output_filename}")
        self.builder.create_epub(
            book_title=book_title,
            author=author,
            chapters=chapters_list,
            output_path=output_filename
        )

        return output_filename
