---
name: analisar-rapido
description: Use quando precisar de uma analise rapida de reuniao a partir de audio/video sem o dashboard visual. Gera apenas transcricao VTT e um analise_rapido.md enxuto (resumo, decisoes, acoes). Usa Whisper small (nao medium) e pula toda a fase de dashboard. Ideal para reunioes de rotina onde o dashboard e overkill.
---

# Analisar Reuniao — Modo Rapido

Voce e um analisador express de reunioes. Versao enxuta do comando `/analisar-reuniao`: apenas transcricao + markdown curto, **sem dashboard**.

## Diferencas vs `/analisar-reuniao`

| Aspecto | Completo | Rapido |
|---------|----------|--------|
| Modelo Whisper | `medium` | `small` |
| Dashboard HTML | Sim | **Nao** |
| analise.md | Completo (15+ secoes) | Enxuto (5 secoes) |
| Pasta gerada | `analise_...` | `analise_rapida_...` |
| Tempo | ~3-8 min | ~1-3 min |

Use quando: reuniao de rotina, standup, 1:1 curto, alinhamento rapido, ou quando voce so quer o resumo e nao vai revisitar depois.

## Dependencias (paths absolutos)

Iguais a `/analisar-reuniao`:
- `/opt/homebrew/bin/ffmpeg` — extracao de audio
- `/Library/Frameworks/Python.framework/Versions/Current/bin/python3` — com `whisper` instalado

## Fase 0: Validacao do input

Se `$ARGUMENTS` vazio, perguntar o caminho. Validar formato (mesmos aceitos pelo comando completo: mp4, mov, webm, avi, mkv, wav, mp3, m4a, ogg, flac).

Informar: nome, tamanho (MB), tipo.

## Fase 1: Extracao de audio

Para video:
```bash
/opt/homebrew/bin/ffmpeg -i "<arquivo>" -vn -acodec pcm_s16le -ar 16000 -ac 1 /tmp/reuniao_rapida_audio.wav -y
```

Para audio: `cp "<arquivo>" /tmp/reuniao_rapida_audio.wav`

## Fase 2: Transcricao Whisper (modelo small)

**Diferenca chave**: usar modelo `small` em vez de `medium`. E mais rapido mas um pouco menos preciso. Aceitavel para reunioes curtas e informais.

```bash
/Library/Frameworks/Python.framework/Versions/Current/bin/python3 << 'PYEOF'
import whisper
from whisper.utils import get_writer
import json, os

print("Carregando modelo small...")
model = whisper.load_model('small')

print("Transcrevendo...")
result = model.transcribe('/tmp/reuniao_rapida_audio.wav', language='pt', verbose=False)

os.makedirs('/tmp/reuniao_rapida_out', exist_ok=True)

# VTT
writer = get_writer('vtt', '/tmp/reuniao_rapida_out')
writer(result, 'transcricao.wav', {'max_line_width': None, 'max_line_count': None, 'highlight_words': False})

# Texto puro
with open('/tmp/reuniao_rapida_transcript.txt', 'w', encoding='utf-8') as f:
    f.write(result['text'])

# Segmentos
segs = [{'start': s['start'], 'end': s['end'], 'text': s['text'].strip()} for s in result['segments']]
with open('/tmp/reuniao_rapida_segments.json', 'w', encoding='utf-8') as f:
    json.dump(segs, f, ensure_ascii=False, indent=2)

total_dur = result['segments'][-1]['end'] if result['segments'] else 0
print(f"Segmentos: {len(result['segments'])}")
print(f"Duracao: {int(total_dur//60)}:{int(total_dur%60):02d}")
PYEOF
```

## Fase 3: Analise enxuta

Ler `/tmp/reuniao_rapida_transcript.txt` e extrair **apenas**:

1. **Slug curto** (3-5 palavras kebab-case) para o nome da pasta
2. **Titulo curto** — frase descritiva (5-8 palavras)
3. **Resumo 1-paragrafo** (2-3 frases) — o que foi discutido
4. **Top 3 decisoes** (se houver) — com contexto minimo
5. **Top 5 acoes** — tabela compacta com responsavel e prazo (se inferivel)
6. **Pontos em aberto** — duvidas nao respondidas (max 3)

**Nao extrair**: sentimento detalhado, word cloud, matriz de risco, entidades, timeline, insights, fluxo. Se precisar disso, rodar o `/analisar-reuniao` completo.

## Fase 4: Criar pasta enxuta

```bash
DATA=$(date +"%d-%m-%Y")
HORA=$(date +"%H-%M-%S")
SLUG="<slug-gerado>"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
PASTA="${PROJECT_DIR}/analise_rapida_${DATA}_${HORA}_${SLUG}"
mkdir -p "$PASTA"
cp /tmp/reuniao_rapida_out/transcricao.vtt "$PASTA/transcricao.vtt"
```

**Prefixo `analise_rapida_`** (nao `analise_`) para diferenciar visualmente no `ls` do repo.

## Fase 5: Gerar `analise_rapido.md`

Template enxuto:

```markdown
# {Titulo}

**Data**: {DD/MM/YYYY}
**Duracao**: {MM:SS}
**Modo**: Analise rapida (Whisper small)

## Resumo

{2-3 frases}

## Decisoes

1. **{decisao 1}**
2. **{decisao 2}**

## Acoes

| Acao | Responsavel | Prazo |
|------|-------------|-------|
| {acao} | {resp ou "—"} | {prazo ou "—"} |

## Pontos em Aberto

- {duvida 1}
- {duvida 2}

---

*Analise rapida. Para dashboard completo com graficos, reprocessar com `/analisar-reuniao`.*
```

## Fase 6: Reportar

Informar:
- Caminho da pasta
- Duracao da reuniao
- Numero de acoes identificadas
- Sugestao: "Para dashboard visual completo, rode `/analisar-reuniao {mesmo arquivo}`."

## Regras nao-negociaveis

- **Sempre modelo `small`** — nunca `medium` no modo rapido (seria contraditorio).
- **Nunca gerar dashboard.html** — se o usuario quer dashboard, nao e esse comando.
- **Sempre prefixo `analise_rapida_`** na pasta.
- **Maximo 3 decisoes e 5 acoes** — se tiver mais, indica que a reuniao precisa do modo completo.
- **Pasta dentro da raiz do repo** (`$CLAUDE_PROJECT_DIR`), nao no diretorio do input.
- **Nunca inventar dados** que nao estao na transcricao.
- **Portugues brasileiro**.
- **Sem emojis**.
- **Slug kebab-case** lowercase sem acentos.
- **Sem "Nao identificado"** repetido — se uma secao nao tem conteudo, omitir (diferente do modo completo que marca "Nao identificado").
