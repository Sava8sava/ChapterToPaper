# src/fetcher/playwright_fetcher.py
import time
from playwright.sync_api import sync_playwright
from src.fetcher.base_fetcher import BaseFetcher

class PlaywrightFetcher(BaseFetcher):
    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms

    def fetch(self, url: str) -> str:
        """
        Abre um Firefox invisível (headless), aguarda o carregamento do JS 
        e retorna o HTML final totalmente renderizado.
        """
        with sync_playwright() as p:
            # LANÇA O FIREFOX EM SEGUNDO PLANO 🦊
            browser = p.firefox.launch(headless=True)
            
            # Cria um contexto simulando um dispositivo real
            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
                locale="pt-BR",
                timezone_id="America/Sao_Paulo"
            )
            
            page = context.new_page()
            
            try:
                # Navega até a URL e aguarda a rede ficar ociosa
                page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
                
                # Pausa para o Javascript injetar o texto na tela
                time.sleep(3.5)
                
                # Pega o HTML completo renderizado pelo Firefox
                html_content = page.content()
                
                browser.close()
                return html_content
                
            except Exception as e:
                browser.close()
                raise RuntimeError(f"Falha ao renderizar a página {url} via Firefox/Playwright: {e}")
