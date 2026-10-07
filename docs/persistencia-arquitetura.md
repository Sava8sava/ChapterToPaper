# Persistência e Arquitetura — Decisões

Documento das decisões e da implementação de persistência do Webnovel to Kindle.

## Objetivo

Persistir metadados de livros, jobs e EPUBs em banco, com cache dos capítulos
baixados em disco, para permitir:

- Retomar o download de onde parou (bookmark por livro)
- Escolher um intervalo de capítulos
- Regenerar EPUBs sem re-scrapear
- Histórico de execuções (jobs) e artefatos (EPUBs gerados)

## Banco de dados

- **SQLAlchemy Core** para acesso a dados
- **SQLite** como banco inicial, local e single-user
- Trocar de banco no futuro (ex: Postgres) = nova pasta de implementação nas
  mesmas abstrações, sem tocar na lógica do domínio

## Princípio SOLID (DIP)

O orquestrador e o CLI dependem **exclusivamente de abstrações** (repositórios),
nunca do banco concreto. O SQLite é apenas uma implementação plugável.

```
src/persistence/
├── models.py                  # registros de domínio (dataclasses)
├── repositories.py            # abstrações dos repositórios
├── schema.py                  # tabelas e conexão SQLite
└── sqlite.py                  # implementações e wiring dos repositórios
```

Trocar de banco no futuro = criar `src/persistence/postgres/` implementando as
mesmas ABCs e injetar no lugar. Nada mais muda.

## Modelo de dados

Tabelas (SQLite/SQLAlchemy):

- **books** — uma webnovel sendo baixada incrementalmente
  - `id`, `title`, `author`, `profile_path`, `start_url` (primeira URL conhecida)
  - `start_chapter_number`
  - `last_chapter_number` (bookmark), `last_chapter_url`
  - `created_at`, `updated_at`
- **chapters** — cache dos capítulos baixados
  - `id`, `book_id` (FK), `number`, `title`, `source_url`
  - `content_file` (caminho do HTML processado em cache), `next_chapter_url`
  - `downloaded_at`
  - `UNIQUE(book_id, number)`
- **jobs** — uma execução / um intervalo solicitado
  - `id`, `book_id` (FK), `status` (running/done/failed/partial)
  - `from_chapter`, `target_chapter`, `error`
  - `started_at`, `finished_at`
- **epubs** — artefatos gerados (histórico)
  - `id`, `book_id` (FK), `title`, `author`
  - `from_chapter`, `to_chapter`, `path`, `created_at`

O **bookmark** (`last_chapter_number`/`last_chapter_url`) é o coração do recurso:
habilita retomar e definir intervalos.

## Layout de arquivos

```
data/
├── db.sqlite3
└── books/<book_id>/
    ├── chapters/000001.html, 000002.html, ...
    └── epubs/livro_1-50_job-1.epub
```

- Metadados no banco; HTML bruto em arquivo (evita BLOB no banco)
- EPUBs novos são gravados em `data/books/<book_id>/epubs/`
- Arquivos de capítulo e EPUB são publicados por troca atômica de nome

## Fluxo de retomada

1. Usuário roda com a URL inicial de sempre → o sistema procura o livro pela
   `start_url`; se existe, continua de `last_chapter + 1`; se não, cria o livro.
2. Cada capítulo baixado: salva HTML no cache, registra o capítulo e atualiza
   `last_chapter` do livro **imediatamente**. O registro e o bookmark usam a
   mesma transação SQLite.
3. `num_capitulos` define quantos capítulos adicionais serão baixados na execução.
4. Regenerar EPUB sem re-scrapear: lê os `content_file` do intervalo e chama o
   builder direto.

## Integração com o orquestrador

O `WebnovelOrchestrator` passa a receber os repositórios via construtor (DI),
como já faz com fetcher/parser/storage:

1. `book_repo.get_or_create_by_start_url(start_url)` → acha o livro ou cria;
   `--start-number` define a numeração inicial somente para um livro novo
2. Loop de capítulos: `fetch → parse → chapter_repo.save()` grava o HTML,
   registra o capítulo e atualiza o bookmark no mesmo checkpoint
3. Para quando baixar a quantidade solicitada em `num_capitulos`
4. `job_repo.update_status(done/failed/partial)`
5. EPUB gerado lendo os `content_file` do intervalo → `epub_repo.record()`
6. Um job deixado como `running` por encerramento abrupto é marcado como
   `partial`/`failed` antes da próxima execução do mesmo livro

O CLI expõe a regeneração sem scraping com
`--book-id ID --rebuild-cache INICIO FIM`.

## Decisões fechadas

- Identidade do livro: `start_url` como chave natural, com `--book-id` como escape
- Numeração no primeiro run: novo argumento `--start-number` (default 1)
- Cache de capítulos: incluído nesta etapa
- Banco inicial: SQLite via SQLAlchemy Core
