# Sistema Web ata.ai — Design

**Data**: 2026-04-11
**Status**: Aprovado (brainstorming)
**Escopo**: Transformar o pipeline de `/analisar-reuniao` (hoje um slash command do Claude Code) em uma aplicação web full-stack com upload, fila de jobs, progresso em tempo real, múltiplos provedores LLM e histórico persistente.

---

## 1. Objetivo

Hoje o `ata.ai` é um repositório puramente baseado em Claude Code — a "lógica" vive em `.claude/commands/analisar-reuniao.md`. Quando um usuário quer analisar uma reunião, ele invoca o slash command, o Claude executa o pipeline (validação → ffmpeg → whisper → análise → render), e escreve a pasta `analise_*` na raiz do repo.

O objetivo deste spec é criar uma **aplicação web completa** que execute esse mesmo pipeline sem depender do Claude Code na máquina do usuário, com:

- Upload por interface gráfica (arrastar e soltar)
- Fila de processamento assíncrona com progresso em tempo real
- Escolha do modelo Whisper com **previsão de tempo** calibrada dinamicamente
- Escolha do provedor LLM (Anthropic API, OpenAI, OpenRouter, Claude CLI local)
- Histórico persistente de análises com download dos artefatos
- Autenticação JWT
- Deploy via `docker compose up`

O slash command atual **continua existindo** para uso "offline" direto no Claude Code; o sistema web é complementar, não substituto.

---

## 2. Stack

| Camada        | Tecnologia                                        |
|---------------|---------------------------------------------------|
| Backend API   | Python 3.12 + FastAPI + SQLModel (sobre SQLAlchemy) |
| Worker        | Python 3.12 + `arq` (fila em Postgres via LISTEN/NOTIFY) |
| Migrations    | Alembic                                           |
| Banco         | PostgreSQL 16                                     |
| Frontend      | Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui |
| Auth          | JWT (access+refresh) + bcrypt                     |
| Progresso     | Server-Sent Events (SSE) alimentados por `LISTEN/NOTIFY` |
| Transcrição   | `openai-whisper` (Python, CPU)                    |
| LLMs          | `anthropic`, `openai`, `openrouter` via SDK oficial + subprocess do `claude` CLI |
| Orquestração  | Docker Compose                                    |

**Por que Postgres para fila em vez de Redis**: o Postgres já é dependência obrigatória (histórico + users + settings). Usar `LISTEN/NOTIFY` para alimentar o `arq` e para emitir eventos SSE elimina um container e um ponto de falha. Mantém o compose em 4 serviços.

---

## 3. Estrutura do repositório

```
ata.ai/
├─ .claude/commands/analisar-reuniao.md     # mantido, inalterado
├─ backend/
│  ├─ pyproject.toml
│  ├─ Dockerfile                            # worker+api no mesmo image
│  ├─ alembic.ini
│  ├─ migrations/
│  └─ app/
│     ├─ main.py                            # FastAPI entrypoint
│     ├─ config.py                          # Settings via pydantic-settings
│     ├─ db.py                              # engine + session
│     ├─ security.py                        # JWT + bcrypt + Fernet
│     ├─ models/                            # SQLModel classes
│     │  ├─ user.py
│     │  ├─ job.py
│     │  ├─ provider_credential.py
│     │  └─ whisper_benchmark.py
│     ├─ schemas/                           # Pydantic request/response
│     ├─ routers/
│     │  ├─ auth.py
│     │  ├─ jobs.py
│     │  ├─ events.py                       # SSE
│     │  ├─ settings.py                     # provider credentials
│     │  └─ artifacts.py                    # download dos arquivos
│     ├─ services/
│     │  ├─ storage.py                      # abstração sobre ./storage
│     │  ├─ ffprobe.py                      # duração do áudio/video
│     │  ├─ whisper_runner.py               # wrapper do whisper + progresso
│     │  ├─ analysis/
│     │  │  ├─ base.py                      # interface Provider
│     │  │  ├─ anthropic_provider.py
│     │  │  ├─ openai_provider.py
│     │  │  ├─ openrouter_provider.py
│     │  │  └─ claude_cli_provider.py
│     │  ├─ renderer/
│     │  │  ├─ markdown.py                  # analise.md
│     │  │  └─ dashboard.py                 # dashboard.html (sem JS pra dados)
│     │  └─ benchmark.py                    # calibração de ETA do whisper
│     ├─ workers/
│     │  ├─ main.py                         # arq worker boot
│     │  └─ pipeline.py                     # função processa_reuniao()
│     └─ seed.py                            # cria admin na primeira subida
├─ frontend/
│  ├─ package.json
│  ├─ Dockerfile
│  ├─ next.config.mjs
│  ├─ tailwind.config.ts
│  └─ src/
│     ├─ app/
│     │  ├─ (auth)/login/page.tsx
│     │  ├─ (app)/layout.tsx                # shell autenticado
│     │  ├─ (app)/page.tsx                  # lista de análises
│     │  ├─ (app)/upload/page.tsx           # nova análise
│     │  ├─ (app)/jobs/[id]/page.tsx        # progresso + resultado
│     │  └─ (app)/settings/page.tsx         # provider credentials
│     ├─ lib/api.ts                         # fetch client autenticado
│     ├─ lib/auth.ts                        # JWT cookie + refresh
│     └─ components/
│        ├─ UploadDropzone.tsx
│        ├─ WhisperModelPicker.tsx          # com ETA
│        ├─ ProviderPicker.tsx
│        ├─ JobProgress.tsx                 # consome SSE
│        └─ DashboardIframe.tsx
├─ docker-compose.yml
├─ .env.example
├─ storage/                                 # volume persistente (gitignored)
│  ├─ uploads/
│  └─ analyses/
└─ docs/superpowers/specs/2026-04-11-sistema-web-ata-ai-design.md
```

As pastas `analise_*` que já existem na raiz são **mantidas intactas** (são saídas históricas do slash command). O novo sistema escreve em `storage/analyses/`.

---

## 4. Banco de dados

### 4.1 Tabelas

**users**
```
id               uuid pk
email            text unique
password_hash    text
role             text  -- 'admin' | 'member'
created_at       timestamptz
```

**provider_credentials** (por usuário, criptografadas)
```
id               uuid pk
user_id          uuid fk -> users.id
provider         text  -- 'anthropic' | 'openai' | 'openrouter' | 'claude_cli'
api_key_encrypted bytea nullable    -- Fernet; null para claude_cli
default_model    text  -- ex: 'claude-opus-4-6', 'gpt-4o', 'anthropic/claude-3.5-sonnet'
enabled          bool
created_at       timestamptz
```

**jobs**
```
id               uuid pk
user_id          uuid fk -> users.id
status           text  -- 'queued'|'running'|'done'|'error'|'canceled'
phase            text  -- 'validating'|'extracting_audio'|'transcribing'|'analyzing'|'rendering'|'done'
progress_pct     smallint  -- 0..100
eta_seconds      int nullable
input_filename   text
input_size_bytes bigint
media_duration_s int nullable
whisper_model    text  -- 'tiny'|'base'|'small'|'medium'|'large-v3'
llm_provider     text
llm_model        text
folder_name      text nullable  -- analise_{data}_{hora}_{slug}
error_message    text nullable
created_at       timestamptz
started_at       timestamptz nullable
finished_at      timestamptz nullable
```

**job_events** (append-only, alimenta SSE e log visual)
```
id               bigserial pk
job_id           uuid fk -> jobs.id
ts               timestamptz default now()
phase            text
progress_pct     smallint
message          text
level            text  -- 'info'|'warn'|'error'
```

**whisper_benchmarks**
```
id               bigserial pk
whisper_model    text
audio_duration_s int
wall_time_s      int
hostname         text  -- identifica o container; permite separar calibrações por máquina
created_at       timestamptz
```

### 4.2 Índices relevantes

- `jobs(user_id, created_at desc)` — listagem
- `job_events(job_id, id)` — tail de eventos
- `whisper_benchmarks(whisper_model, created_at desc)` — média móvel

### 4.3 NOTIFY

Trigger em `job_events` emite `pg_notify('job:<job_id>', payload_json)` em cada INSERT. A API escuta via um listener global e multiplexa para as conexões SSE abertas.

---

## 5. Pipeline do worker

Função `processa_reuniao(job_id)` executada pelo `arq`:

| # | Fase              | % início | % fim | Ação |
|---|-------------------|----------|-------|------|
| 1 | `validating`       | 0        | 5     | Confere existência, extensão, tamanho máx (configurável). `ffprobe` para duração |
| 2 | `extracting_audio` | 5        | 15    | Só se vídeo. `ffmpeg -vn -acodec pcm_s16le -ar 16000 -ac 1` |
| 3 | `transcribing`     | 15       | 70    | `whisper.load_model(modelo).transcribe(...)`. Progresso via callback por segmento: `pct = 15 + (segment_end/total_duration) * 55`. Grava também em `whisper_benchmarks` ao concluir |
| 4 | `analyzing`        | 70       | 90    | Provider LLM escolhido recebe transcrição + segmentos e retorna JSON estruturado (resumo, tópicos, decisões, findings, ações, riscos, timeline, entidades, sentimento, palavras-chave, insights) |
| 5 | `rendering`        | 90       | 98    | Gera `analise.md` e `dashboard.html` (HTML+CSS puros, sem JS para dados, seguindo as regras rígidas do CLAUDE.md) |
| 6 | `done`             | 98       | 100   | Move artefatos para `storage/analyses/<folder>/`, atualiza `jobs.status = done` |

Cada transição escreve em `job_events`, que dispara NOTIFY, que chega ao cliente via SSE.

**Erro em qualquer fase**: `status='error'`, `error_message` preenchido, evento `level='error'` emitido, SSE envia evento final e fecha.

---

## 6. Providers LLM

Interface comum em `app/services/analysis/base.py`:

```python
class AnalysisProvider(Protocol):
    async def analyze(
        self,
        transcript: str,
        segments: list[Segment],
        model: str,
    ) -> AnalysisResult: ...
```

Onde `AnalysisResult` é um Pydantic model com todos os campos que o renderer precisa. O prompt é o mesmo para todos os providers, extraído de `.claude/commands/analisar-reuniao.md` (Fase 3) e armazenado em `app/services/analysis/prompts.py`.

### 6.1 `anthropic_provider`
SDK oficial `anthropic`. Usa prompt caching (cache da instrução + schema; transcrição varia). Modelo default configurável.

### 6.2 `openai_provider`
SDK oficial `openai`. Usa `response_format={"type":"json_schema"}` para garantir saída estruturada.

### 6.3 `openrouter_provider`
SDK `openai` apontado para `https://openrouter.ai/api/v1`. Modelos no formato `<provider>/<model>`.

### 6.4 `claude_cli_provider`
Executa via subprocess:
```python
proc = await asyncio.create_subprocess_exec(
    "claude", "-p", prompt,
    "--model", model,              # ex: 'claude-opus-4-6'
    "--output-format", "json",
    stdout=PIPE, stderr=PIPE,
    env={...}  # ANTHROPIC_API_KEY não setada — usa sessão montada
)
```
`-p` entrega o prompt em modo non-interactive; `--model` escolhe o modelo; `--output-format json` devolve um envelope estruturado cujo campo `result` contém o markdown/JSON da resposta. Funciona porque o container monta `~/.claude` do host como `:ro` (ver §8.2).

---

## 7. API HTTP

Prefixo `/api`. Todos endpoints autenticados requerem `Authorization: Bearer <access_token>`.

| Método | Rota                           | Descrição |
|--------|--------------------------------|-----------|
| POST   | `/auth/login`                  | email+senha → `{access, refresh}` |
| POST   | `/auth/refresh`                | refresh token → novo access |
| GET    | `/auth/me`                     | usuário atual |
| GET    | `/settings/providers`          | lista credenciais do usuário (sem a key) |
| PUT    | `/settings/providers/{provider}` | upsert credencial (criptografa) |
| DELETE | `/settings/providers/{provider}` | remove |
| GET    | `/whisper/models`              | retorna modelos disponíveis + ETA para uma `duration_s` no query string |
| POST   | `/jobs`                        | multipart upload → cria job `queued` e retorna `{id}` |
| GET    | `/jobs`                        | lista paginada |
| GET    | `/jobs/{id}`                   | detalhe (inclui eventos recentes) |
| DELETE | `/jobs/{id}`                   | deleta registro + arquivos |
| GET    | `/jobs/{id}/events` *(SSE)*    | stream de progresso |
| GET    | `/jobs/{id}/artifacts/transcricao.vtt` | download |
| GET    | `/jobs/{id}/artifacts/analise.md`       | download |
| GET    | `/jobs/{id}/artifacts/dashboard.html`   | serve o HTML estático (iframe) |

### 7.1 Cálculo de ETA (`/whisper/models`)

```
fator_modelo_default = {
    'tiny': 0.08, 'base': 0.15, 'small': 0.30,
    'medium': 0.60, 'large-v3': 1.20
}

def eta(modelo, duration_s):
    hist = SELECT avg(wall_time_s::float / audio_duration_s)
           FROM whisper_benchmarks
           WHERE whisper_model = modelo
             AND hostname = current_hostname
           ORDER BY created_at DESC LIMIT 10
    fator = hist if hist else fator_modelo_default[modelo]
    return int(duration_s * fator)
```

A UI mostra na hora do upload a tabela:
```
tiny     ~12s
base     ~22s
small    ~45s
medium   ~1m30s    ← default
large-v3 ~3m
```

---

## 8. Docker Compose

### 8.1 Serviços

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ata
      POSTGRES_USER: ata
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck: pg_isready

  api:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    depends_on:
      postgres: {condition: service_healthy}
    environment:
      DATABASE_URL: postgresql+asyncpg://ata:${POSTGRES_PASSWORD}@postgres/ata
      JWT_SECRET: ${JWT_SECRET}
      FERNET_KEY: ${FERNET_KEY}
      ADMIN_EMAIL: ${ADMIN_EMAIL}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
    volumes:
      - ./storage:/app/storage
    ports: ["8000:8000"]

  worker:
    build: ./backend
    command: python -m app.workers.main
    depends_on:
      postgres: {condition: service_healthy}
    environment: *api_env
    volumes:
      - ./storage:/app/storage
      - ${HOME}/.claude:/root/.claude:ro       # Claude CLI sessão
      - ${HOME}/.claude.json:/root/.claude.json:ro

  web:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports: ["3000:3000"]
    depends_on: [api]

volumes:
  pg_data:
```

### 8.2 Dockerfile do backend (api+worker)

Imagem única para api e worker (comando sobrescreve no compose):

```dockerfile
FROM python:3.12-slim

# ffmpeg, curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl ca-certificates gnupg && rm -rf /var/lib/apt/lists/*

# Node.js 20 + Claude Code CLI (usado pelo claude_cli_provider no worker)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y nodejs \
 && npm install -g @anthropic-ai/claude-code

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# pre-baixa modelos do whisper para acelerar primeiro job
# (opcional; pode ser ativado por build arg)

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.3 `.env.example`

```
POSTGRES_PASSWORD=change-me
JWT_SECRET=change-me-use-a-long-random-string
FERNET_KEY=                 # gere com python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ADMIN_EMAIL=admin@edilson.dev
ADMIN_PASSWORD=ksjao10so!
```

O seed (`app/seed.py`) cria o usuário admin na primeira subida caso a tabela `users` esteja vazia.

---

## 9. Frontend

Next.js App Router. Design usa a paleta do projeto (indigo `#4f46e5`, gradient header) via Tailwind config.

### 9.1 Telas

**/login** — email+senha, POST `/api/auth/login`, guarda access em memória e refresh em cookie httpOnly. Redireciona para `/`.

**/** — Dashboard com lista de análises (tabela: data, arquivo, status badge, duração, modelo whisper, provider) + botão "Nova análise". Linha clicável vai para `/jobs/{id}`.

**/upload** — Etapas visuais:
1. Dropzone. Ao soltar arquivo, chama endpoint auxiliar que roda `ffprobe` rápido (sub-segundo) e retorna duração.
2. Picker de modelo Whisper. Mostra ETA calculada para cada modelo.
3. Picker de provider LLM (só mostra providers com `enabled=true` em settings).
4. Botão "Processar" → POST `/api/jobs` (multipart) → redireciona para `/jobs/{id}`.

**/jobs/[id]** — Tela de progresso:
- Cabeçalho com nome do arquivo + status + % + ETA restante
- Barra de progresso
- Log visual (lista dos `job_events` mais recentes)
- Consome SSE de `/api/jobs/{id}/events` via `EventSource`
- Quando `status=done`: renderiza `DashboardIframe` apontando para `/api/jobs/{id}/artifacts/dashboard.html` + botões de download dos 3 artefatos
- Quando `status=error`: mostra mensagem de erro + botão "Reprocessar"

**/settings** — Página de configurações. Cards por provider com:
- Toggle enabled
- Input para API key (mostrado como password, pré-preenchido mascarado se já existe)
- Select do modelo default
- Botão "Testar conexão" (chama endpoint que faz um ping mínimo no provider)

Para `claude_cli`, não tem campo de API key — só toggle + modelo default (o worker passa `--model` ao `claude` CLI).

### 9.2 Autenticação

JWT em cookie httpOnly para refresh; access token fica em memória do cliente e é renovado automaticamente pelo fetch wrapper quando recebe 401. Middleware do Next.js protege `(app)/*`.

---

## 10. Regras que o renderer deve respeitar

Copiadas de `CLAUDE.md` — o `dashboard.py` tem que cumprir:

- Self-contained, **sem JavaScript para exibir dados**. Gráficos todos em HTML + CSS: barras via `width: %`, donuts via `conic-gradient`, bubbles via `position: absolute`, sparklines via SVG inline estático. JS permitido apenas como progressive enhancement (busca na transcrição) e a página deve funcionar sem ele.
- `<meta name="color-scheme" content="light">` e `color-scheme: light` no `:root`.
- Paleta fixa: primário `#4f46e5`, gradient `linear-gradient(135deg, #312e81, #4f46e5, #7c3aed)`. Semânticas: verde decisão, vermelho problema, âmbar finding, azul info, roxo construtivo.
- Ordem de seções: Meta → Sentimento → Participantes → Tópicos → Entidades → Fluxo → Timeline → Insights/Decisões → Matriz de risco → Ações → Transcrição com busca → Footer.
- Classes semânticas: `insight-card` com `decisao|finding|problema|acao`; `timeline-item` com `positive|neutral|concern|constructive`; `tag` com `tag-sistema|tag-orgao|tag-tech|tag-ferramenta|tag-pessoa`.
- Seções vazias omitidas, nunca deixadas em branco.
- Transcrição renderizada direto no HTML (não em template string JS).
- Nunca inventar dados. Tudo em português brasileiro. Sem emojis.
- Timestamps literais `[MM:SS]` nas citações.

O `markdown.py` segue o mesmo template de `analise.md` que o slash command usa hoje.

---

## 11. Fora de escopo

Deliberadamente **não fazem parte** deste spec:

- Multi-tenancy real (org, convites, billing).
- Rate limiting / quotas.
- OAuth (Google/GitHub).
- Processamento via GPU (só CPU, como hoje).
- Suporte a idiomas diferentes de pt-BR.
- Streaming de upload chunked para arquivos >1 GB (limite inicial: 500 MB via `multipart`).
- Compartilhamento público de análises por link.
- Edição manual do conteúdo da análise após gerada.
- Webhooks / integrações externas.
- Observabilidade (métricas, tracing) — só logs estruturados em stdout.

Cada um desses pode virar um spec separado no futuro.

---

## 12. Critérios de aceite

O sistema está "pronto" quando:

1. `docker compose up` sobe os 4 serviços sem erro e o admin é criado automaticamente.
2. Login com `admin@edilson.dev` + senha do `.env` funciona.
3. Upload de um `.mp4` de reunião (usar a existente em `analise_11-04-2026_15-38-30_magistra-boletim-disciplinas/` como referência) dispara um job.
4. Página de progresso mostra fases mudando em tempo real via SSE.
5. ETA da primeira reunião é aproximada; a partir da segunda reunião no mesmo modelo, fica dentro de ±15% do tempo real.
6. Ao concluir, o dashboard renderizado em iframe abre e é visualmente equivalente ao que o slash command gera hoje (paleta, estrutura, sem JS para dados).
7. Os 3 artefatos (`transcricao.vtt`, `analise.md`, `dashboard.html`) são baixáveis.
8. Trocar o provider em settings (ex: Anthropic → OpenAI) e reprocessar funciona.
9. Derrubar o worker no meio de um job deixa o `status='error'` consistente (sem travar em `running`); ao reiniciar, o job pode ser reprocessado manualmente.
10. O slash command `/analisar-reuniao` antigo continua funcionando sem regressão.
