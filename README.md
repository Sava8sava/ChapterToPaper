# Webnovel to Kindle

Aplicação para baixar capítulos de web novels a partir de um link e compilá-los em um único arquivo EPUB, pronto para leitura no Kindle.

## Funcionalidades

- Recebe um link de capítulo de novel e uma quantidade desejada de capítulos
- Baixa sequencialmente os capítulos seguintes a partir do link informado
- Converte o conteúdo HTML de cada capítulo para EPUB
- Compila todos os capítulos em um único arquivo EPUB
- Salva o arquivo final localmente
- Pausa com jitter entre requisições para evitar bloqueio
- Perfil de site configurável via JSON (seletores CSS/XPath)

## Requisitos

- Python 3.10+
- Dependências listadas em `requirements.txt`

## Instalação

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
python main.py <url_do_capitulo> <numero_de_capitulos> [--profile <arquivo_json>]
```

## Estrutura do projeto

```
webnovel-to-kindle/
├── config/sites/          # Perfis JSON dos sites suportados
├── src/
│   ├── fetcher/           # Requisições HTTP (interface + implementação requests)
│   ├── parser/            # Parsing HTML (extração de conteúdo e próximo link)
│   ├── epub_builder/      # Conversão e compilação de EPUBs
│   ├── storage/           # Salvamento local do arquivo final
│   ├── models/            # Objetos de dados (Chapter, SiteProfile)
│   └── orchestrator.py    # Coordena o fluxo completo
├── downloads/             # Saída dos EPUBs finais
├── main.py                # Ponto de entrada (CLI)
└── requirements.txt
```

## Arquitetura

O projeto segue os princípios SOLID com módulos desacoplados por responsabilidade:

1. **Fetcher** — baixa o HTML de cada capítulo
2. **Parser** — extrai título, conteúdo e link do próximo capítulo
3. **EpubBuilder** — monta um único EPUB com todos os capítulos
4. **Storage** — salva o arquivo final em disco

Todos os capítulos são baixados como HTML puro primeiro; ao final, um único `EpubBook` é montado via Ebooklib.

## Perfil de site

Crie um arquivo JSON em `config/sites/` com os seletores do site:

```json
{
  "site": "exemplo.com",
  "title_selector": "h1.chapter-title",
  "content_selector": "div.chapter-content",
  "next_chapter_selector": "a.next-chap",
  "next_chapter_attr": "href"
}
```

## Conversão para Kindle (opcional)

Para compatibilidade com Kindles mais antigos, converta o EPUB para AZW3 usando Calibre:

```bash
ebook-convert livro.epub livro.azw3
```
