#interface do parser
from abc import ABC, abstractmethod
from src.models.site_profile import SiteProfile
from src.models.chapter import Chapter

class BaseParser(ABC):
    @abstractmethod
    def parse(self, html_content: str, url: str, profile: SiteProfile) -> Chapter:
        """Extrai o título e o conteúdo do capítulo."""
        pass

    @abstractmethod
    def get_next_chapter_url(self, html_content: str, profile: SiteProfile) -> str | None:
        """Extrai a URL do próximo capítulo. Retorna None se não houver."""
        pass
