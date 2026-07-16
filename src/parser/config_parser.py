# src/parser/config_parser.py

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from src.models.site_profile import SiteProfile
from src.models.chapter import Chapter

class ConfigParser:
    def parse(self, html_content: str, url: str, number: int, profile: SiteProfile) -> Chapter:
        """
        Lê o HTML, extrai os dados e retorna o seu objeto Chapter estruturado.
        """
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 1. Extrai o título do capítulo
        title_element = soup.select_one(profile.title_selector)
        title = title_element.get_text(strip=True) if title_element else f"Capítulo {number}"
        
        # 2. Extrai o conteúdo (HTML limpo)
        content_element = soup.select_one(profile.content_selector)
        content_html = str(content_element) if content_element else ""
        
        # 3. Extrai e resolve a URL do próximo capítulo
        next_chapter_url = None
        next_element = soup.select_one(profile.next_chapter_selector)
        if next_element:
            href = next_element.get(profile.next_chapter_attr)
            if href:
                next_chapter_url = urljoin(url, href)
        
        # Retorna o seu modelo Chapter exatamente com todos os campos preenchidos!
        return Chapter(
            number=number,
            title=title,
            content_html=content_html,
            source_url=url,
            next_chapter_url=next_chapter_url
        )
