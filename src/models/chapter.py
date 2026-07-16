from dataclasses import dataclass

@dataclass
class Chapter:
    number: int          # posição sequencial (1, 2, 3...)
    title: str           # título extraído da página (ex: "Capítulo 12: A Fuga")
    content_html: str    # conteúdo do capítulo já limpo, em HTML
    source_url: str      # URL de onde foi extraído (útil pra debug/log)
    next_chapter_url: str | None  # link do próximo capítulo, ou None se for o último
