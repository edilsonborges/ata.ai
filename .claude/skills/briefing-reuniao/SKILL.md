---
name: briefing-reuniao
description: Use quando precisar de um briefing contextual (1-pager) para preparar uma proxima reuniao, baseado em reunioes anteriores sobre um tema ou com um participante especifico. Varre todas as pastas analise_*, filtra por termo de busca e gera markdown + HTML com contexto historico, decisoes anteriores, acoes pendentes relacionadas e pontos em aberto.
---

# Briefing Pre-Reuniao

Voce e um assistente de preparacao. A partir de um **termo de filtro** (tema, participante, sistema), varre todas as pastas `analise_*/` do repositorio e produz um **briefing contextual** que uma pessoa pode ler em 2 minutos antes de entrar em uma reuniao.

## Objetivo

Gerar dois artefatos na **raiz do repositorio**:

1. `briefing_YYYY-MM-DD_{slug-tema}.md` — versao markdown (rapida de ler no editor)
2. `briefing_YYYY-MM-DD_{slug-tema}.html` — versao HTML self-contained (compartilhavel via AirDrop/preview)

## Fase 0: Coletar input

Perguntar ao usuario (se nao veio em `$ARGUMENTS`):

- **Termo de filtro** (obrigatorio) — pode ser:
  - Nome de pessoa: "Joao"
  - Sistema/tema: "boletim", "Magistra", "API de grades"
  - Organizacao: "STI", "Mei Poube"
- **Proximo encontro** (opcional) — data/objetivo da reuniao que esta sendo preparada

## Fase 1: Varrer pastas e filtrar

```bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
find "$PROJECT_DIR" -maxdepth 2 -type d -name "analise_*" | sort
```

Para cada pasta, ler `analise.md` e aplicar filtro:

**Regra de match** (case-insensitive, sem acentos):
- O termo aparece em qualquer campo textual? (titulo, resumo, topicos, decisoes, acoes, participantes, entidades, insights)
- Se sim, essa reuniao entra no briefing.

Extrair em cada match:
- Titulo + data + duracao
- Contexto especifico (trechos das secoes onde o termo apareceu)
- Decisoes relacionadas (buscar em "Decisoes Tomadas" por proximidade ao termo)
- Acoes relacionadas (tabela "Acoes e Proximos Passos", filtrar linhas onde o termo ou responsavel bate)
- Findings e riscos relacionados

## Fase 2: Consolidar e ordenar

Ordenar reunioes da **mais recente para mais antiga** (ordem cronologica inversa — o que importa e o contexto recente).

Calcular:

- Quantas reunioes matcharam
- Quantas decisoes cumulativas
- Quantas acoes ainda pendentes
- Pessoas-chave recorrentes
- Sistemas/ferramentas recorrentes

## Fase 3: Gerar `briefing_*.md`

Estrutura:

```markdown
# Briefing: {Tema ou Pessoa}

**Gerado em**: {YYYY-MM-DD HH:MM}
**Termo de filtro**: `{termo}`
**Reunioes encontradas**: {N}
**Proxima reuniao**: {se fornecida}

---

## TL;DR

{3-4 bullets com o essencial que a pessoa precisa saber para entrar na reuniao informada}

- {ponto 1 — ex: "Decisao X foi tomada em 10/04 mas nao foi implementada"}
- {ponto 2}
- {ponto 3}

## Contexto Historico

### Reuniao mais recente relacionada — {data}

**Titulo**: {titulo}
**O que foi discutido**: {resumo dos trechos relacionados ao tema}
**Decisoes**:
- {decisao 1}
- {decisao 2}

### Reuniao anterior — {data}

...

## Decisoes Cumulativas

1. **{decisao}** — tomada em {data} ({reuniao})
2. **{decisao 2}** — tomada em {data}

## Acoes Pendentes Relacionadas

| # | Acao | Responsavel | Prazo | Origem |
|---|------|-------------|-------|--------|
| 1 | {acao} | {resp} | {prazo} | {data - titulo reuniao} |

## Pontos em Aberto / Duvidas Pendentes

- **{pergunta 1}** — levantada em {data}, ainda sem resposta
- **{pergunta 2}**

## Pessoas-chave

- **{Nome}** — {papel, o que essa pessoa tem contribuido/questionado nas reunioes anteriores}

## Sistemas/Ferramentas Mencionados

{lista de entidades recorrentes}

## Sugestao de Pauta para Proxima Reuniao

1. {topico 1 — baseado em acoes pendentes}
2. {topico 2 — baseado em decisoes nao implementadas}
3. {topico 3 — baseado em duvidas em aberto}

---

*Briefing gerado a partir de {N} reunioes no repositorio ata.ai.*
*Fontes*:
- [analise_{DD-MM-YYYY}_..._{slug}](./analise_{DD-MM-YYYY}_..._{slug}/analise.md)
- [analise_..._{slug}](./analise_..._{slug}/analise.md)
```

## Fase 4: Gerar `briefing_*.html`

HTML self-contained seguindo as convencoes do projeto:

- **Zero CDN, zero JS para dados, zero dependencia externa**
- Paleta identica ao dashboard (indigo + semanticos)
- `<meta name="color-scheme" content="light">` + `color-scheme: light` no CSS
- Fontes system stack
- Layout 1-pager pensado para tela cheia ou preview do iOS

### 4.1 Estrutura HTML

```
<header class="header gradient-indigo">
  <div class="badge">Briefing</div>
  <h1>{Tema}</h1>
  <div class="meta">{N} reunioes · {acoes} acoes pendentes · gerado {data}</div>
</header>
<div class="container">

  <div class="tldr-card">
    <h3>TL;DR</h3>
    <ul>... bullets ...</ul>
  </div>

  <div class="grid-2">
    <div class="card">
      <h3>Decisoes Cumulativas</h3>
      ... lista numerada ...
    </div>
    <div class="card">
      <h3>Pontos em Aberto</h3>
      ... lista ...
    </div>
  </div>

  <div class="card">
    <h3>Acoes Pendentes Relacionadas</h3>
    <table> ... </table>
  </div>

  <h2 class="section-title">Contexto Historico</h2>
  <div class="timeline">
    <div class="timeline-item" data-date="10/04">
      <div class="date">10/04/2026</div>
      <div class="desc"><strong>{titulo}</strong> — {resumo}</div>
    </div>
  </div>

  <div class="card">
    <h3>Pessoas-chave</h3>
    ... tabela ou lista com tag-pessoa ...
  </div>

  <div class="card accent">
    <h3>Sugestao de Pauta</h3>
    <ol>... ...</ol>
  </div>

</div>
<footer> ... </footer>
```

### 4.2 CSS

Copiar base do `gerar-ata-formal`/dashboard adaptando para layout compacto (1-pager):

- `max-width: 900px` no container
- `.tldr-card` com border-left indigo espesso e fundo `--accent-light`
- Tabelas compactas
- Timeline estilo do dashboard mas mais densa

## Fase 5: Salvar e reportar

```bash
DATA=$(date +"%Y-%m-%d")
SLUG="{slug-do-termo-filtro}"
MD="$PROJECT_DIR/briefing_${DATA}_${SLUG}.md"
HTML="$PROJECT_DIR/briefing_${DATA}_${SLUG}.html"
```

Informar:
- Reunioes encontradas (lista curta de titulos)
- Caminhos dos dois arquivos
- Destaque: "Top prioridade ao entrar na reuniao: {X}"

## Regras nao-negociaveis

- **Minimo 1 reuniao** com match para gerar briefing. Se nenhuma bater, informar "Nenhuma reuniao anterior encontrada para o termo '{X}'."
- **Ordenacao cronologica inversa** (mais recente primeiro).
- **Nunca inventar contexto** — se uma pergunta foi feita mas nao respondida na transcricao, marcar "em aberto" literalmente.
- **Citar fonte (reuniao de origem)** em cada bullet de decisao ou acao.
- **Acoes pendentes** usam a mesma regra de `consolidar-acoes`: tudo que nao esta explicitamente como "Concluida".
- **Slug do tema** em kebab-case, lowercase, sem acentos.
- **Se o termo e um nome de pessoa**, priorizar contexto sobre o que essa pessoa pediu, decidiu ou levantou.
- **Se o termo e um sistema/modulo**, priorizar decisoes tecnicas e acoes de implementacao.
- **Zero JS para dados, zero CDN** — compatibilidade com iOS Quick Look.
- **Modo light forcado**.
- **Salvar na raiz do repo**.
