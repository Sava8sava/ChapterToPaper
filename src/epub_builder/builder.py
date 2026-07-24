# src/epub_builder/builder.py

import os
import uuid
import logging
import mimetypes
import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from src.models.chapter import Chapter
from src.storage.storage import StorageService

# Configuração de logs para acompanharmos o progresso no terminal
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class EpubBuilder:
    def __init__(self,storage_service: StorageService, timeout_images: int = 10):
        self.storage = storage_service
        self.timeout_images = timeout_images
        # Usamos um User-Agent comum para evitar que servidores de imagem nos bloqueiem
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _download_image(self, url: str) -> tuple[bytes, str] | None:
        """
        Baixa uma imagem da internet e retorna seus bytes e o tipo MIME correto.
        Retorna None se o download falhar.
        """
        try:
            logger.info(f"Baixando imagem externa: {url}")
            response = requests.get(url, headers=self.headers, timeout=self.timeout_images)
            response.raise_for_status()
            
            # Detecta o tipo MIME da imagem (ex: image/jpeg, image/png)
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                # Se o header falhar, tenta adivinhar pela extensão da URL
                guessed_type, _ = mimetypes.guess_type(url)
                content_type = guessed_type or "image/jpeg"
                
            return response.content, content_type
        except Exception as e:
            logger.warning(f"Falha ao baixar imagem de {url}: {e}")
            return None

    def create_epub(self, book_title: str, author: str, chapters: list[Chapter]) -> str:
        """
        Recebe a lista de capítulos, processa as imagens embutindo-as fisicamente,
        organiza o sumário, aplica estilos CSS e gera o arquivo .epub final.
        """
        logger.info(f"Iniciando a criação do EPUB: {book_title}")
        
        # 1. Inicializa o objeto do livro
        book = epub.EpubBook()
        
        # Define metadados obrigatórios
        book.set_identifier(str(uuid.uuid4()))
        book.set_title(book_title)
        book.set_language("pt-BR")
        book.add_author(author)
        
        # 2. Define os estilos CSS padrões para o Kindle
        # (Imagens centralizadas, tamanho fluido, parágrafos bem espaçados e justificados)
        style_content = """
            body {
                font-family: "Literata", "Merriweather", serif;
                padding: 0 5%;
            }
            p {
                text-align: justify;
                text-indent: 1.5em;
                margin: 0.5em 0;
                line-height: 1.5;
            }
            img {
                display: block;
                max-width: 100%;
                height: auto;
                margin: 1.5em auto;
            }
            h1, h2, h3 {
                text-align: center;
                margin-top: 1.5em;
                margin-bottom: 1em;
            }
        """
        css_item = epub.EpubItem(
            uid="style_default",
            file_name="style/default.css",
            media_type="text/css",
            content=style_content
        )
        book.add_item(css_item)
        
        epub_chapters = []
        
        # 3. Processa cada capítulo individualmente
        for chapter in chapters:
            logger.info(f"Processando capítulo {chapter.number}: {chapter.title}")
            
            # BeautifulSoup para varrer o HTML e encontrar as imagens
            soup = BeautifulSoup(chapter.content_html, "lxml")
            img_tags = soup.find_all("img")
            
            # Loop de download e substituição das imagens
            for idx, img in enumerate(img_tags):
                img_url = img.get("src")
                if not img_url:
                    continue
                
                # Baixa os bytes da imagem
                img_data = self._download_image(img_url)
                
                if img_data:
                    bytes_data, mime_type = img_data
                    
                    # Define a extensão correta baseada no tipo MIME
                    ext = mimetypes.guess_extension(mime_type) or ".jpg"
                    local_filename = f"images/cap_{chapter.number}_img_{idx}{ext}"
                    
                    # Cria e adiciona o arquivo físico da imagem dentro do livro
                    epub_img = epub.EpubImage()
                    epub_img.uid = f"img_{chapter.number}_{idx}"
                    epub_img.file_name = local_filename
                    epub_img.media_type = mime_type
                    epub_img.content = bytes_data
                    book.add_item(epub_img)
                    
                    # Atualiza o HTML substituindo a URL da web pelo caminho local no EPUB
                    img["src"] = local_filename
                    logger.info(f"Imagem embutida com sucesso: {local_filename}")
                else:
                    # Se falhar, removemos a tag ou limpamos para não aparecer imagem quebrada no Kindle
                    img.decompose()
            
            # Gera o HTML final limpo e atualizado
            processed_html = str(soup)
            
            # Estrutura HTML padrão do capítulo EPUB
            chapter_html_body = f"""
                <html>
                <head>
                    <title>{chapter.title}</title>
                    <link rel="stylesheet" href="style/default.css" type="text/css" />
                </head>
                <body>
                    <h1>{chapter.title}</h1>
                    {processed_html}
                </body>
                </html>
            """
            
            # Cria o item do capítulo
            epub_chap = epub.EpubHtml(
                title=chapter.title,
                file_name=f"chap_{chapter.number:03d}.xhtml",
                lang="pt-BR"
            )
            epub_chap.content = chapter_html_body
            epub_chap.add_item(css_item) # Vincula a folha de estilo
            
            # Adiciona o capítulo ao livro
            book.add_item(epub_chap)
            epub_chapters.append(epub_chap)
            
        # 4. Configurações de Organização Interna do Livro (Obrigatórias)
        book.toc = tuple(epub_chapters) # Sumário interativo
        
        # Define a ordem de leitura do livro (Spine)
        book.spine = ["nav"] + epub_chapters
        
        # Adiciona arquivos padrões de navegação e compatibilidade
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        output_path = self.storage.save_final_epub(
            book_title=book_title,
            write_callback=lambda path: epub.write_epub(path, book, {})
        )
        
        logger.info(f"Livro gerado com sucesso!")
        return output_path
