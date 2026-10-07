# src/services/storage.py

import os
import re
import shutil
import tempfile
import logging
import unicodedata

logger = logging.getLogger("WebnovelToKindle.Storage")

class StorageService:
    def __init__(self, downloads_dir: str = "downloads"):
        self.downloads_dir = os.path.abspath(downloads_dir)
        # Garante a existência da pasta final de downloads
        os.makedirs(self.downloads_dir, exist_ok=True)
        # Cria um diretório temporário seguro no sistema operacional para persistir HTMLs e imagens voláteis
        self.temp_dir = tempfile.mkdtemp(prefix="webnovel_scraping_")
        logger.info(f"Storage inicializado. Temp: {self.temp_dir} | Downloads: {self.downloads_dir}")

    def save_temp_file(self, filename: str, content: bytes | str) -> str:
        """Salva um arquivo temporário de trabalho (HTML bruto, imagens baixadas, etc.)"""
        filepath = self.get_temp_filepath(filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        mode = "wb" if isinstance(content, bytes) else "w"
        encoding = "utf-8" if mode == "w" else None
        
        with open(filepath, mode, encoding=encoding) as f:
            f.write(content)
        return filepath

    def get_temp_filepath(self, filename: str) -> str:
        """Retorna o caminho de um arquivo dentro do diretório temporário"""
        filepath = os.path.abspath(os.path.join(self.temp_dir, filename))
        if os.path.commonpath([self.temp_dir, filepath]) != self.temp_dir:
            raise ValueError(f"Caminho temporário inseguro: {filename}")
        return filepath

    @staticmethod
    def safe_filename(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
        filename = re.sub(r"[^a-zA-Z0-9_-]+", "_", ascii_value).strip("_-")
        return filename.lower() or "ebook"

    def save_final_epub(
        self,
        book_title: str,
        write_callback,
        filename_stem: str | None = None,
    ) -> str:
        """
        Salva o arquivo EPUB final na pasta de downloads.
        Recebe um callback para que a biblioteca de epub escreva diretamente no caminho final gerado.
        """
        safe_title = self.safe_filename(filename_stem or book_title)
        output_path = os.path.join(self.downloads_dir, f"{safe_title}.epub")
        file_descriptor, temporary_path = tempfile.mkstemp(
            prefix=f".{safe_title}.", suffix=".epub.tmp", dir=self.downloads_dir
        )
        os.close(file_descriptor)

        try:
            write_callback(temporary_path)
            if os.path.getsize(temporary_path) == 0:
                raise RuntimeError("A geração do EPUB produziu um arquivo vazio")
            with open(temporary_path, "rb") as handle:
                os.fsync(handle.fileno())
            os.replace(temporary_path, output_path)
        except Exception:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise

        logger.info(f"Arquivo final persistido com sucesso em: {output_path}")
        return output_path

    def cleanup(self):
        """Remove todos os arquivos temporários criados nesta sessão"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info("Diretório temporário de cache limpo com sucesso.")
