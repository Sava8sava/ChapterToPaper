# Webnovel to Kindle

Aplicação para baixar capítulos de web novels a partir de um link e compilá-los em um único arquivo EPUB, pronto para leitura no Kindle.

## Funcionalidades

- Recebe um link de capítulo de novel e uma quantidade desejada de capítulos
- Baixa sequencialmente os capítulos seguintes a partir do link informado
- Converte o conteúdo HTML de cada capítulo para EPUB
- Compila todos os capítulos em um único arquivo EPUB
- Salva o arquivo final localmente
- Persiste cada capítulo e retoma automaticamente após interrupções
- Mantém histórico de execuções e EPUBs em SQLite
- Registra execuções incompletas como `partial` ou `failed`
- Pausa com jitter entre requisições para evitar bloqueio
- Perfil de site configurável via JSON (seletores CSS/XPath)

## Requisitos

- Python 3.10+
- Dependências listadas em `requirements.txt`
- Docker (opcional)

## Instalação

### Local

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Docker

```bash
docker compose build
```

## Uso

### Local

```bash
python main.py <url_do_capitulo> <numero_de_capitulos> [--profile <arquivo_json>]
```

`numero_de_capitulos` é a quantidade adicional desta execução. Ao repetir a URL
inicial, o programa identifica o livro e continua a partir do próximo capítulo
persistido.

Se a URL inicial não corresponde ao capítulo 1, informe sua numeração no
primeiro uso:

```bash
python main.py <url_do_capitulo_50> 10 --start-number 50
```

Use `--book-id ID` para selecionar explicitamente um livro já cadastrado e
`--data-dir DIRETORIO` para alterar o diretório persistente (padrão: `data`).

Para gerar outro EPUB sem acessar o site, use um intervalo já armazenado:

```bash
python main.py --book-id 1 --rebuild-cache 1 50
```

### Docker

```bash
docker compose run --rm app <url_do_capitulo> <numero_de_capitulos> [--profile <arquivo_json>]
```

O diretório local `data/` é montado em `/app/data`, preservando banco, cache e
EPUBs entre execuções do container.

## Estrutura do projeto

```
webnovel-to-kindle/
├── config/sites/          # Perfis JSON dos sites suportados
├── src/
│   ├── fetcher/           # Requisições HTTP (interface + implementação requests)
│   ├── parser/            # Parsing HTML (extração de conteúdo e próximo link)
│   ├── epub_builder/      # Conversão e compilação de EPUBs
│   ├── storage/           # Salvamento local do arquivo final
│   ├── persistence/       # Repositórios e implementação SQLite
│   ├── models/            # Objetos de dados (Chapter, SiteProfile)
│   └── orchestrator.py    # Coordena o fluxo completo
├── data/                  # Banco, cache dos capítulos e EPUBs finais
├── main.py                # Ponto de entrada (CLI)
└── requirements.txt
```

## Arquitetura

O projeto segue os princípios SOLID com módulos desacoplados por responsabilidade:

1. **Fetcher** — baixa o HTML de cada capítulo
2. **Parser** — extrai título, conteúdo e link do próximo capítulo
3. **EpubBuilder** — monta um único EPUB com todos os capítulos
4. **Persistence** — registra livros, capítulos, jobs e EPUBs em SQLite
5. **Storage** — escreve cache e EPUBs de forma atômica em disco

Cada capítulo é persistido antes do próximo download. Ao final, o EPUB é montado
a partir do cache persistente via Ebooklib.

## Dados persistidos

```text
data/
├── db.sqlite3
└── books/<book_id>/
    ├── chapters/000001.html
    └── epubs/<titulo>_<inicio>-<fim>_job-<id>.epub
```

Não remova somente o banco ou somente os arquivos de capítulos: os metadados e
o cache formam uma única unidade lógica.

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
