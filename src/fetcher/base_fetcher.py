# src/fetcher/base_fetcher.py
from abc import ABC, abstractmethod

class BaseFetcher(ABC):
    @abstractmethod
    def fetch(self, url: str) -> str:
        """
        Faz a requisição HTTP para a URL fornecida e retorna o conteúdo HTML como string.
        Deve levantar uma exceção em caso de erro (ex: 404, 500, timeout).
        """
        pass
