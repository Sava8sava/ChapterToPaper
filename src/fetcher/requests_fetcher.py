# src/fetcher/requests_fetcher.py
import requests
from fake_useragent import UserAgent
from src.fetcher.base_fetcher import BaseFetcher

class RequestsFetcher(BaseFetcher):
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        # Inicializa o gerador de User-Agents falsos/reais
        self.ua = UserAgent()

    def _get_headers(self) -> dict:
        """Gera cabeçalhos realistas para simular um navegador comum."""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/",
            "DNT": "1",  # Do Not Track
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

    def fetch(self, url: str) -> str:
        """Faz o download do HTML de uma URL de forma segura."""
        headers = self._get_headers()
        
        try:
            # Realiza a requisição GET simulando um navegador
            response = requests.get(url, headers=headers, timeout=self.timeout)
            
            # Levanta um erro caso o status code não seja da família 200 (ex: 403, 404, 500)
            response.raise_for_status()
            
            # Garante a codificação correta dos caracteres (acentos em português)
            response.encoding = response.apparent_encoding
            
            return response.text
            
        except requests.exceptions.HTTPError as http_err:
            raise RuntimeError(f"Erro HTTP ao acessar {url}: {http_err}")
        except requests.exceptions.RequestException as req_err:
            raise RuntimeError(f"Erro de conexão ao acessar {url}: {req_err}")
