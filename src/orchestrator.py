# src/orchestrator.py

import time
import random
import logging
from src.models.site_profile import SiteProfile
from src.fetcher.playwright_fetcher import PlaywrightFetcher
from src.parser.config_parser import ConfigParser
from src.epub_builder.builder import EpubBuilder
from src.storage.storage import StorageService  # Importando o Storage correspondente à sua pasta

logger = logging.getLogger("WebnovelToKindle.Orchestrator")

class WebnovelOrchestrator:
    def __init__(self, json_profile_path: str):
        # 1. Instancia e injeta as dependências de forma limpa (DIP)
        self.profile = SiteProfile.from_json(json_profile_path)
        self.fetcher = PlaywrightFetcher()
        self.parser = ConfigParser()
        
        # O Orchestrator gerencia o ciclo de vida do StorageService nesta execução
        self.storage = StorageService()
        
        # Injetamos o serviço de armazenamento no EpubBuilder
        self.builder = EpubBuilder(storage_service=self.storage)

    def run(self, start_url: str, book_title: str, author: str, max_chapters: int = 100) -> str:
        """
        Executa o fluxo completo de raspagem em corrente, gerencia arquivos temporários
        e delega a geração física do EPUB. Retorna o caminho do arquivo gerado.
        """
        chapters_list = []
        current_url = start_url
        chapter_number = 1

        logger.info(f"Iniciando orquestração para: {book_title}")

        try:
            while current_url and chapter_number <= max_chapters:
                logger.info(f"Processando Capítulo {chapter_number} -> URL: {current_url}")

                try:
                    # 1. Download dinâmico via Playwright
                    html_content = self.fetcher.fetch(current_url)

                    # 2. Opcional/Debug Seguro: Salvar o HTML bruto baixado na pasta temporária do storage
                    # self.storage.save_temp_file(f"cap_{chapter_number}_raw.html", html_content)

                    # 3. Extração semântica com o parser
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
            logger.info("Enviando capítulos para geração de e-book...")
            output_filename = self.builder.create_epub(
                book_title=book_title,
                author=author,
                chapters=chapters_list
            )

            return output_filename

        finally:
            # RNF (Requisito Não Funcional): Garante que a sujeira temporária seja eliminada
            # do computador do usuário, independentemente de sucesso ou falha no meio do processo.
            logger.info("Iniciando limpeza de arquivos temporários do ciclo de vida...")
            self.storage.cleanup()
