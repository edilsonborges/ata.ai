---
name: comparar-reunioes
description: Use quando precisar comparar duas ou mais reunioes para ver evolucao de topicos, decisoes que mudaram, acoes carregadas entre reunioes, e participantes recorrentes. Gera HTML com diff visual lado a lado.
---

# Comparar Reunioes

Voce e um analista comparativo. Compara 2 ou mais pastas `analise_*/` e gera um relatorio visual com:

- Topicos em comum e exclusivos de cada reuniao
- Decisoes que evoluiram ou foram revertidas
- Acoes carregadas de uma reuniao anterior para outra
- Participantes recorrentes
- Mudanca de sentimento/tom entre encontros

## Objetivo

Gerar `comparacao_YYYY-MM-DD_HH-MM-SS.html` na **raiz do repositorio** com visualizacao lado a lado (2 colunas) ou matriz (3+ reunioes).

## Fase 0: Selecionar reunioes para comparar

1. Se `$ARGUMENTS` contem caminhos de pastas separados por espaco/virgula, usar.
2. Se vazio, listar as **5 mais recentes** e perguntar ao usuario quais comparar (minimo 2, maximo 4).

```bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
ls -1d "$PROJECT_DIR"/analise_* 2>/dev/null | sort -r | head -10
```

Validar:
- Minimo 2 pastas
- Maximo 4 pastas (acima disso usar `consolidar-acoes` ou `tendencias`)
- Todas devem conter `analise.md`

## Fase 1: Extrair dados de cada reuniao

Para cada pasta selecionada, ler `analise.md` e extrair:

- Titulo
- Data e duracao
- Participantes (lista de nomes)
- Resumo executivo
- Topicos discutidos (com relevancia)
- Decisoes tomadas (lista numerada)
- Findings
- Acoes pendentes
- Riscos
- Sentimento/tom

Estruturar como JSON temporario `/tmp/comparacao_raw.json`.

## Fase 2: Calcular diffs

### 2.1 Participantes

- **Comum a todas**: intersecao
- **Exclusivos**: diferenca por reuniao

### 2.2 Topicos

- Normalizar titulos (lower + sem acentos)
- **Comum**: topicos que aparecem em 2+ reunioes (match por similaridade simples — palavras-chave em comum)
- **Exclusivos**: topicos que so aparecem em uma
- Para topicos comuns, mostrar relevancia em cada reuniao (evolucao)

### 2.3 Decisoes

- Listar todas as decisoes de todas as reunioes lado a lado
- Marcar decisoes que **contradizem** uma anterior (palavras-chave: "reverter", "nao mais", "em vez de", "voltamos atras", "mudamos", "decisao revertida")
- Marcar decisoes que **continuam** uma anterior (mesma palavra-chave de topico)

### 2.4 Acoes

- Para cada acao da reuniao mais antiga, procurar referencia na mais recente
- Status provavel: pendente (nao mencionada), em andamento (mencionada com avanco), concluida (status "Concluida"), revertida (decisao contraria)

### 2.5 Sentimento

- Extrair "Sentimento e Dinamica" de cada analise.md
- Mostrar lado a lado se mudou (ex: "Construtivo → Tenso", "Alinhado → Alinhado")

## Fase 3: Layout HTML comparativo

### 3.1 Estrutura (2 reunioes)

```
Header (gradient indigo)
├─ Titulo: "Comparacao de Reunioes"
├─ Subtitulo: "{N} reunioes comparadas"

Meta cards (grid-4)
├─ Reunioes comparadas: {N}
├─ Topicos em comum: {count}
├─ Decisoes evoluidas: {count}
├─ Participantes recorrentes: {count}

Secao "Visao geral lado a lado" (grid-2)
├─ Card reuniao A: titulo, data, duracao, resumo
├─ Card reuniao B: titulo, data, duracao, resumo

Secao "Topicos"
├─ Comuns (tabela: topico, relevancia A, relevancia B, evolucao)
├─ Exclusivos A (lista)
├─ Exclusivos B (lista)

Secao "Decisoes" (timeline vertical)
├─ Item por decisao, cor por tipo:
│   Verde: nova decisao
│   Ambar: evoluiu
│   Vermelho: revertida
│   Azul: mantida

Secao "Acoes carregadas"
├─ Tabela: acao, reuniao A (status), reuniao B (status), evolucao

Secao "Participantes"
├─ Venn simples (texto/lista): comuns, so em A, so em B

Secao "Mudanca de tom"
├─ Card com sentimento A → B

Footer
```

### 3.2 Estrutura (3-4 reunioes) — modo matriz

Em vez de lado a lado, usar tabelas com colunas por reuniao:

```
| Topico         | Reuniao 1 (04/01) | Reuniao 2 (11/01) | Reuniao 3 (18/01) |
|----------------|--------------------|--------------------|--------------------|
| Boletim        | 30%                | 15%                | —                  |
| Nota por peso  | 25%                | —                  | 20%                |
```

### 3.3 CSS chave

Usar paleta do dashboard. Adicionar classes especificas:

```css
.comparison-grid {
  display: grid;
  grid-template-columns: repeat({N_REUNIOES}, 1fr);
  gap: 1rem;
}
.reuniao-col {
  background: var(--card);
  border-radius: var(--radius);
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
  border-top: 4px solid var(--accent);
}
.reuniao-col .data {
  font-size: .8rem;
  color: var(--text-muted);
  margin-bottom: .5rem;
}
.evolution-item {
  display: flex; align-items: center; gap: .6rem;
  padding: .5rem .8rem;
  border-radius: 8px;
  background: var(--card);
  margin-bottom: .4rem;
}
.evolution-item.up::before { content: '↑'; color: var(--green); font-weight: 700; }
.evolution-item.down::before { content: '↓'; color: var(--red); font-weight: 700; }
.evolution-item.stable::before { content: '→'; color: var(--blue); font-weight: 700; }
.evolution-item.new::before { content: '+'; color: var(--purple); font-weight: 700; }
.evolution-item.removed::before { content: '−'; color: var(--text-muted); font-weight: 700; }
.venn-section {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: .8rem;
}
.venn-col {
  background: var(--card);
  border-radius: var(--radius);
  padding: 1rem;
}
.venn-col h4 {
  font-size: .85rem;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: .5rem;
}
.decision-timeline .item {
  padding: .8rem 1rem;
  border-left: 4px solid;
  margin-bottom: .8rem;
  background: var(--card);
  border-radius: 0 8px 8px 0;
}
.decision-timeline .item.new { border-color: var(--green); }
.decision-timeline .item.evolved { border-color: var(--amber); }
.decision-timeline .item.reverted { border-color: var(--red); }
.decision-timeline .item.kept { border-color: var(--blue); }
.decision-timeline .item .meta {
  font-size: .75rem;
  color: var(--text-muted);
  margin-bottom: .2rem;
}
```

## Fase 4: Narrativa interpretativa

Antes do fechamento do HTML, incluir uma secao "Insights da Comparacao" com 3-5 bullets escritos pelo Claude analisando:

- Quais topicos ganharam/perderam relevancia
- Decisoes que foram revertidas e o motivo
- Acoes que nao foram cumpridas entre reunioes
- Mudanca de tom/dinamica
- Padroes de comportamento

Essa secao e a "interpretacao" — use linguagem clara e direta, sem inventar dados que nao estao nas analises.

## Fase 5: Salvar e reportar

```bash
OUTPUT="$PROJECT_DIR/comparacao_$(date +%Y-%m-%d_%H-%M-%S).html"
```

Informar:
- Reunioes comparadas (titulos + datas)
- Topicos em comum
- Decisoes revertidas encontradas
- Caminho do HTML

## Regras nao-negociaveis

- **Zero CDN, zero dependencia externa, zero JS para dados**: todos os diffs, tabelas e timelines devem vir renderizados **direto no HTML estatico**. Graficos (ex: barras de relevancia por reuniao) sao HTML + CSS puro (`width: N%`). Sem Chart.js, sem CDN, sem JSON injetado em JS. A pagina deve ser legivel em iOS Quick Look sem JS.
- **Minimo 2, maximo 4 reunioes** por comparacao. Acima disso, e tendencia, nao comparacao.
- **Match de topicos e heuristico** — baseado em palavras-chave e similaridade. Sinalizar explicitamente que e inferencia.
- **Nunca inventar evolucoes** — se nao ha sinal claro de que uma decisao foi revertida, classificar como "nova".
- **Respeitar ordem cronologica** — sempre mostrar reunioes da mais antiga para a mais recente (esquerda → direita).
- **Paleta identica ao dashboard**.
- **Modo light forcado**.
- **Nao alterar analise.md originais**.
- **Salvar na raiz do repo**, nao em pasta individual.
- **Se as reunioes forem muito diferentes** (zero topicos em comum), reportar isso explicitamente no topo do HTML: "Estas reunioes tem pouco overlap tematico — a comparacao pode ter valor limitado."
