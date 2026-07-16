from dataclasses import dataclass

@dataclass
class SiteProfile:
    site: str                    # nome/domínio do site (ex: "exemplo.com")
    title_selector: str          # seletor CSS do título do capítulo
    content_selector: str        # seletor CSS do conteúdo do capítulo
    next_chapter_selector: str   # seletor CSS do link/elemento do próximo capítulo
    next_chapter_attr: str       # atributo de onde tirar a URL (geralmente "href")

    @classmethod
    def from_json(cls, path: str) -> "SiteProfile":
        import json
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
