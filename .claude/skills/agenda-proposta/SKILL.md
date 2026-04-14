---
name: agenda-proposta
description: Use quando precisar gerar uma pauta sugerida para uma proxima reuniao, baseada em acoes pendentes e pontos em aberto de reunioes anteriores. Consolida tudo o que ainda nao foi resolvido e transforma em uma agenda executiva com tempo estimado por item e prioridade.
---

# Agenda Proposta

Voce e um facilitador de reunioes. Varre todas as pastas `analise_*/`, identifica acoes pendentes, pontos em aberto e decisoes nao implementadas, e produz uma **agenda sugerida** para a proxima reuniao, com tempo estimado por item e prioridade.

## Objetivo

Gerar `agenda_proposta_YYYY-MM-DD.md` (e opcionalmente `.html`) na **raiz do repositorio**, contendo:

- Lista ordenada de pontos a tratar
- Tempo estimado por item (total nao deve ultrapassar o tempo disponivel)
- Prioridade e motivo de cada item
- Quem precisa estar presente por item
- Referencia para reuniao(oes) de origem

## Fase 0: Coletar parametros

Perguntar ao usuario (se nao veio em `$ARGUMENTS`):

1. **Duracao da proxima reuniao** (obrigatorio) — ex: 30min, 1h, 1h30
2. **Tema/escopo** (opcional) — ex: "revisao Magistra", "retrospectiva sprint 42"
3. **Participantes esperados** (opcional) — para filtrar itens por quem estara presente

Se o usuario nao passar duracao, usar padrao de **1 hora**.

## Fase 1: Varrer e extrair pendencias

```bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
find "$PROJECT_DIR" -maxdepth 2 -type d -name "analise_*" | sort -r
```

Para cada `analise.md`, extrair:

### 1.1 Acoes pendentes

Regra igual ao `consolidar-acoes`: tudo que nao tem status em `['Concluida', 'Concluido', 'Feito', 'Done']`.

### 1.2 Decisoes "em aberto"

Buscar na secao "Decisoes Tomadas" por marcadores como:
- "depende de"
- "a confirmar"
- "a validar com"
- "pendente de"
- "aguardando"

### 1.3 Duvidas levantadas nao respondidas

Buscar na secao "Insights" e "Findings" por perguntas ou duvidas que nao foram resolvidas na transcricao. Usar heuristica: frases com "?", "precisa definir", "nao esta claro".

### 1.4 Acoes revertidas ou bloqueadas

Do `consolidar-acoes`: itens com status "Bloqueada", "Revertida", "Em pausa".

### 1.5 Riscos nao mitigados

Matriz de risco com probabilidade × impacto ≥ 50 (de 100). Se nao houver mitigacao documentada, entra na agenda.

## Fase 2: Filtrar por escopo (se fornecido)

Se o usuario passou um tema, filtrar usando a mesma heuristica do `briefing-reuniao` (match por termo normalizado).

## Fase 3: Ranquear itens

Score para ordenacao:

| Criterio | Peso |
|----------|------|
| Prioridade alta (acao/risco) | +50 |
| Bloqueando outras acoes | +30 |
| Mais de 2 reunioes em aberto | +25 |
| Duvida sem resposta | +20 |
| Risco prob*impacto ≥ 70 | +40 |
| Prioridade media | +15 |
| Prioridade baixa | +5 |

Ordenar descending. Quebrar empate por "prazo mais proximo".

## Fase 4: Alocar tempo

Regra de tempo por tipo:

| Tipo de item | Tempo minimo | Tempo maximo |
|--------------|--------------|--------------|
| Decisao tecnica | 10 min | 15 min |
| Review de acao pendente | 3 min | 5 min |
| Alinhamento de duvida | 5 min | 10 min |
| Risco a mitigar | 10 min | 15 min |
| Retrospectiva rapida | 5 min | 10 min |

**Buffer de 10%** para transicao entre itens. Abertura (2 min) e fechamento (3 min) fixos.

Algoritmo:

```
tempo_disponivel = duracao - abertura - fechamento - buffer_10%
itens_priorizados = itens ordenados por score
agenda = []
tempo_alocado = 0

para cada item em itens_priorizados:
    tempo_item = tempo_minimo_do_tipo
    se tempo_alocado + tempo_item <= tempo_disponivel:
        agenda.append(item com tempo_item)
        tempo_alocado += tempo_item
    senao:
        marcar como "para proxima reuniao"

# Segunda passada: ampliar itens ate tempo_maximo se sobra tempo
folga = tempo_disponivel - tempo_alocado
para cada item em agenda (por score desc):
    se folga > 0 e tempo_item < tempo_maximo_do_tipo:
        extra = min(folga, tempo_maximo - tempo_item)
        item.tempo += extra
        folga -= extra
```

## Fase 5: Gerar agenda_proposta_*.md

```markdown
# Agenda Proposta — {Tema ou "Reuniao Periodica"}

**Gerada em**: {YYYY-MM-DD HH:MM}
**Duracao planejada**: {duracao} ({tempo_alocado} min alocados + {buffer} min buffer)
**Itens na pauta**: {N}

---

## Abertura (2 min)

- Alinhamento do objetivo da reuniao
- Revisao rapida da pauta

## Pauta

### 1. {Titulo do item} ({N} min) — [PRIORIDADE]

**Motivo**: {por que entrou na pauta — ex: "acao pendente ha 3 reunioes"}
**Tipo**: {decisao tecnica / review / alinhamento / risco / retro}
**Origem**: [analise_{DD-MM}_{slug}](./{pasta}/analise.md)
**Quem precisa estar**: {resp + stakeholders}

**Contexto curto**:
> {trecho original da analise, com citacao [MM:SS] se existir}

**O que decidir/esclarecer**:
- {pergunta objetiva 1}
- {pergunta objetiva 2}

---

### 2. {item 2} ({N} min) — [PRIORIDADE]
...

## Fechamento (3 min)

- Resumo de decisoes
- Confirmacao de proximos passos
- Quem documenta a ata

---

## Itens que NAO entraram nesta pauta (falta de tempo)

Estes serao priorizados na proxima reuniao:

- {item X} — {motivo}
- {item Y} — {motivo}

## Referencias

Reunioes anteriores consultadas:

- [analise_{DD-MM}_{slug}](./{pasta}/) — {data} — {titulo}
- [analise_...](./...)

---

*Agenda gerada a partir de {N} reunioes. Itens podem ser reorganizados.*
```

## Fase 6: (Opcional) Gerar HTML

Se o usuario pediu ou se faz sentido compartilhar, gerar tambem versao HTML seguindo as convencoes:

- **Zero CDN, zero JS para dados, zero dependencia externa**
- Paleta do dashboard (indigo + semanticos)
- Layout de agenda com numeros grandes (1, 2, 3...), tempo por item, pill de prioridade
- Modo light forcado

## Fase 7: Salvar e reportar

```bash
DATA=$(date +"%Y-%m-%d")
SLUG="{tema-slug ou 'reuniao-periodica'}"
MD="$PROJECT_DIR/agenda_proposta_${DATA}_${SLUG}.md"
```

Informar:
- Itens na pauta (contagem)
- Tempo alocado vs duracao
- Itens que ficaram de fora
- Caminho do arquivo

## Regras nao-negociaveis

- **Tempo total nunca ultrapassa duracao** fornecida.
- **Sempre reservar buffer de 10%** para transicoes.
- **Nao inventar itens** — todos vem de reunioes existentes. Se nao ha pendencias, reportar isso.
- **Sempre citar reuniao de origem** com link relativo para a pasta.
- **Perguntas objetivas no item** — "O que decidir" deve ser pergunta acionavel, nao topico vago.
- **Maximo 8 itens na pauta** — se pauta tiver mais que isso, cortar pelo score e mover o resto para "nao entraram".
- **Abertura e fechamento fixos** (2 min + 3 min).
- **Se o usuario passou escopo**, aplicar filtro antes de ranquear.
- **Modo light forcado** (se gerar HTML).
- **Slug kebab-case** lowercase sem acentos.
- **Salvar na raiz do repo**.
