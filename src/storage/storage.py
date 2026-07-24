# src/services/storage.py

import os
import shutil
import tempfile
import logging

logger = logging.getLogger("WebnovelToKindle.Storage")

class StorageService:
    def __init__(self, downloads_dir: str = "downloads"):
        self.downloads_dir = os.path.abspath(downloads_dir)
        # Cria um diretório temporário seguro no sistema operacional para persistir HTMLs e imagens voláteis
        self.temp_dir = tempfile.mkdtemp(prefix="webnovel_scraping_")
        
        # Garante a existência da pasta final de downloads
        os.makedirs(self.downloads_dir, exist_ok=True)
        logger.info(f"Storage inicializado. Temp: {self.temp_dir} | Downloads: {self.downloads_dir}")

    def save_temp_file(self, filename: str, content: bytes | str) -> str:
        """Salva um arquivo temporário de trabalho (HTML bruto, imagens baixadas, etc.)"""
        filepath = os.path.join(self.temp_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        mode = "wb" if isinstance(content, bytes) else "w"
        encoding = "utf-8" if mode == "w" else None
        
        with open(filepath, mode, encoding=encoding) as f:
            f.write(content)
        return filepath

    def get_temp_filepath(self, filename: str) -> str:
        """Retorna o caminho de um arquivo dentro do diretório temporário"""
        return os.path.join(self.temp_dir, filename)

    def save_final_epub(self, book_title: str, write_callback) -> str:
        """
        Salva o arquivo EPUB final na pasta de downloads.
        Recebe um callback para que a biblioteca de epub escreva diretamente no caminho final gerado.
        """
        safe_title = book_title.lower().replace(" ", "_")
        output_path = os.path.join(self.downloads_dir, f"{safe_title}.epub")
        
        # Executa a escrita delegada
        write_callback(output_path)
        logger.info(f"Arquivo final persistido com sucesso em: {output_path}")
        return output_path

    def cleanup(self):
        """Remove todos os arquivos temporários criados nesta sessão"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info("Diretório temporário de cache limpo com sucesso.")
