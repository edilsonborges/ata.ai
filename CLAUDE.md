# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é este repositório

`ata.ai` é um projeto **puramente baseado em Claude Code** — não tem código-fonte, `package.json`, testes, build ou CI. O repositório existe para hospedar e versionar slash commands customizados que transformam áudios/vídeos de reuniões em artefatos estruturados (transcrição, análise em markdown e dashboard HTML).

Toda a "lógica" do projeto vive dentro de arquivos `.md` em `.claude/commands/`, que são interpretados pelo próprio Claude Code quando o usuário invoca o comando correspondente no chat.

## Comando principal: `/analisar-reuniao`

Arquivo: `.claude/commands/analisar-reuniao.md`

Pipeline de 7 fases executado pelo próprio Claude via Bash:

1. **Validação** — checa existência e formato (`.mp4/.mov/.webm/.avi/.mkv` ou `.wav/.mp3/.m4a/.ogg/.flac`).
2. **Extração de áudio** (só para vídeo) — `ffmpeg` converte para WAV 16kHz mono em `/tmp/reuniao_audio.wav`.
3. **Transcrição Whisper** — modelo `medium`, idioma `pt`, gera VTT nativo + texto puro + segmentos JSON em `/tmp/reuniao_out/` e `/tmp/`.
4. **Análise de conteúdo** — Claude lê `/tmp/reuniao_transcript.txt` e `/tmp/reuniao_segments.json` e extrai resumo, tópicos, decisões, findings, ações, riscos, timeline, entidades, sentimento, palavras-chave e insights.
5. **Criação da pasta** — `analise_{DD-MM-YYYY}_{HH-MM-SS}_{slug}/` dentro da **raiz do próprio repositório `ata.ai`** (usa `$CLAUDE_PROJECT_DIR`, fallback `$PWD`). NÃO no diretório do arquivo de entrada nem no CWD atual.
6. **Geração de `analise.md` e `dashboard.html`** — dashboard é HTML self-contained com Chart.js via CDN.
7. **Apresentação** — lista arquivos criados e oferece aprofundar pontos.

## Dependências externas (paths absolutos obrigatórios)

O comando usa caminhos completos intencionalmente — não substitua por chamadas simples sem verificar:

- `/opt/homebrew/bin/ffmpeg` — extração de áudio de vídeos
- `/Library/Frameworks/Python.framework/Versions/Current/bin/python3` — deve ter `whisper` (openai-whisper) instalado

Se qualquer um faltar, o comando falha. Não há fallbacks.

## Convenções rígidas do dashboard HTML

A seção 6 de `analisar-reuniao.md` define um padrão visual **que não deve ser alterado sem motivo explícito**:

- **Self-contained sem JS para dados**: CSS inline, zero dependências externas (sem CDN, sem Chart.js). **JavaScript nunca é necessário para visualizar dados** — iOS Quick Look, iOS Files Preview e AirDrop preview desativam JS em HTMLs locais. Todos os gráficos devem ser HTML + CSS puros: barras com `width: N%`, donuts com `conic-gradient`, bubbles com `position: absolute`, sparklines com SVG inline estático. JS só existe como progressive enhancement (ex: busca na transcrição) e a página deve continuar legível sem ele. Transcrição vai **renderizada direto no HTML**, nunca em string JS.
- **Light mode forçado (mobile)**: `<meta name="color-scheme" content="light">` no `<head>` + `color-scheme: light` no `:root` do CSS. Sem isso, iOS Safari e Chrome Android em dark mode do sistema invertem cores automaticamente e o texto fica branco sobre fundo claro (ilegível). Inputs como `.search-input` precisam de `background` e `color` explícitos pelo mesmo motivo.
- **Paleta fixa**: primário indigo `#4f46e5`, gradient header `linear-gradient(135deg, #312e81, #4f46e5, #7c3aed)`. Cores semânticas: verde decisão, vermelho problema, âmbar finding, azul info, roxo construtivo.
- **Estrutura de seções na ordem**: Meta cards → Sentimento → Participantes → Tópicos → Entidades → Fluxo → Timeline → Insights/Decisões → Matriz de risco → Ações → Transcrição com busca → Footer.
- **Classes semânticas nomeadas**: `insight-card` usa `decisao|finding|problema|acao`; `timeline-item` usa `positive|neutral|concern|constructive`; `tag` usa `tag-sistema|tag-orgao|tag-tech|tag-ferramenta|tag-pessoa`.
- **Seções vazias são omitidas**, não deixadas em branco.
- **Transcrição embutida** como template string JS — escapar backticks, `${` e `\` (ou usar `JSON.stringify()` via Python).

## Regras não-negociáveis para geração de artefatos

Estas regras estão no final de `analisar-reuniao.md` e devem ser respeitadas em qualquer ajuste no comando:

- **Nunca inventar dados** que não estejam na transcrição. Se algo não foi abordado, omitir a seção ou marcar "Não identificado".
- **Sempre citar trechos literais** entre aspas com timestamp `[MM:SS]` quando relevante.
- **Nunca usar emojis** nos arquivos gerados (`transcricao.vtt`, `analise.md`, `dashboard.html`).
- **Todos os artefatos em português brasileiro**.
- **Pasta criada dentro da raiz do repositório `ata.ai`** (`$CLAUDE_PROJECT_DIR`), não no diretório do arquivo de entrada nem no CWD.
- **Slug kebab-case**, lowercase, sem acentos, 3-5 palavras.
- **Whisper não separa locutores** — participantes são inferidos por contexto e o dashboard/markdown devem deixar isso explícito ao leitor.

## Editando o comando

Ao modificar `.claude/commands/analisar-reuniao.md`:

- Mantenha a estrutura de fases numeradas — o comando é longo (~900 linhas) e a navegação depende disso.
- Mantenha os blocos de código Bash/Python **executáveis como estão**; Claude os copia literalmente durante a execução.
- Se alterar o CSS/HTML do dashboard, atualize tanto o "bloco CSS completo" (seção 6.3) quanto os templates de componente (seção 6.5) para não divergirem.
- A seção 6.8 ("Regras para geração do dashboard") funciona como checklist final — qualquer nova convenção visual deve ser adicionada lá.
