---
name: analisar-decisoes
description: Use quando precisar extrair apenas as decisoes arquiteturais/tecnicas de uma reuniao em formato ADR (Architecture Decision Record), com contexto, opcoes consideradas, decisao tomada e consequencias. Pode operar sobre um arquivo de audio/video novo OU sobre uma pasta analise_* ja existente. Ideal para manter log de decisoes de projeto.
---

# Extrair Decisoes (ADR)

Voce e um curador de Architecture Decision Records. Extrai **apenas as decisoes tecnicas/arquiteturais** de uma reuniao e gera ADRs em formato padronizado, com contexto, alternativas consideradas, decisao final e consequencias.

## Quando usar

- Reuniao de alinhamento tecnico onde varias decisoes foram tomadas
- Review de arquitetura / design doc discussion
- Planejamento de refatoracao
- Escolha de biblioteca/framework/abordagem
- Qualquer conversa onde voce precise do log permanente de "o que decidimos e por que"

**Diferenca vs `/analisar-reuniao`**: o comando completo captura tudo (decisoes + acoes + sentimento + riscos + etc). Este extrai **so decisoes**, em formato ADR estruturado, pronto para virar arquivo no repo de codigo.

## Fase 0: Identificar fonte

Dois modos:

### Modo A: Arquivo de audio/video novo

Se `$ARGUMENTS` e caminho de arquivo (mp4/wav/etc), executar Fases 1-2 abaixo (igual ao `/analisar-reuniao`).

### Modo B: Pasta analise_* existente

Se `$ARGUMENTS` e caminho de pasta `analise_*`, **pular Fases 1-2** e ir direto para Fase 3, lendo o `analise.md` existente e re-extraindo decisoes em formato ADR.

Se `$ARGUMENTS` vazio, perguntar ao usuario qual modo usar.

## Fase 1: Extracao de audio (modo A)

```bash
/opt/homebrew/bin/ffmpeg -i "<arquivo>" -vn -acodec pcm_s16le -ar 16000 -ac 1 /tmp/decisoes_audio.wav -y
```

## Fase 2: Transcricao (modo A)

Modelo `medium` para garantir captura correta de termos tecnicos:

```bash
/Library/Frameworks/Python.framework/Versions/Current/bin/python3 << 'PYEOF'
import whisper
from whisper.utils import get_writer
import json, os

model = whisper.load_model('medium')
result = model.transcribe('/tmp/decisoes_audio.wav', language='pt', verbose=False)

os.makedirs('/tmp/decisoes_out', exist_ok=True)
writer = get_writer('vtt', '/tmp/decisoes_out')
writer(result, 'transcricao.wav', {'max_line_width': None, 'max_line_count': None, 'highlight_words': False})

with open('/tmp/decisoes_transcript.txt', 'w', encoding='utf-8') as f:
    f.write(result['text'])

segs = [{'start': s['start'], 'end': s['end'], 'text': s['text'].strip()} for s in result['segments']]
with open('/tmp/decisoes_segments.json', 'w', encoding='utf-8') as f:
    json.dump(segs, f, ensure_ascii=False, indent=2)
PYEOF
```

## Fase 3: Extrair decisoes (ambos os modos)

Ler transcricao (ou `analise.md` no modo B) e identificar **cada decisao tecnica/arquitetural** tomada. Para cada uma, extrair os 5 campos ADR:

### 3.1 Heuristica para identificar decisoes

Buscar marcadores linguisticos como:
- "vamos fazer X" / "vamos usar Y"
- "decidimos que"
- "ficou definido que"
- "a opcao escolhida foi"
- "melhor abordagem e"
- "nao vamos mais fazer"
- "mudamos para"
- "vamos reverter"

E tambem: trechos onde o grupo discute alternativas e chega em um consenso — mesmo sem marcador explicito, se a transcricao mostra "A sugeriu X, B preferiu Y, concluimos com Y", isso e uma decisao.

### 3.2 Estrutura ADR por decisao

Cada decisao vira um ADR com:

1. **Titulo** — curto, imperativo, especifico. Ex: "Vincular idioma a disciplina, nao ao professor"
2. **Status** — `Aceita` (padrao), `Proposta` (se ainda em debate), `Revertida` (se reverte decisao anterior)
3. **Contexto** — o problema ou situacao que motivou a decisao. 2-3 paragrafos explicando o que estava em jogo.
4. **Opcoes consideradas** — se a transcricao mostra alternativas, listar. Se nao, omitir.
5. **Decisao** — o que foi escolhido, em linguagem clara e direta.
6. **Consequencias** — efeitos esperados (bons e ruins). Pode ser tanto o que fica melhor quanto tradeoffs aceitos.
7. **Citacao de origem** — trecho literal com timestamp se existir.

## Fase 4: Criar pasta ou anexar

### Modo A (novo)

```bash
DATA=$(date +"%d-%m-%Y")
HORA=$(date +"%H-%M-%S")
SLUG="<slug-tema-principal>"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
PASTA="${PROJECT_DIR}/adr_${DATA}_${HORA}_${SLUG}"
mkdir -p "$PASTA"
cp /tmp/decisoes_out/transcricao.vtt "$PASTA/transcricao.vtt"
```

Prefixo **`adr_`** (nao `analise_`).

### Modo B (pasta existente)

Criar subdiretorio `decisoes/` dentro da pasta `analise_*` existente:

```bash
mkdir -p "$PASTA_ORIGINAL/decisoes"
```

## Fase 5: Gerar arquivos ADR

Um arquivo `.md` por decisao, numerado:

```
decisoes/
  0001-titulo-da-decisao.md
  0002-outra-decisao.md
  0003-mais-uma.md
```

Numeracao continua se ja existirem ADRs anteriores no repo (verificar com `ls` antes).

### Template ADR

```markdown
# ADR-{NNNN}: {Titulo}

**Data**: {YYYY-MM-DD}
**Status**: {Aceita|Proposta|Revertida|Substituida por ADR-XXXX}
**Origem**: [analise_{DD-MM}_{slug}](../)
**Tomada em**: [MM:SS] — "{citacao curta}"

## Contexto

{2-3 paragrafos explicando o problema, a situacao tecnica, quais pressoes ou constraints motivaram a discussao}

## Opcoes Consideradas

1. **{Opcao A}** — {prós e contras se mencionados}
2. **{Opcao B}** — {prós e contras}
3. **{Opcao C}** — {prós e contras}

(Omitir esta secao se a transcricao nao mostra alternativas — a decisao pode ter sido tomada sem debate de opcoes)

## Decisao

{Declaracao clara e direta do que foi escolhido. 1-2 paragrafos.}

## Consequencias

### Positivas
- {consequencia 1}
- {consequencia 2}

### Negativas / Tradeoffs aceitos
- {tradeoff 1}
- {tradeoff 2}

### Neutras / A observar
- {ponto a acompanhar}

## Referencias

- Citacao original: [transcricao.vtt](../transcricao.vtt) em {MM:SS}
- Decisoes relacionadas: [ADR-{NNN}](./{arquivo}.md) (se aplicavel)

---

*ADR extraido via /analisar-decisoes a partir de reuniao {data}.*
```

## Fase 6: Indice de decisoes

Criar/atualizar `decisoes/README.md` com um indice:

```markdown
# Decisoes Arquiteturais — {Contexto da reuniao}

## Indice

| # | Titulo | Data | Status |
|---|--------|------|--------|
| [0001](./0001-titulo-da-decisao.md) | Titulo curto | YYYY-MM-DD | Aceita |
| [0002](./0002-outra-decisao.md) | Titulo curto | YYYY-MM-DD | Aceita |
| [0003](./0003-mais-uma.md) | Titulo curto | YYYY-MM-DD | Revertida por 0007 |

## Por Status

- **Aceitas**: {count}
- **Propostas** (em debate): {count}
- **Revertidas**: {count}
- **Substituidas**: {count}

## Por tema

- **Dominio pedagogico**: ADR-0001, ADR-0003
- **Arquitetura de dados**: ADR-0002
- **UI/UX**: ADR-0005
```

## Fase 7: Reportar

Informar:
- Numero de decisoes extraidas
- Caminho do diretorio `decisoes/`
- Lista curta de titulos dos ADRs gerados
- Sugestao: "Considere copiar esses ADRs para o repositorio de codigo (em `docs/adr/` ou similar) para integra-los ao historico do projeto."

## Regras nao-negociaveis

- **Apenas decisoes tecnicas/arquiteturais** — nao extrair decisoes operacionais ("quem vai redigir a ata") ou pessoais ("ferias do Joao").
- **Nunca inventar contexto ou opcoes** — se a transcricao nao mostra alternativas, omitir a secao "Opcoes consideradas".
- **Nunca inventar consequencias** — se a transcricao nao discute tradeoffs, escrever apenas as consequencias logicas diretas e marcar "(inferido)".
- **Sempre citar timestamp da decisao** — origem rastreavel e essencial em ADR.
- **Numeracao sequencial de 4 digitos** — `0001`, `0002`, ... (permite 9999 decisoes sem reformat).
- **Um arquivo por decisao** — nao agrupar multiplas decisoes em um ADR.
- **Slug kebab-case** no nome do arquivo.
- **Formato padrao ADR** — respeitar as 6 secoes (Contexto, Opcoes, Decisao, Consequencias, Referencias).
- **Indice README.md sempre atualizado** apos cada rodada de extracao.
- **Portugues brasileiro, sem emojis**.
- **Salvar na raiz do repo** (`adr_*/`) ou dentro de pasta existente (`analise_*/decisoes/`).
