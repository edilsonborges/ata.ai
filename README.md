# ata.ai

Plataforma para transformar áudios e vídeos de reuniões em artefatos estruturados — transcrição (`.vtt`), análise estruturada (`.md`) e dashboard visual self-contained (`.html`) — com dois caminhos de uso que compartilham o mesmo pipeline:

- **Slash command Claude Code** (`/analisar-reuniao`) — fluxo offline executado dentro do editor; gera os artefatos direto na raiz do repositório.
- **App web full-stack** (FastAPI + Next.js + PostgreSQL) — interface com autenticação, histórico de jobs, múltiplos provedores de LLM configuráveis e progresso em tempo real via SSE.

Este README é o manual operacional do repositório. Para o histórico de design consulte `docs/superpowers/`.

---

## Índice

1. [Visão geral](#visao-geral)
2. [Arquitetura](#arquitetura)
3. [Pré-requisitos](#pre-requisitos)
4. [Setup rápido — app web (Docker Compose)](#setup-rapido-app-web-docker-compose)
5. [Setup do slash command (offline)](#setup-do-slash-command-offline)
6. [Estrutura do repositório](#estrutura-do-repositorio)
7. [Usando o app web](#usando-o-app-web)
8. [Usando o slash command `/analisar-reuniao`](#usando-o-slash-command-analisar-reuniao)
9. [Skills complementares](#skills-complementares)
10. [Templates de dashboard](#templates-de-dashboard)
11. [API REST](#api-rest)
12. [Provedores de LLM](#provedores-de-llm)
13. [Desenvolvimento](#desenvolvimento)
14. [Troubleshooting](#troubleshooting)
15. [Documentação adicional](#documentacao-adicional)

---

## Visão geral

O pipeline é o mesmo nos dois caminhos:

```
arquivo (mp4/mov/webm/wav/mp3/...) 
    -> ffmpeg (extrai WAV 16kHz mono)
    -> Whisper (transcricao.vtt + texto + segmentos JSON)
    -> LLM (Anthropic | OpenAI | OpenRouter | Claude CLI) — produz JSON estruturado
    -> renderers (analise.md + dashboard.html)
```

O resultado é uma pasta com três arquivos irmãos, nomeada `analise_{DD-MM-YYYY}_{HH-MM-SS}_{slug}/`:

- `transcricao.vtt` — transcrição com timestamps (WebVTT)
- `analise.md` — análise em markdown (resumo, tópicos, decisões, findings, ações, riscos, timeline, entidades, sentimento, insights)
- `dashboard.html` — dashboard visual self-contained (CSS puro, zero CDN, light mode forçado — abre em Quick Look iOS, AirDrop preview, navegador e impressão sem dependências)

Regras duras respeitadas por ambos os caminhos:
- Nunca inventar dados não presentes na transcrição.
- Sempre citar trechos literais com timestamp `[MM:SS]`.
- Sem emojis nos artefatos.
- Português brasileiro.
- Slug kebab-case, lowercase, sem acentos.
- Whisper não separa locutores — participantes são inferidos por contexto e isso é declarado explicitamente.

---

## Arquitetura

### Ambos os caminhos compartilham

- Formato dos artefatos finais (`.vtt`, `.md`, `.html`)
- Paleta e convenções visuais do dashboard (indigo `#4f46e5`, classes `insight-card`, `timeline-item`, `tag-*`)
- Biblioteca de templates HTML (`.claude/templates/`)
- Regras rígidas de renderização (light mode, zero JS para dados, sem CDN, transcrição embutida)

### Caminho 1 — Slash command (offline)

- Executado dentro do Claude Code.
- Arquivo: `.claude/commands/analisar-reuniao.md` (~900 linhas, pipeline literal).
- Usa binários locais: `/opt/homebrew/bin/ffmpeg` e `/Library/Frameworks/Python.framework/Versions/Current/bin/python3` com `openai-whisper`.
- Gera a pasta na raiz do projeto (`$CLAUDE_PROJECT_DIR`).
- Não depende de rede, banco nem autenticação.

### Caminho 2 — App web (online)

Quatro serviços orquestrados por Docker Compose:

| Serviço    | Tecnologia              | Porta | Função                                    |
|------------|-------------------------|-------|-------------------------------------------|
| `postgres` | PostgreSQL 16           | 5432  | Persistência (users, jobs, events, providers, benchmarks) |
| `api`      | FastAPI 0.111 / Uvicorn | 8000  | Endpoints REST + SSE                      |
| `worker`   | Python 3.12             | —     | Processa jobs em background (polling)     |
| `web`      | Next.js 14 App Router   | 3000  | Interface web (TypeScript + Tailwind)     |

Progresso em tempo real: cada fase do worker insere em `job_events`, um trigger `PL/pgSQL` dispara `NOTIFY job_event`, o router `/api/jobs/{id}/events` faz `LISTEN` e transmite como Server-Sent Events para o frontend.

### Fluxo de dados (app web)

```
upload (multipart) 
    -> POST /api/jobs (api salva em storage/uploads, cria Job queued)
    -> worker polling detecta, muda status=running
    -> ffprobe (duração) -> ffmpeg (áudio) -> Whisper (transcricao) 
    -> LLM provider (análise estruturada) -> markdown + dashboard 
    -> storage/analyses/{folder_name}/ 
    -> status=done, SSE emite phase=done
    -> frontend embute iframe do dashboard + links de download
```

---

## Pré-requisitos

### Para o app web (Docker)

- Docker Desktop (ou Docker Engine) com Docker Compose v2
- ~8 GB livres em disco (imagens + modelo Whisper cacheado + uploads)
- Portas livres: `3000`, `8000`, `5432`

### Para o slash command (local, macOS)

- `ffmpeg` em `/opt/homebrew/bin/ffmpeg`
  ```bash
  brew install ffmpeg
  ```
- Python com `openai-whisper` em `/Library/Frameworks/Python.framework/Versions/Current/bin/python3`
  ```bash
  /Library/Frameworks/Python.framework/Versions/Current/bin/pip3 install openai-whisper torch
  ```
- Claude Code CLI instalado

Se qualquer dependência faltar, o slash command falha sem fallback (intencional — evita resultados inconsistentes).

### Para usar provedores LLM remotos

Chave de API de pelo menos um de:
- Anthropic (Claude) — https://console.anthropic.com
- OpenAI — https://platform.openai.com
- OpenRouter — https://openrouter.ai

Alternativa sem custo de API: `claude_cli` (usa o Claude Code local via volume mount — requer o CLI autenticado em `~/.claude.json`).

---

## Setup rápido — app web (Docker Compose)

### 1. Clone e configure

```bash
git clone https://github.com/edilsonborges/ata.ai.git
cd ata.ai
cp .env.example .env
```

### 2. Gere os secrets e ajuste `.env`

```bash
# JWT_SECRET (32 bytes em hex)
openssl rand -hex 32

# FERNET_KEY (base64 urlsafe, 32 bytes)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Edite `.env` colocando os valores gerados e trocando `POSTGRES_PASSWORD`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`. Variáveis completas:

| Variável                    | Exemplo                                   | Observação |
|-----------------------------|-------------------------------------------|------------|
| `POSTGRES_DB`               | `ata`                                     | nome do database |
| `POSTGRES_USER`             | `ata`                                     | |
| `POSTGRES_PASSWORD`         | `change-me-in-production`                 | trocar antes de produção |
| `JWT_SECRET`                | saída de `openssl rand -hex 32`           | HS256 |
| `JWT_ACCESS_TTL_SECONDS`    | `900` (15 min)                            | |
| `JWT_REFRESH_TTL_SECONDS`   | `2592000` (30 dias)                       | |
| `FERNET_KEY`                | saída do `Fernet.generate_key()`          | criptografa API keys |
| `ADMIN_EMAIL`               | `admin@edilson.dev`                       | usuário seed |
| `ADMIN_PASSWORD`            | `ksjao10so!`                              | seed inicial — trocar |
| `MAX_UPLOAD_MB`             | `500`                                     | limite de upload |
| `STORAGE_DIR`               | `/app/storage`                            | dentro do container |

### 3. Suba o stack

```bash
docker compose up --build
```

Ordem de startup:
1. `postgres` sobe e aguarda healthy.
2. `api` roda `alembic upgrade head`, depois `python -m app.seed` (cria admin + credenciais vazias dos 4 provedores), depois `uvicorn --reload`.
3. `worker` conecta ao Postgres e entra no loop de polling (2s).
4. `web` roda `npm run dev`.

Quando todos subirem:
- Frontend: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs
- Health: http://localhost:8000/health

### 4. Primeiro acesso

1. Abra http://localhost:3000 — o middleware redireciona para `/login`.
2. Use `ADMIN_EMAIL` / `ADMIN_PASSWORD` do `.env`.
3. Vá em **Configurações** e habilite pelo menos um provedor de LLM (cole a API key e marque "Ativado").
4. Volte para **/** e clique em **Nova análise** para subir um vídeo/áudio.

---

## Setup do slash command (offline)

Nenhum setup além dos pré-requisitos locais. Dentro do Claude Code, na raiz deste repositório:

```
/analisar-reuniao /caminho/para/video.mp4
```

Também aceita caminho relativo ou arquivos com espaços (use aspas):

```
/analisar-reuniao @"Dados reuniao - 2026-03-31.mp4"
```

Se `$ARGUMENTS` estiver vazio, o comando pede o caminho.

A pasta de saída é criada em `$CLAUDE_PROJECT_DIR` (raiz do repo), não no diretório do arquivo de entrada.

---

## Estrutura do repositório

```
ata.ai/
├── .claude/
│   ├── commands/
│   │   └── analisar-reuniao.md       # slash command principal (~900 linhas)
│   ├── skills/                       # 8 skills complementares (SKILL.md cada)
│   │   ├── analisar-1on1/
│   │   ├── analisar-decisoes/
│   │   ├── analisar-rapido/
│   │   ├── comparar-reunioes/
│   │   ├── consolidar-acoes/
│   │   ├── gerar-ata-formal/
│   │   ├── gerar-pdf-reuniao/
│   │   └── gerar-slides/
│   └── templates/                    # biblioteca de dashboards HTML
│       ├── executivo-clean.html
│       ├── tecnico-denso.html
│       ├── retrospectiva-warm.html
│       ├── minimalista-editorial.html
│       └── README.md                 # regra de escolha de template
├── backend/                          # FastAPI + worker (Python 3.12)
│   ├── app/
│   │   ├── main.py                   # entrypoint FastAPI + CORS + routers
│   │   ├── config.py                 # Settings via pydantic-settings
│   │   ├── db.py                     # engine asyncpg / session factory
│   │   ├── deps.py                   # current_user dependency
│   │   ├── security.py               # JWT + bcrypt + Fernet
│   │   ├── seed.py                   # cria admin + credenciais vazias
│   │   ├── models/                   # SQLModel: User, Job, JobEvent, ProviderCredential, WhisperBenchmark
│   │   ├── schemas/                  # Pydantic IO
│   │   ├── routers/                  # auth, settings, whisper, jobs, events, artifacts
│   │   ├── services/
│   │   │   ├── storage.py            # paths, slugify, extensões suportadas
│   │   │   ├── ffprobe.py            # duração de mídia
│   │   │   ├── whisper_runner.py     # wrapper do openai-whisper
│   │   │   ├── benchmark.py          # ETA dinâmico por modelo
│   │   │   ├── analysis/             # 4 providers + base + prompts + schemas
│   │   │   └── renderer/             # markdown.py, dashboard.py
│   │   └── workers/
│   │       ├── main.py               # polling loop
│   │       └── pipeline.py           # process_job (validar, ffmpeg, whisper, LLM, render)
│   ├── migrations/                   # Alembic (0001_initial + trigger PL/pgSQL)
│   ├── alembic.ini
│   ├── pyproject.toml                # deps e extras [dev]
│   └── Dockerfile                    # python:3.12-slim + ffmpeg + node + @anthropic-ai/claude-code
├── frontend/                         # Next.js 14 (TypeScript + Tailwind)
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── globals.css
│   │   │   ├── (auth)/login/         # /login (público)
│   │   │   └── (app)/                # rotas autenticadas
│   │   │       ├── layout.tsx        # shell
│   │   │       ├── page.tsx          # / (lista de jobs)
│   │   │       ├── upload/           # /upload
│   │   │       ├── settings/         # /settings
│   │   │       └── jobs/[id]/        # /jobs/:id (SSE + iframe)
│   │   ├── lib/
│   │   │   ├── api.ts                # fetch wrapper + refresh 401
│   │   │   └── auth.ts               # localStorage ata_tokens
│   │   └── middleware.ts             # redireciona conforme token
│   ├── next.config.mjs               # rewrite /api/* -> NEXT_PUBLIC_API_URL
│   ├── tailwind.config.ts
│   ├── package.json
│   └── Dockerfile                    # node:20-alpine
├── docs/
│   └── superpowers/
│       ├── plans/                    # planos de implementação (2026-04-11...)
│       └── specs/                    # specs de design (2026-04-11...)
├── storage/                          # bind-mount do Docker (persistente)
│   ├── uploads/                      # entrada: {job_id}_{filename}
│   └── analyses/                     # saída: analise_DD-MM-YYYY_HH-MM-SS_slug/
├── analise_*/                        # saídas do slash command (raiz; ignoradas pelo git)
├── docker-compose.yml                # 4 serviços
├── .env.example
├── CLAUDE.md                         # guia do Claude Code para este repo
└── README.md                         # este arquivo
```

> Nota: O `.gitignore` ignora `analise_*/` (saídas do slash command), `storage/uploads/*` e `storage/analyses/*` (saídas do app web), `.env`, `node_modules/`, `.next/`, caches Python e screenshots soltos.

---

## Usando o app web

### 1. Login

Digite email e senha (seed do `.env`). Tokens `access` (15 min) e `refresh` (30 dias) são guardados em `localStorage` como `ata_tokens`. O cliente (`lib/api.ts`) faz refresh automático ao receber 401.

### 2. Configurar um provedor de LLM

Página **/settings**. Para cada provedor:

- **Ativado** — liga/desliga para aparecer na seleção de upload.
- **Modelo default** — string literal enviada ao provedor (ex.: `claude-opus-4-6`, `gpt-4o`, `anthropic/claude-3.5-sonnet`).
- **API key** — criptografada com Fernet antes de salvar (após salvar, o backend só retorna `has_api_key: true`, nunca o valor). Deixe vazio para manter o valor atual ao atualizar outro campo.

O provedor `claude_cli` não pede API key — usa o Claude Code local do host via volume (`${HOME}/.claude` e `${HOME}/.claude.json` montados read-only no container do worker).

### 3. Criar uma nova análise

Página **/upload**:

1. Selecione o arquivo (aceita `.mp4`, `.mov`, `.webm`, `.avi`, `.mkv`, `.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac`).
2. O cliente detecta a duração via `HTMLMediaElement` e chama `GET /api/whisper/models?duration_s=X` — a resposta traz ETA estimado por modelo (calibrado pela tabela `whisper_benchmarks` a partir de execuções anteriores).
3. Escolha o modelo Whisper (default: `medium`). `tiny` / `small` são mais rápidos; `large` é mais preciso.
4. Escolha o provedor de LLM (só aparecem os com `enabled=true`).
5. Clique em **Processar**.

### 4. Acompanhar progresso em tempo real

A página `/jobs/:id` abre um stream SSE (`GET /api/jobs/:id/events`). Cada evento emitido pelo worker aparece na UI com fase e porcentagem:

```
validating (0-10%) 
  -> extracting_audio (10-20%) 
  -> transcribing (20-70%) 
  -> analyzing (72-90%) 
  -> rendering (90-100%) 
  -> done (100%)
```

### 5. Baixar artefatos

Quando `status=done`:

- Links diretos de download: `transcricao.vtt`, `analise.md`.
- Botão "Abrir dashboard" — abre em nova aba.
- Iframe embutido com o `dashboard.html` renderizado em 80vh.

Para apagar um job (e seus arquivos em `storage/uploads/` e `storage/analyses/`): `DELETE /api/jobs/{id}` via UI ou curl.

---

## Usando o slash command `/analisar-reuniao`

O arquivo fonte `.claude/commands/analisar-reuniao.md` é interpretado literalmente pelo Claude Code — os blocos Bash/Python dentro dele são copiados e executados como estão.

### Fases

| Fase | Ação | Artefato |
|------|------|----------|
| 0 | Validação (extensão e existência) | — |
| 1 | `ffmpeg` extrai áudio (se vídeo) | `/tmp/reuniao_audio.wav` |
| 2 | Whisper transcreve com modelo `medium`, idioma `pt` | `/tmp/reuniao_out/transcricao.vtt`, `/tmp/reuniao_transcript.txt`, `/tmp/reuniao_segments.json` |
| 3 | Claude analisa texto + segmentos | (em memória) |
| 4 | Cria pasta `analise_DD-MM-YYYY_HH-MM-SS_slug/` em `$CLAUDE_PROJECT_DIR` e copia VTT | `transcricao.vtt` |
| 5 | Gera análise em markdown | `analise.md` |
| 6 | Gera dashboard HTML (escolhe template em `.claude/templates/` conforme peso dominante da reunião) | `dashboard.html` |
| 7 | Apresentação e oferta de aprofundamento | — |

O template do dashboard é escolhido automaticamente:

- **executivo-clean** — decisões + ações + participantes seniores
- **tecnico-denso** — arquitetura, sistemas, findings técnicos
- **retrospectiva-warm** — retrospectivas, sentimento em primeiro plano
- **minimalista-editorial** — estratégia reflexiva, citações longas

Empate → `executivo-clean`.

### Regras duras do slash command

Documentadas em `.claude/commands/analisar-reuniao.md` seção 6.8:

- HTML 100% self-contained: sem CDN, sem Chart.js, sem `<canvas>`.
- Todos os gráficos em HTML+CSS: barras via `width: N%`, donuts via `conic-gradient`, bubbles via `position: absolute`, sparklines via `<svg>` inline.
- `<meta name="color-scheme" content="light">` obrigatório (evita inversão automática em dark mode do iOS).
- Transcrição embutida direto no HTML (não em string JS).
- JS apenas como progressive enhancement (ex.: busca na transcrição).
- Nenhum emoji nos artefatos.

---

## Skills complementares

Cada skill vive em `.claude/skills/<nome>/SKILL.md` e pode ser invocada via `Skill` tool dentro do Claude Code. Operam sobre pastas `analise_*/` já existentes, salvo onde indicado.

| Skill | Input | Output | Quando usar |
|-------|-------|--------|-------------|
| `gerar-ata-formal` | pasta `analise_*/` | `ata_formal.html` (A4 institucional, linhas de assinatura) | Atas corporativas/institucionais |
| `gerar-pdf-reuniao` | `*.html` (dashboard, ata, slides) | `*.pdf` (A4 via Chrome headless) | Distribuição por email/impressão |
| `gerar-slides` | pasta `analise_*/` | `slides.html` (scroll-snap, 1 slide por página) | Apresentação executiva rápida |
| `analisar-rapido` | áudio/vídeo novo | pasta `analise_*/` com `transcricao.vtt` + markdown curto (sem dashboard) | Reuniões de rotina |
| `analisar-decisoes` | áudio/vídeo OU pasta existente | `adr_*.md` (Architecture Decision Record) | Log de decisões técnicas |
| `analisar-1on1` | áudio/vídeo | pasta `analise_1on1_*/` (foco em rapport, compromissos pessoais, feedback) | 1:1, mentoria, review |
| `comparar-reunioes` | 2+ pastas `analise_*/` | `comparacao_*.html` (diff lado a lado) | Evolução de tema ao longo do tempo |
| `consolidar-acoes` | todas as pastas `analise_*/` | `acoes_consolidadas_YYYY-MM-DD.html` | Follow-up cross-reunião |

---

## Templates de dashboard

`.claude/templates/` é uma biblioteca de 4 HTMLs autocontidos que servem como base visual para o dashboard. O catálogo, a regra de escolha e as regras de adaptação estão em `.claude/templates/README.md`.

Todos seguem as mesmas restrições do slash command (light mode, CSS-only, sem CDN, transcrição embutida). Ao adaptar:

1. Preserve identidade visual (paleta, tipografia, densidade).
2. Substitua 100% dos dados de amostra por conteúdo real da transcrição.
3. Omita seções vazias (não deixe placeholders).
4. Mantenha todas as restrições não-negociáveis do `CLAUDE.md`.

---

## API REST

Base: `http://localhost:8000` (dev). O frontend usa `NEXT_PUBLIC_API_URL` via rewrite em `next.config.mjs` para encaminhar `/api/*`.

Swagger interativo: `http://localhost:8000/docs`.

### Autenticação

Todos os endpoints exceto `/health`, `POST /api/auth/login` e `POST /api/auth/refresh` exigem `Authorization: Bearer <access_token>`.

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/auth/login` | Body: `{email, password}`. Retorna `{access_token, refresh_token}` |
| POST | `/api/auth/refresh` | Body: `{refresh_token}`. Retorna novo par |
| GET | `/api/auth/me` | Retorna `{id, email, role}` do usuário autenticado |

### Provedores de LLM

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/settings/providers` | Lista credenciais (nunca devolve `api_key`, só `has_api_key: bool`) |
| PUT | `/api/settings/providers/{provider}` | Upsert `{default_model, enabled, api_key?}`. API key vazia mantém a atual |
| DELETE | `/api/settings/providers/{provider}` | Remove credencial |

### Whisper / estimativa

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/whisper/models?duration_s={int}` | Lista `[{name, eta_seconds, is_default}]`. ETA calibrada por `whisper_benchmarks` |

### Jobs

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/jobs` | `multipart/form-data`: `file`, `whisper_model`, `llm_provider`, `llm_model`. Retorna `{id}` |
| GET | `/api/jobs` | Lista 100 mais recentes do usuário |
| GET | `/api/jobs/{id}` | Detalhe (inclui `folder_name` quando `status=done`) |
| DELETE | `/api/jobs/{id}` | Remove job e arquivos |

### Stream de progresso

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/jobs/{id}/events` | `text/event-stream` (SSE). Primeiro evento é snapshot; emite um evento por transição de fase. Fecha quando `phase=done` ou `level=error` |

### Artefatos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/jobs/{id}/artifacts/{name}` | `name` whitelist: `transcricao.vtt`, `analise.md`, `dashboard.html` |

### Health

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/health` | `{ok: true}` |

### Modelo Job (estados)

- `status`: `queued` → `running` → (`done` | `error` | `canceled`)
- `phase`: `validating` → `extracting_audio` → `transcribing` → `analyzing` → `rendering` → `done`
- `progress_pct`: 0–100

---

## Provedores de LLM

Quatro drivers implementando `AnalysisProvider` em `backend/app/services/analysis/`:

| Provider | Driver | Requer API key | Observação |
|----------|--------|----------------|------------|
| `anthropic` | `AsyncAnthropic` | sim | Modelos Claude (default `claude-opus-4-6`) |
| `openai` | `AsyncOpenAI` | sim | GPT-4o etc |
| `openrouter` | `AsyncOpenAI` com `base_url=https://openrouter.ai/api/v1` | sim | Roteador multi-provider |
| `claude_cli` | subprocess do `@anthropic-ai/claude-code` | não (usa `~/.claude.json`) | Precisa do CLI autenticado no host; volumes já montados pelo `docker-compose.yml` |

Todos os providers devolvem o mesmo `AnalysisResult` (definido em `app/services/analysis/schemas.py`), que os renderers (`markdown.py`, `dashboard.py`) consomem sem saber qual driver foi usado.

Prompts e `SYSTEM_PROMPT` centralizados em `app/services/analysis/prompts.py` — ao ajustar a qualidade da análise, edite ali (afeta os quatro providers simultaneamente).

---

## Desenvolvimento

### Hot reload

Os bind-mounts do `docker-compose.yml` mantêm:

- `./backend:/app` → `uvicorn --reload` refaz imports a cada save.
- `./frontend:/app` → `next dev` recarrega o navegador.

Alguns arquivos exigem restart manual:
- `pyproject.toml` — rebuild do container: `docker compose build api worker`.
- `package.json` — rebuild do web: `docker compose build web`.
- `alembic.ini` e novas migrations — aplicar via `docker compose exec api alembic upgrade head`.

### Migrations

```bash
# criar nova revisão
docker compose exec api alembic revision -m "add coluna x" --autogenerate

# aplicar
docker compose exec api alembic upgrade head

# downgrade uma revisão
docker compose exec api alembic downgrade -1
```

A migration `0001_initial` cria todas as tabelas e o trigger `notify_job_event()` que emite `NOTIFY job_event` em cada `INSERT` em `job_events`.

### Acessar o banco

```bash
docker compose exec postgres psql -U ata -d ata

# ver jobs recentes
SELECT id, status, phase, progress_pct, created_at FROM jobs ORDER BY created_at DESC LIMIT 10;

# ver eventos de um job
SELECT ts, phase, progress_pct, level, message FROM job_events WHERE job_id = '...' ORDER BY ts;

# recalibrar estimativas
SELECT whisper_model, AVG(wall_time_s::float / audio_duration_s) AS ratio 
FROM whisper_benchmarks 
GROUP BY whisper_model;
```

### Executar testes (opcional)

Deps em `[project.optional-dependencies.dev]` — `pytest`, `pytest-asyncio`, `pytest-httpx`, `mypy`, `ruff`.

```bash
docker compose exec api pytest
docker compose exec api ruff check app
docker compose exec api mypy app
```

### Scripts npm (frontend)

```bash
docker compose exec web npm run lint
docker compose exec web npm run build   # build de produção
```

### Parar tudo

```bash
docker compose down             # mantém volumes (pg_data)
docker compose down -v          # remove volumes (perde dados)
```

---

## Troubleshooting

### O upload de vídeo retorna 413 (Payload Too Large)

Ajuste `MAX_UPLOAD_MB` no `.env` e reinicie o `api`. Se estiver atrás de um proxy (nginx/Traefik), aumente também `client_max_body_size` do proxy.

### O worker fica em `transcribing` muito tempo

Whisper roda em CPU por padrão (sem CUDA no container slim). Duração em CPU ~1× a 3× o tempo do áudio, dependendo do modelo (`medium` é ~2× em Apple Silicon). Para acelerar:

- Use modelo `small` ou `tiny` no upload.
- Rode fora do Docker com GPU habilitada (comentar o serviço `worker` no compose e executar `python -m app.workers.main` local com torch+CUDA).

### `claude_cli provider` não funciona dentro do Docker

Verifique se:
- Os volumes `${HOME}/.claude:/root/.claude:ro` e `${HOME}/.claude.json:/root/.claude.json:ro` estão montados (já estão no `docker-compose.yml`).
- O CLI local está autenticado (`claude auth login` no host antes de subir o stack).

### SSE não chega no frontend

- Confirme que o reverse proxy (se houver) não está buffering. O endpoint já envia `X-Accel-Buffering: no`, mas alguns proxies ignoram.
- Verifique logs do `api` em busca de erros de `LISTEN/NOTIFY`.
- Abra o devtools → Network → filtrar por `events` → o request deve ficar `pending` com chunks chegando.

### Slash command falha em "Whisper não encontrado"

```bash
which python3
# Se não retornar /Library/Frameworks/Python.framework/Versions/Current/bin/python3, instale o Python.org ou ajuste os paths no comando.

/Library/Frameworks/Python.framework/Versions/Current/bin/python3 -c "import whisper"
# Se der ImportError:
/Library/Frameworks/Python.framework/Versions/Current/bin/pip3 install openai-whisper torch
```

### O dashboard abre com texto branco/ilegível

É a inversão automática de dark mode do iOS/Chrome Android. O arquivo deveria ter `<meta name="color-scheme" content="light">` e `color-scheme: light` no `:root`. Se gerou manualmente e essas linhas sumiram, recolocar — são regras não-negociáveis do projeto.

### Erros de CORS no frontend

`CORSMiddleware` do FastAPI permite apenas `http://localhost:3000`. Em outro hostname ou produção, edite `app/main.py` e rebuild o `api`.

---

## Documentação adicional

- `CLAUDE.md` — guia de navegação para o Claude Code operar no repositório (descreve o slash command e as convenções).
- `.claude/commands/analisar-reuniao.md` — pipeline completo do slash command (fases 0–7, CSS do dashboard, templates de componente, regras).
- `.claude/templates/README.md` — catálogo de templates de dashboard e regras de escolha/adaptação.
- `.claude/skills/*/SKILL.md` — frontmatter com `description` e `when_to_use` de cada skill.
- `docs/superpowers/plans/` — planos de implementação datados (ex.: `2026-04-11-sistema-web-ata-ai.md`).
- `docs/superpowers/specs/` — specs de design (stack, DB, fluxos de dados).

---

## Licença e autoria

Repositório: https://github.com/edilsonborges/ata.ai  
Mantenedor: Edilson Borges
