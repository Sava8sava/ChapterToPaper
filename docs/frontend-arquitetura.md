# Frontend Web — Decisões

Documento de decisões para a atualização de frontend do Webnovel to Kindle.

## Objetivo

Criar uma interface web que rode localmente, expondo o mesmo fluxo do CLI com
progresso em tempo real e histórico de livros/jobs. O CLI continua coexistindo.

## Stack

- **FastAPI** + **Jinja2** (server-rendered) + **JS puro** (fetch + polling)
- 100% Python, zero build step, alinhado ao projeto atual
- Dependências novas em `requirements.txt`: `fastapi`, `uvicorn`, `jinja2`
- Descartadas para uso local single-user: React/Vue (build step + node) e
  Streamlit (fraco para job de background/progresso)

## Estrutura

```
src/web/
├── app.py                    # FastAPI: rotas e wiring (injeção dos repositórios)
├── jobs.py                   # JobManager: executa o scraping em background (asyncio task)
├── templates/                # Jinja2: dashboard, form, detalhe do livro
└── static/                   # JS puro (fetch + polling ~2s) e CSS
```

## JobManager

- Executa o `WebnovelOrchestrator` como task async in-process
- Single-user local **não precisa de Celery/Redis**
- Progresso/status persistidos na tabela `jobs` (já definida na persistência),
  lidos via repositório — sobrevive a recarga da página

## Telas

1. **Formulário de download** — URL inicial, intervalo (de/até), título, autor,
   perfil do site → dispara o job
2. **Progresso em tempo real** — contador "capítulo X de Y", status
   (running/failed/done) e último erro; polling a cada ~2s
3. **Lista de livros** — posição salva (`last_chapter`), botão
   "continuar de onde parou", "baixar EPUB" (servido pelo FastAPI) e
   "regenerar" via cache (sem re-scrapear)

## Arquitetura (SOLID)

- O web app injeta os mesmos repositórios abstratos usados pelo orquestrador (DI)
- A web é uma segunda interface sobre as mesmas camadas de domínio/repositórios,
  não uma substituição

## Decisões fechadas

- **A.** Abrangência: CLI e web convivem (CLI preservado para scriptar/automatizar)
- **B.** EPUBs servidos diretamente pelo FastAPI
- **C.** Sem autenticação (uso local, single-user)
- **D.** Progresso: contador + status + último erro

## Fora de escopo (futuro)

- Login/proteção
- Docker Compose (já possui Dockerfile)