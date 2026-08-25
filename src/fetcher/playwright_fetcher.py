# src/fetcher/playwright_fetcher.py
import logging
from playwright.sync_api import sync_playwright
from src.fetcher.base_fetcher import BaseFetcher

logger = logging.getLogger("WebnovelToKindle.Fetcher")

class PlaywrightFetcher(BaseFetcher):
    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms

    def fetch(self, url: str) -> str:
        """
        Abre um navegador headless, carrega o DOM rapidamente e aguarda
        o elemento de texto (<p>) estar presente antes de extrair o HTML.
        """
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
                locale="pt-BR",
                timezone_id="America/Sao_Paulo"
            )
            
            page = context.new_page()
            
            try:
                # 1. Carrega a estrutura inicial sem travar em scripts de rede/anúncios
                page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
                
                # 2. Espera até 10s pelos parágrafos de texto (atende React/Next.js do WeTried)
                try:
                    page.wait_for_selector("p", timeout=10000)
                except Exception:
                    logger.warning(f"Tempo limite atingido aguardando parágrafos em {url}. Continuando...")

                # 3. Pausa pequena de estabilização (1 segundo)
                page.wait_for_timeout(1000)

                html_content = page.content()
                browser.close()
                return html_content
                
            except Exception as e:
                browser.close()
                raise RuntimeError(f"Falha ao renderizar a página {url} via Firefox/Playwright: {e}")
