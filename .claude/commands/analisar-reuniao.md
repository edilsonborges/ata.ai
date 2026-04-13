---
description: Analisa reuniao a partir de audio/video, gerando pasta com transcricao VTT, analise em markdown e dashboard HTML auto-contido
argument-hint: [caminho-do-arquivo] ou vazio para perguntar
---

Voce e um analisador profissional de reunioes. A partir de um arquivo de audio ou video em `$ARGUMENTS`, produza uma analise estruturada e completa.

IMPORTANTE: este comando e focado em analise GERAL de reunioes (resumo, decisoes, acoes, timeline, insights, riscos). NAO e um roteiro fixo de perguntas 1:1 — o conteudo emerge da propria transcricao.

## Objetivo

Gerar uma pasta `analise_{DD-MM-YYYY}_{HH-MM-SS}_{slug-resumo}/` dentro do proprio repositorio `ata.ai` (raiz do projeto — use `$CLAUDE_PROJECT_DIR`), NAO no diretorio do arquivo de entrada. A pasta contem tres artefatos:

1. `transcricao.vtt` — transcricao com timestamps em formato WebVTT
2. `analise.md` — analise estruturada em markdown
3. `dashboard.html` — dashboard visual self-contained (abre direto no navegador)

---

## Fase 0: Validacao do input

Se `$ARGUMENTS` estiver vazio, pergunte ao usuario o caminho completo do arquivo.

Validar que o arquivo existe e eh um formato suportado:
- **Video**: `.mp4`, `.mov`, `.webm`, `.avi`, `.mkv`
- **Audio**: `.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac`

Informar ao usuario:
- Nome do arquivo
- Tamanho (MB)
- Tipo detectado (audio ou video)

Se o formato nao for suportado, abortar com mensagem de erro clara.

---

## Fase 1: Extracao de audio (se video)

Para arquivos de video, extrair audio:
```bash
/opt/homebrew/bin/ffmpeg -i "<arquivo>" -vn -acodec pcm_s16le -ar 16000 -ac 1 /tmp/reuniao_audio.wav -y
```

Para arquivos de audio, copiar direto:
```bash
cp "<arquivo>" /tmp/reuniao_audio.wav
```

Informar a duracao detectada em MM:SS ao usuario.

---

## Fase 2: Transcricao Whisper em formato VTT

Executar Whisper com modelo `medium` em portugues e gerar VTT com timestamps usando o writer nativo:

```bash
/Library/Frameworks/Python.framework/Versions/Current/bin/python3 << 'PYEOF'
import whisper
from whisper.utils import get_writer
import json, os

print("Carregando modelo medium...")
model = whisper.load_model('medium')

print("Transcrevendo...")
result = model.transcribe('/tmp/reuniao_audio.wav', language='pt', verbose=False)

os.makedirs('/tmp/reuniao_out', exist_ok=True)

# VTT via writer nativo
writer = get_writer('vtt', '/tmp/reuniao_out')
writer(result, 'transcricao.wav', {'max_line_width': None, 'max_line_count': None, 'highlight_words': False})

# Texto puro
with open('/tmp/reuniao_transcript.txt', 'w', encoding='utf-8') as f:
    f.write(result['text'])

# Segmentos estruturados
segs = [{'start': s['start'], 'end': s['end'], 'text': s['text'].strip()} for s in result['segments']]
with open('/tmp/reuniao_segments.json', 'w', encoding='utf-8') as f:
    json.dump(segs, f, ensure_ascii=False, indent=2)

total_dur = result['segments'][-1]['end'] if result['segments'] else 0
print(f"Segmentos: {len(result['segments'])}")
print(f"Duracao: {int(total_dur//60)}:{int(total_dur%60):02d}")
print(f"Caracteres: {len(result['text'])}")
print(f"VTT: /tmp/reuniao_out/transcricao.vtt")
PYEOF
```

O writer do Whisper cria o arquivo como `<nome>.vtt`. Localize-o em `/tmp/reuniao_out/` apos executar (o nome pode ser `transcricao.vtt` ou variacao — usar `ls` para confirmar).

Informar ao usuario: segmentos, duracao total, caracteres transcritos.

---

## Fase 3: Analise do conteudo

Ler `/tmp/reuniao_transcript.txt` (texto puro) e `/tmp/reuniao_segments.json` (segmentos com timestamps).

Analisar em profundidade, extraindo:

1. **Slug curto (3-5 palavras, kebab-case, lowercase, sem acentos)** — para o nome da pasta. Exemplos: `revisao-arquitetura-api`, `retro-sprint-42`, `planejamento-q2-2026`.

2. **Titulo da reuniao** — frase descritiva curta.

3. **Metadados**:
   - Data da reuniao (se mencionada; caso contrario, data atual)
   - Duracao total
   - Participantes identificados (inferidos por contexto — Whisper nao separa locutores)

4. **Resumo executivo** — 3-5 frases.

5. **Topicos discutidos** — titulo, resumo, relevancia estimada (%).

6. **Decisoes tomadas** — com contexto.

7. **Findings/descobertas** — coisas importantes aprendidas.

8. **Acoes e proximos passos** — com responsavel, prazo, prioridade, status (se inferivel).

9. **Riscos identificados** — com probabilidade e impacto (escala 1-10).

10. **Timeline de eventos** — momentos-chave com faixa `MM:SS – MM:SS` e tom (positivo/neutro/preocupacao/construtivo).

11. **Entidades mencionadas** — agrupadas: pessoas, sistemas, orgaos, tecnologias, ferramentas.

12. **Sentimento e dinamica** — tom geral, engajamento, distribuicao de fala estimada (%).

13. **Palavras-chave** — 15-25 palavras para word cloud, com peso/frequencia (filtrar stopwords portuguesas).

14. **Insights** — observacoes nao obvias.

15. **Fluxo/processo** (se aplicavel) — etapas ordenadas mencionadas.

SEMPRE citar trechos literais entre aspas com timestamp quando relevante.
NUNCA inventar dados que nao estao na transcricao. Se algo nao foi abordado, omitir a secao ou marcar "Nao identificado".

---

## Fase 4: Criar pasta de analise

Gerar nome da pasta e criar dentro do proprio repositorio `ata.ai` (raiz do projeto). Usar `$CLAUDE_PROJECT_DIR` quando disponivel, com fallback para `$PWD`:

```bash
DATA=$(date +"%d-%m-%Y")
HORA=$(date +"%H-%M-%S")
SLUG="<slug-gerado-na-fase-3>"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
PASTA="${PROJECT_DIR}/analise_${DATA}_${HORA}_${SLUG}"
mkdir -p "$PASTA"
cp /tmp/reuniao_out/transcricao.vtt "$PASTA/transcricao.vtt"
```

Se o writer do Whisper gerou outro nome de arquivo, ajustar o `cp` de acordo (listar `/tmp/reuniao_out/` para confirmar).

Informar o caminho completo da pasta criada.

---

## Fase 5: Gerar `analise.md`

Criar dentro da pasta com esta estrutura:

```markdown
# {Titulo da Reuniao}

**Data**: {DD/MM/YYYY}
**Duracao**: {MM:SS}
**Participantes**: {lista curta}

---

## Resumo Executivo

{3-5 frases}

## Participantes

| Nome | Papel | Tipo |
|------|-------|------|
| {nome} | {papel inferido} | {condutor/executor/apoio} |

> Nota: Whisper nao separa locutores. Atribuicao inferida por contexto.

## Topicos Discutidos

### {Topico 1} ({relevancia}%)
{Resumo}

> "{citacao literal}" — [MM:SS]

## Decisoes Tomadas

1. **{Decisao}** — {contexto e responsaveis}

## Findings

1. **{Finding}** — {detalhe}

## Acoes e Proximos Passos

| Acao | Responsavel | Prazo | Prioridade | Status |
|------|-------------|-------|------------|--------|
| {acao} | {resp} | {prazo} | {alta/media/baixa} | {status} |

## Riscos Identificados

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| {risco} | {1-10} | {1-10} | {mitigacao} |

## Timeline

- **[{MM:SS} – {MM:SS}]** {evento} — {positivo/neutro/preocupacao/construtivo}

## Entidades Mencionadas

- **Pessoas**: {lista}
- **Sistemas**: {lista}
- **Orgaos**: {lista}
- **Tecnologias**: {lista}
- **Ferramentas**: {lista}

## Sentimento e Dinamica

{tom geral, engajamento, distribuicao de fala}

## Insights

{observacoes nao obvias, padroes, oportunidades}

---

*Analise gerada a partir de transcricao Whisper (modelo medium, pt-BR).*
```

---

## Fase 6: Gerar `dashboard.html`

Criar um dashboard visual **100% self-contained e sem JavaScript** (CSS inline, **nenhum grafico dependente de JS**). Motivo: iOS Quick Look, Preview no Files e AirDrop preview DESATIVAM JavaScript em HTMLs locais. Mesmo com Chart.js inline, o JS nao executa nesses contextos e o usuario ve cards vazios. Portanto todas as visualizacoes devem ser HTML + CSS puros — sem `<canvas>`, sem Chart.js, sem dependencia de `<script>` para mostrar dados. JavaScript pode existir apenas como **progressive enhancement** (ex: busca na transcricao) — se nao executar, o dashboard continua legivel. O design segue o padrao descrito abaixo rigorosamente.

### 6.0 Escolha do template base (obrigatorio)

Antes de gerar o `dashboard.html`, escolher um template base em `.claude/templates/`. O agente NAO deve gerar o dashboard do zero — deve usar um dos modelos existentes como ponto de partida visual e adaptar o conteudo. Catalogo completo e regras em `.claude/templates/README.md`.

**Regra de decisao** (avaliar no conteudo analisado na Fase 4):

| Sinais dominantes | Template |
| --- | --- |
| Decisoes executivas, acoes priorizadas, poucos participantes seniores, foco em entrega/resultado | `executivo-clean.html` |
| Arquitetura, codigo, sistemas, findings tecnicos, fluxos de processo, incidentes, RFCs | `tecnico-denso.html` |
| Retrospectiva explicita, sentimento/humor em primeiro plano, mesmo time, start/stop/continue, 1-on-1 em grupo | `retrospectiva-warm.html` |
| Tom reflexivo, estrategia de longo prazo, citacoes longas relevantes, pouca acao numerica, board/conselho | `minimalista-editorial.html` |

Em caso de empate, usar `executivo-clean.html` como default.

**Como adaptar o template escolhido**:

1. Abrir o HTML do template e usa-lo como base visual: preservar paleta, tipografia, estilo de card, densidade, estrutura de secoes.
2. Substituir **100% dos dados de amostra** pelos dados reais extraidos na Fase 4. Nenhum texto do sample (nomes fake, "Sprint 12", "Refatoracao API", etc) pode sobrar no output.
3. **Omitir secoes sem dado real** (ex: se nao houve riscos, nao deixar "Matriz de Risco" com cards vazios).
4. Ajustar textos longos (resumo, pull quotes) ao tom do template escolhido — o `minimalista-editorial` espera paragrafos reflexivos; o `tecnico-denso` espera bullets curtos e diretos.
5. Manter todas as restricoes tecnicas listadas em 6.1 (zero JS para dados, light mode forcado, CSS-only charts, sem CDN, sem emojis).
6. Se o template tem JS opcional de busca na transcricao, pode manter (progressive enhancement) — a pagina deve continuar legivel sem ele.

### 6.1 Requisitos tecnicos

- `<html lang="pt-BR">`, charset UTF-8, viewport responsivo
- **Zero dependencia de JavaScript para mostrar dados** (OBRIGATORIO). iOS Quick Look, iOS Files Preview e AirDrop preview DESATIVAM JavaScript em HTMLs locais. Nao usar Chart.js (nem via CDN, nem inline). Todas as visualizacoes devem ser **HTML + CSS puros**: barras com `width: N%`, donuts com `conic-gradient`, bubbles com `position: absolute` e `background: radial-gradient`, sparklines com `<svg>` inline estatico. JavaScript so pode existir como **progressive enhancement** (ex: busca na transcricao) — a pagina inteira deve ser legivel com JS desativado.
- Fontes: system stack (sem Google Fonts)
- **Modo light forcado** (OBRIGATORIO para legibilidade em mobile): incluir `<meta name="color-scheme" content="light">` no `<head>` E `color-scheme: light` no `:root` do CSS. Sem isso, iOS Safari e Chrome Android com dark mode do sistema invertem cores automaticamente e o texto vira branco sobre fundo claro (ilegivel).
- Grid responsivo com breakpoint mobile em 600px
- Print-friendly via `@media print`
- Tudo inline no arquivo — deve abrir no navegador, no iOS Files, via AirDrop ou Quick Look **sem nenhuma dependencia externa e sem depender de JS**

### 6.2 Estrutura HTML (ordem das secoes)

```
<html>
  <head> (meta charset + viewport + <meta name="color-scheme" content="light">, title, <style>)
  <body>
    <header class="header"> (gradient indigo/purple, badge + h1 + subtitle)
    <div class="container">
      <div class="grid-4"> Meta Cards (Data, Participantes, Duracao, Risco) </div>

      <h2 class="section-title">Sentimento e Engajamento</h2>
      <div class="grid-3"> card donut + card radar + card gauge confianca </div>
      <div class="grid-2"> card line chart temporal + card bar chart </div>

      <h2 class="section-title">Participantes</h2>
      <div class="grid-2"> card tabela perfis + card bar horizontal distribuicao fala </div>

      <h2 class="section-title">Topicos Discutidos</h2>
      <div class="grid-2"> card topic bar horizontal + card word cloud </div>

      <h2 class="section-title">Entidades Mencionadas</h2>
      <div class="grid-2 or grid-3"> cards com tags por categoria </div>

      <h2 class="section-title">Fluxo / Processo</h2> (opcional, se aplicavel)
      <div class="card"> <div class="flow"> ... </div> </div>

      <h2 class="section-title">Timeline da Reuniao</h2>
      <div class="card"> <div class="timeline"> ... </div> </div>

      <h2 class="section-title">Insights e Decisoes</h2>
      <div class="grid-2"> insight-cards coloridos por tipo </div>

      <h2 class="section-title">Matriz de Risco</h2>
      <div class="card"> <canvas id="riskBubble"></canvas> </div>

      <h2 class="section-title">Acoes e Proximos Passos</h2>
      <div class="card"> <table> ... </table> </div>

      <h2 class="section-title">Transcricao Completa</h2>
      <div class="card"> <input search> + <transcript-box> </div>

      <div class="footer"> ... </div>
    </div>
    <script src="chart.js cdn"></script>
    <script> ... charts + search ... </script>
  </body>
</html>
```

Omitir secoes vazias (ex: se nao houve riscos, omitir "Matriz de Risco" e sua secao).

### 6.3 Bloco CSS completo (copiar integralmente)

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  color-scheme: light;
  --bg: #f5f6fa;
  --card: #ffffff;
  --text: #1a1a2e;
  --text-muted: #6b7280;
  --accent: #4f46e5;
  --accent-light: #eef2ff;
  --green: #10b981;
  --red: #ef4444;
  --amber: #f59e0b;
  --blue: #3b82f6;
  --purple: #8b5cf6;
  --border: #e5e7eb;
  --radius: 12px;
}
html {
  background: var(--bg);
  color: var(--text);
  -webkit-text-size-adjust: 100%;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}
.header {
  background: linear-gradient(135deg, #312e81, #4f46e5, #7c3aed);
  color: #fff;
  padding: 2.5rem 2rem 2rem;
}
.header .badge {
  display: inline-block;
  background: rgba(255,255,255,.15);
  padding: .3rem .8rem;
  border-radius: 999px;
  font-size: .8rem;
  margin-bottom: .75rem;
  backdrop-filter: blur(10px);
}
.header h1 { font-size: 1.75rem; font-weight: 700; margin-bottom: .5rem; }
.header .subtitle { opacity: .85; font-size: .95rem; }
.container { max-width: 1400px; margin: 0 auto; padding: 1.5rem; }
.grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.25rem; }
.grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }
.grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
.card {
  background: var(--card);
  border-radius: var(--radius);
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  transition: box-shadow .2s;
  overflow-x: auto;
}
.card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.1); }
.card h3 {
  font-size: 1rem;
  color: var(--text-muted);
  margin-bottom: 1rem;
  text-transform: uppercase;
  letter-spacing: .04em;
  font-weight: 600;
}
.section-title {
  font-size: 1.35rem;
  font-weight: 700;
  margin: 2rem 0 1rem;
  padding-bottom: .5rem;
  border-bottom: 2px solid var(--accent);
}
.meta-card {
  background: var(--card);
  border-radius: var(--radius);
  padding: 1.25rem;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.meta-card .value { font-size: 1.6rem; font-weight: 700; color: var(--accent); }
.meta-card .label { font-size: .82rem; color: var(--text-muted); margin-top: .25rem; }
.pill {
  display: inline-block;
  padding: .15rem .6rem;
  border-radius: 999px;
  font-size: .75rem;
  font-weight: 600;
}
.pill-green  { background: #d1fae5; color: #065f46; }
.pill-blue   { background: #dbeafe; color: #1e40af; }
.pill-amber  { background: #fef3c7; color: #92400e; }
.pill-red    { background: #fee2e2; color: #991b1b; }
.pill-purple { background: #ede9fe; color: #5b21b6; }
.pill-gray   { background: #f3f4f6; color: #374151; }
.tag {
  display: inline-block;
  padding: .2rem .65rem;
  border-radius: 6px;
  font-size: .78rem;
  margin: .15rem;
  font-weight: 500;
}
.tag-sistema    { background: #dbeafe; color: #1e40af; }
.tag-orgao      { background: #fce7f3; color: #9d174d; }
.tag-tech       { background: #d1fae5; color: #065f46; }
.tag-ferramenta { background: #fef3c7; color: #92400e; }
.tag-pessoa     { background: #ede9fe; color: #5b21b6; }
.timeline { position: relative; padding-left: 2rem; }
.timeline::before {
  content: ''; position: absolute;
  left: .6rem; top: 0; bottom: 0;
  width: 2px; background: var(--border);
}
.timeline-item { position: relative; margin-bottom: 1.5rem; }
.timeline-item::before {
  content: ''; position: absolute;
  left: -1.65rem; top: .4rem;
  width: 12px; height: 12px;
  border-radius: 50%;
  border: 2px solid var(--accent);
  background: var(--card);
}
.timeline-item.positive::before     { border-color: var(--green);  background: #d1fae5; }
.timeline-item.neutral::before      { border-color: var(--blue);   background: #dbeafe; }
.timeline-item.concern::before      { border-color: var(--amber);  background: #fef3c7; }
.timeline-item.constructive::before { border-color: var(--purple); background: #ede9fe; }
.timeline-item .time { font-size: .78rem; color: var(--text-muted); }
.timeline-item .desc { font-weight: 500; }
.insight-card {
  background: var(--card);
  border-radius: var(--radius);
  padding: 1rem 1.25rem;
  border-left: 4px solid;
  margin-bottom: .75rem;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.insight-card.problema { border-color: var(--red); }
.insight-card.finding  { border-color: var(--amber); }
.insight-card.decisao  { border-color: var(--green); }
.insight-card.acao     { border-color: var(--blue); }
.insight-type {
  font-size: .72rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  font-weight: 700;
  margin-bottom: .25rem;
}
.insight-card.problema .insight-type { color: var(--red); }
.insight-card.finding  .insight-type { color: var(--amber); }
.insight-card.decisao  .insight-type { color: var(--green); }
.insight-card.acao     .insight-type { color: var(--blue); }
.word-cloud {
  display: flex; flex-wrap: wrap; gap: .4rem;
  align-items: center; justify-content: center; padding: 1rem;
}
.word-cloud span {
  display: inline-block;
  padding: .2rem .5rem;
  border-radius: 6px;
  transition: transform .2s;
  cursor: default;
}
.word-cloud span:hover { transform: scale(1.15); }
.gauge-container { text-align: center; }
.gauge-value { font-size: 2.5rem; font-weight: 800; color: var(--accent); }
.gauge-bar {
  height: 10px; border-radius: 5px;
  background: var(--border); margin-top: .5rem; overflow: hidden;
}
.gauge-fill { height: 100%; border-radius: 5px; transition: width .6s; }
table { width: 100%; border-collapse: collapse; font-size: .9rem; }
th {
  background: var(--accent-light); color: var(--accent);
  font-weight: 600; text-align: left; padding: .6rem .8rem;
}
td { padding: .6rem .8rem; border-bottom: 1px solid var(--border); }
tr:hover td { background: #fafbff; }
.flow { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; padding: 1rem 0; }
.flow-step {
  background: var(--accent-light); color: var(--accent);
  padding: .5rem 1rem; border-radius: 8px;
  font-weight: 600; font-size: .85rem; white-space: nowrap;
}
.flow-arrow { color: var(--text-muted); font-size: 1.2rem; }
.transcript-box {
  max-height: 500px; overflow-y: auto; padding: 1rem;
  background: #fafbff; border-radius: 8px;
  font-size: .87rem; line-height: 1.8; white-space: pre-wrap;
}
.transcript-box::-webkit-scrollbar { width: 6px; }
.transcript-box::-webkit-scrollbar-track { background: transparent; }
.transcript-box::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
.transcript-box::-webkit-scrollbar-thumb:hover { background: #9ca3af; }
.highlight { background: #fef08a; border-radius: 2px; padding: 0 1px; }
.search-input {
  width: 100%; padding: .6rem 1rem;
  border: 1px solid var(--border); border-radius: 8px;
  font-size: .9rem; margin-bottom: .75rem;
  outline: none; transition: border-color .2s;
  background: var(--card); color: var(--text);
  -webkit-appearance: none; appearance: none;
}
.search-input:focus { border-color: var(--accent); }
.search-input::placeholder { color: var(--text-muted); }
.chart-container { position: relative; width: 100%; }
.chart-sm { max-height: 250px; }
.chart-md { max-height: 320px; }
.footer {
  text-align: center; padding: 2rem; margin-top: 2rem;
  border-top: 1px solid var(--border);
  color: var(--text-muted); font-size: .8rem;
}
@media (max-width: 600px) {
  .header h1 { font-size: 1.3rem; }
  .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
}
@media print {
  .header { background: #4f46e5 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .card, .meta-card, .insight-card { break-inside: avoid; }
  .transcript-box { max-height: none; overflow: visible; }
}
```

### 6.4 Paleta de cores (referencia)

**Primario**: `#4f46e5` (indigo). Light: `#eef2ff`. Dark: `#312e81`. Secundario: `#7c3aed` (roxo).

**Semanticos**:
- Verde (decisao/positivo): `#10b981` / light `#d1fae5` / dark `#065f46`
- Vermelho (problema/risco): `#ef4444` / light `#fee2e2` / dark `#991b1b`
- Ambar (finding/atencao): `#f59e0b` / light `#fef3c7` / dark `#92400e`
- Azul (info/tecnico): `#3b82f6` / light `#dbeafe` / dark `#1e40af`
- Roxo (construtivo): `#8b5cf6` / light `#ede9fe` / dark `#5b21b6`

**Neutros**: bg `#f5f6fa`, card `#ffffff`, text `#1a1a2e`, muted `#6b7280`, border `#e5e7eb`.

**Gradient header**: `linear-gradient(135deg, #312e81, #4f46e5, #7c3aed)`.

### 6.5 Templates HTML por componente

#### Header
```html
<header class="header">
  <span class="badge">Analise de Reuniao</span>
  <h1>{titulo}</h1>
  <p class="subtitle">{subtitulo/contexto}</p>
</header>
```

#### Meta Cards (grid 4)
```html
<div class="grid-4">
  <div class="meta-card"><div class="value">{DD/MM/YYYY}</div><div class="label">Data da Reuniao</div></div>
  <div class="meta-card"><div class="value">{N}</div><div class="label">Participantes</div></div>
  <div class="meta-card"><div class="value">{MM:SS}</div><div class="label">Duracao</div></div>
  <div class="meta-card"><div class="value">{Baixo|Medio|Alto}</div><div class="label">Risco Geral</div></div>
</div>
```

#### Card generico
```html
<div class="card">
  <h3>{TITULO EM CAPS}</h3>
  <div class="chart-container chart-sm"><canvas id="xxx"></canvas></div>
</div>
```

#### Insight Card
```html
<div class="insight-card decisao">
  <div class="insight-type">Decisao</div>
  <strong>{titulo curto}</strong>
  <p>{descricao e contexto}</p>
</div>
```
Classes: `decisao` (verde), `finding` (ambar), `problema` (vermelho), `acao` (azul).

#### Timeline
```html
<div class="timeline">
  <div class="timeline-item neutral">
    <div class="time">{MM:SS} &ndash; {MM:SS}</div>
    <div class="desc">{descricao do evento}</div>
    <span class="pill pill-blue">{tipo curto}</span>
  </div>
</div>
```
Classes de sentimento do item: `positive`, `neutral`, `concern`, `constructive`.

#### Pills
```html
<span class="pill pill-green">Concluida</span>
<span class="pill pill-amber">Em andamento</span>
<span class="pill pill-red">Bloqueada</span>
<span class="pill pill-purple">Condutora</span>
<span class="pill pill-gray">N/A</span>
```

#### Tags por categoria
```html
<span class="tag tag-sistema">Sistema ERP</span>
<span class="tag tag-pessoa">Joao (PO)</span>
<span class="tag tag-orgao">STI</span>
<span class="tag tag-tech">Angular</span>
<span class="tag tag-ferramenta">Jira</span>
```

#### Tabela
```html
<div class="card">
  <h3>ACOES E PROXIMOS PASSOS</h3>
  <table>
    <thead>
      <tr><th>Acao</th><th>Responsavel</th><th>Prazo</th><th>Prioridade</th><th>Status</th></tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>{acao}</strong></td>
        <td>{resp}</td>
        <td>{prazo}</td>
        <td><span class="pill pill-red">Alta</span></td>
        <td><span class="pill pill-amber">Em andamento</span></td>
      </tr>
    </tbody>
  </table>
</div>
```

#### Flow diagram
```html
<div class="card">
  <h3>FLUXO DO PROCESSO</h3>
  <div class="flow">
    <div class="flow-step">1. {etapa}</div>
    <span class="flow-arrow">&rarr;</span>
    <div class="flow-step">2. {etapa}</div>
    <span class="flow-arrow">&rarr;</span>
    <div class="flow-step">3. {etapa}</div>
  </div>
</div>
```

#### Word Cloud
```html
<div class="word-cloud">
  <span style="font-size:2rem;color:#4f46e5;font-weight:700">{palavra principal}</span>
  <span style="font-size:1.7rem;color:#7c3aed;font-weight:700">{palavra}</span>
  <span style="font-size:1.4rem;color:#10b981;font-weight:600">{palavra}</span>
  <span style="font-size:1.2rem;color:#3b82f6;font-weight:600">{palavra}</span>
  <span style="font-size:1rem;color:#8b5cf6">{palavra}</span>
  <span style="font-size:.9rem;color:#6b7280">{palavra}</span>
  <!-- Variar font-size de .82rem ate 2rem conforme peso/frequencia -->
  <!-- Variar cor entre accent, purple, green, blue, amber, muted -->
</div>
```

#### Gauge (confianca/consenso)
```html
<div class="gauge-container">
  <div class="gauge-value">{N}%</div>
  <p style="color:var(--text-muted);font-size:.85rem;margin:.25rem 0">{descricao breve}</p>
  <div class="gauge-bar">
    <div class="gauge-fill" style="width:{N}%;background:linear-gradient(90deg,var(--blue),var(--green))"></div>
  </div>
</div>
```

#### Transcript + Search
```html
<div class="card">
  <h3>TRANSCRICAO COMPLETA</h3>
  <input type="text" class="search-input" id="searchInput" placeholder="Buscar na transcricao...">
  <div class="transcript-box" id="transcriptBox"></div>
</div>
```

#### Footer
```html
<div class="footer">
  <p>Dashboard gerado em {DD/MM/YYYY HH:MM} | Fonte: transcricao Whisper (modelo medium, pt-BR)</p>
  <p style="margin-top:.25rem">Graficos de sentimento sao estimativas baseadas em analise linguistica e podem nao refletir com precisao as emocoes reais dos participantes.</p>
</div>
```

### 6.6 Graficos em HTML/CSS puro (sem JavaScript)

**NAO use Chart.js nem qualquer lib de graficos que dependa de JS.** Use os templates CSS abaixo para todas as visualizacoes. Adicione estes estilos ao bloco CSS principal (secao 6.3) na primeira vez que precisar:

```css
/* ---- Graficos CSS puros ---- */

/* Barra horizontal (speakers, topicos) */
.hbar { display: flex; flex-direction: column; gap: .7rem; }
.hbar-row { display: flex; align-items: center; gap: .75rem; font-size: .85rem; }
.hbar-label { flex: 0 0 130px; color: var(--text); font-weight: 500; }
.hbar-track { flex: 1; height: 22px; background: #f3f4f6; border-radius: 6px; overflow: hidden; }
.hbar-fill { height: 100%; border-radius: 6px; display: flex; align-items: center; justify-content: flex-end; padding-right: .5rem; color: #fff; font-size: .72rem; font-weight: 700; }

/* Donut via conic-gradient (sem JS) */
.donut-wrap { display: flex; flex-direction: column; align-items: center; gap: 1rem; }
.donut {
  width: 180px; height: 180px; border-radius: 50%;
  position: relative;
  /* a propriedade background e gerada inline com conic-gradient */
}
.donut::before {
  content: ''; position: absolute;
  inset: 30px; background: var(--card);
  border-radius: 50%;
}
.donut-legend { display: flex; flex-wrap: wrap; gap: .4rem .75rem; font-size: .78rem; justify-content: center; }
.donut-legend span { display: flex; align-items: center; gap: .35rem; color: var(--text); }
.donut-legend span::before { content: ''; width: 10px; height: 10px; border-radius: 2px; display: inline-block; }

/* Barra vertical por fases (engajamento) */
.vbars { display: flex; align-items: flex-end; justify-content: space-around; gap: .4rem; height: 200px; padding: .5rem 0 1.5rem; border-bottom: 1px solid var(--border); position: relative; }
.vbar { flex: 1; display: flex; flex-direction: column; align-items: center; gap: .25rem; position: relative; }
.vbar-stack { width: 100%; max-width: 28px; display: flex; flex-direction: column-reverse; }
.vbar-seg { width: 100%; min-height: 2px; }
.vbar-seg:first-child { border-radius: 0 0 4px 4px; }
.vbar-seg:last-child { border-radius: 4px 4px 0 0; }
.vbar-label { font-size: .66rem; color: var(--text-muted); text-align: center; position: absolute; bottom: -1.25rem; white-space: nowrap; transform: rotate(-30deg); transform-origin: center; }

/* Matriz de risco (probabilidade x impacto) */
.risk-matrix { position: relative; width: 100%; aspect-ratio: 1; max-width: 480px; margin: 0 auto; background: linear-gradient(135deg, #d1fae5 0%, #fef3c7 50%, #fee2e2 100%); border: 1px solid var(--border); border-radius: 8px; }
.risk-matrix::before, .risk-matrix::after { content: ''; position: absolute; background: rgba(0,0,0,.06); }
.risk-matrix::before { left: 0; right: 0; top: 50%; height: 1px; }
.risk-matrix::after  { top: 0; bottom: 0; left: 50%; width: 1px; }
.risk-axis-x, .risk-axis-y { position: absolute; font-size: .7rem; color: var(--text-muted); font-weight: 600; }
.risk-axis-x { bottom: -1.5rem; left: 50%; transform: translateX(-50%); }
.risk-axis-y { top: 50%; left: -2.5rem; transform: translateY(-50%) rotate(-90deg); transform-origin: center; }
.risk-dot {
  position: absolute; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: .7rem; font-weight: 700;
  transform: translate(-50%, 50%);
  box-shadow: 0 2px 6px rgba(0,0,0,.15);
}

/* Radar simplificado: lista vertical de metricas com mini-barras */
.radar-list { display: flex; flex-direction: column; gap: .6rem; }
.radar-row { display: flex; align-items: center; gap: .5rem; font-size: .82rem; }
.radar-row .lbl { flex: 0 0 100px; color: var(--text); font-weight: 500; }
.radar-row .track { flex: 1; height: 8px; background: #f3f4f6; border-radius: 4px; overflow: hidden; }
.radar-row .fill { height: 100%; background: linear-gradient(90deg, var(--blue), var(--accent)); border-radius: 4px; }
.radar-row .val { flex: 0 0 38px; text-align: right; color: var(--text-muted); font-size: .78rem; font-weight: 600; }

/* Sparkline temporal (svg estatico inline) */
.sparkline { width: 100%; max-width: 520px; height: 120px; display: block; margin: 0 auto; }
.sparkline path.area-accent { fill: rgba(79,70,229,.15); stroke: var(--accent); stroke-width: 2; }
.sparkline path.area-amber  { fill: rgba(245,158,11,.15); stroke: var(--amber);  stroke-width: 2; }
.sparkline-legend { display: flex; gap: 1rem; justify-content: center; font-size: .75rem; color: var(--text-muted); margin-top: .5rem; }
.sparkline-legend span { display: flex; align-items: center; gap: .35rem; }
.sparkline-legend span::before { content: ''; width: 12px; height: 3px; border-radius: 2px; }
```

**Templates HTML** (substituir valores conforme os dados reais da reuniao):

```html
<!-- 1. Donut de sentimento (conic-gradient inline) -->
<div class="card">
  <h3>Sentimento Geral</h3>
  <div class="donut-wrap">
    <div class="donut" style="background: conic-gradient(
      var(--green)  0%  35%,
      var(--blue)   35% 60%,
      var(--purple) 60% 80%,
      var(--amber)  80% 92%,
      var(--cyan)   92% 100%)"></div>
    <div class="donut-legend">
      <span><i style="background:var(--green)"></i> Colaborativo 35%</span>
      <span><i style="background:var(--blue)"></i> Tecnico 25%</span>
      <span><i style="background:var(--purple)"></i> Construtivo 20%</span>
      <span><i style="background:var(--amber)"></i> Preocupacao 12%</span>
      <span><i style="background:var(--cyan)"></i> Pragmatico 8%</span>
    </div>
  </div>
</div>

<!-- 2. Radar simplificado (lista vertical com barras) -->
<div class="card">
  <h3>Emocoes Detectadas</h3>
  <div class="radar-list">
    <div class="radar-row"><span class="lbl">Colaboracao</span><div class="track"><div class="fill" style="width:85%"></div></div><span class="val">85</span></div>
    <div class="radar-row"><span class="lbl">Curiosidade</span><div class="track"><div class="fill" style="width:60%"></div></div><span class="val">60</span></div>
    <div class="radar-row"><span class="lbl">Resolucao</span><div class="track"><div class="fill" style="width:70%"></div></div><span class="val">70</span></div>
    <div class="radar-row"><span class="lbl">Entusiasmo</span><div class="track"><div class="fill" style="width:40%"></div></div><span class="val">40</span></div>
    <div class="radar-row"><span class="lbl">Preocupacao</span><div class="track"><div class="fill" style="width:55%"></div></div><span class="val">55</span></div>
    <div class="radar-row"><span class="lbl">Pragmatismo</span><div class="track"><div class="fill" style="width:90%"></div></div><span class="val">90</span></div>
  </div>
</div>

<!-- 3. Sparkline temporal (SVG estatico inline — nao depende de JS) -->
<div class="card">
  <h3>Evolucao do Sentimento</h3>
  <svg class="sparkline" viewBox="0 0 520 120" preserveAspectRatio="none">
    <!-- Area sentimento: gerar o path "M x,y L x,y ... L x,y Z" a partir dos 11 pontos -->
    <path class="area-accent" d="M0,48 L52,54 L104,60 L156,66 L208,42 L260,36 L312,30 L364,30 L416,36 L468,48 L520,18 L520,120 L0,120 Z"/>
    <!-- Area engajamento -->
    <path class="area-amber"  d="M0,36 L52,30 L104,24 L156,18 L208,12 L260,18 L312,24 L364,18 L416,30 L468,24 L520,36 L520,120 L0,120 Z"/>
  </svg>
  <div class="sparkline-legend">
    <span style="color:var(--accent)"><i style="background:var(--accent)"></i> Sentimento</span>
    <span style="color:var(--amber)"><i style="background:var(--amber)"></i> Engajamento</span>
  </div>
</div>

<!-- 4. Barra horizontal (speakers, topicos) — reutilizavel -->
<div class="card">
  <h3>Distribuicao de Fala</h3>
  <div class="hbar">
    <div class="hbar-row">
      <div class="hbar-label">Narrador</div>
      <div class="hbar-track"><div class="hbar-fill" style="width:65%;background:var(--purple)">65%</div></div>
    </div>
    <div class="hbar-row">
      <div class="hbar-label">Joao</div>
      <div class="hbar-track"><div class="hbar-fill" style="width:25%;background:var(--blue)">25%</div></div>
    </div>
    <div class="hbar-row">
      <div class="hbar-label">Outros</div>
      <div class="hbar-track"><div class="hbar-fill" style="width:10%;background:var(--slate,#64748b)">10%</div></div>
    </div>
  </div>
</div>

<!-- 5. Barra vertical stacked (engajamento por fase) -->
<div class="card">
  <h3>Engajamento por Fase</h3>
  <div class="vbars">
    <div class="vbar">
      <div class="vbar-stack" style="height:65%">
        <div class="vbar-seg" style="height:50%;background:var(--blue)"></div>
        <div class="vbar-seg" style="height:15%;background:var(--rose,#f43f5e)"></div>
      </div>
      <span class="vbar-label">Abertura</span>
    </div>
    <!-- ... repetir por fase, altura total em % relativo ao maximo ... -->
  </div>
</div>

<!-- 6. Matriz de risco (dots posicionados em %) -->
<div class="card">
  <h3>Matriz de Risco (Probabilidade x Impacto)</h3>
  <div class="risk-matrix">
    <span class="risk-axis-x">Probabilidade &rarr;</span>
    <span class="risk-axis-y">Impacto &rarr;</span>
    <!-- Cada dot: left = probabilidade*10%, bottom = impacto*10% -->
    <div class="risk-dot" style="width:56px;height:56px;background:var(--red);left:80%;bottom:90%" title="Migracao quebra grades">R1</div>
    <div class="risk-dot" style="width:48px;height:48px;background:var(--amber);left:90%;bottom:70%" title="Oficina de matematica">R2</div>
    <div class="risk-dot" style="width:44px;height:44px;background:var(--purple);left:70%;bottom:80%" title="Perda de conteudo">R3</div>
  </div>
</div>
```

**Regras de calculo dos valores**:
- Donut: os percentuais DEVEM somar 100% (caso contrario o visual fica quebrado). Ajustar para totalizar exatamente 100%.
- Barras horizontais: `width` em porcentagem direta do valor (0-100%).
- Sparkline SVG: gerar os caminhos com Python, mapeando os pontos (0-100) para coordenadas SVG (viewBox 520x120, inverter Y). Cada path comeca no primeiro ponto, traca linhas para todos os demais, e fecha para baixo com `L 520,120 L 0,120 Z` para formar a area.
- Matriz de risco: `left` = probabilidade * 10% e `bottom` = impacto * 10%. Tamanho do dot proporcional a importancia (raio entre 30 e 60px).

### 6.7 Transcricao (e busca como progressive enhancement)

A transcricao completa deve estar **renderizada diretamente no HTML** (dentro do `<div class="transcript-box">`), nao injetada via JS. Se JS estiver desativado (Quick Look no iOS), o usuario ainda consegue ler a transcricao inteira.

```html
<div class="card">
  <h3>Transcricao Completa</h3>
  <!-- Campo de busca: aparece somente quando JS esta ativo; esconder via <noscript> -->
  <input type="text" class="search-input" id="searchInput" placeholder="Buscar na transcricao...">
  <noscript><style>#searchInput { display: none; }</style></noscript>
  <div class="transcript-box" id="transcriptBox">[00:00] Primeira fala...
[00:15] Segunda fala...
[00:32] Terceira fala...</div>
</div>
```

A busca fica como **progressive enhancement** (opcional — funciona quando JS roda, degrada silenciosamente quando nao roda):

```html
<script>
// Busca opcional. Se JS nao executar, a transcricao continua legivel.
(function() {
  var box = document.getElementById('transcriptBox');
  var input = document.getElementById('searchInput');
  if (!box || !input) return;
  var original = box.textContent;
  function render(term) {
    var safe = original.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    if (!term) { box.innerHTML = safe; return; }
    var escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    var regex = new RegExp('(' + escaped + ')', 'gi');
    box.innerHTML = safe.replace(regex, '<span class="highlight">$1</span>');
  }
  input.addEventListener('input', function() { render(this.value.trim()); });
})();
</script>
```

**IMPORTANTE**:
- A transcricao eh colocada **diretamente no HTML** (entre as tags `<div>`), nao em uma string JavaScript. Isso garante que ela aparece mesmo com JS desativado.
- Os caracteres `<`, `>` e `&` da transcricao devem ser escapados como entidades HTML ao serem embutidos (use Python para fazer isso).
- Preservar quebras de linha — a `.transcript-box` tem `white-space: pre-wrap`.

### 6.8 Regras para geracao do dashboard

- Arquivo **totalmente autocontido** — CSS inline, zero dependencias externas, zero uso de CDN
- **JavaScript NUNCA e necessario para ver dados** (OBRIGATORIO). iOS Quick Look, iOS Files Preview e AirDrop preview desativam JS em HTMLs locais. Todos os graficos devem ser HTML + CSS puros (ver secao 6.6). JS so pode existir para enhancements opcionais (ex: filtro de busca na transcricao) e a pagina deve continuar legivel se o JS nao executar.
- **NAO usar `<canvas>` nem Chart.js** — nem via CDN, nem inline
- Transcricao completa vai **renderizada direto no HTML**, nao dentro de uma string JS
- Abrir no navegador SEM dependencias locais e tambem no iOS Files/Quick Look
- Dados **derivados do conteudo real** — nunca inventar numeros
- Se uma secao nao tiver dados (ex: sem riscos identificados), **omitir completamente** ou marcar "Nenhum identificado"
- Manter consistencia visual — nao alterar CSS variables, cores ou espaçamentos
- **Legibilidade mobile (OBRIGATORIO)**: o `<head>` DEVE incluir `<meta name="color-scheme" content="light">` e o CSS DEVE ter `color-scheme: light` no `:root`. Sem essas duas garantias, iOS Safari e Chrome Android com dark mode do sistema aplicam inversao automatica e o texto fica branco/ilegivel. Inputs de formulario (ex: `.search-input`) devem ter `background` e `color` explicitos pelo mesmo motivo. Nunca remover essas linhas ao editar o CSS.
- Word cloud com 15-25 palavras significativas, filtrar stopwords PT-BR (e, ou, que, de, para, em, com, por, a, o, um, uma, os, as, na, no, da, do, etc.)
- Timeline usar classes `positive/neutral/concern/constructive` conforme tom
- Insight cards usar `decisao/finding/problema/acao` conforme tipo
- Transcricao inclui timestamps `[MM:SS]` antes de cada fala para facilitar leitura temporal
- Incluir `<h3>` com titulo em UPPERCASE em todos os cards de grafico/conteudo

---

## Fase 7: Apresentacao

Ao final, apresentar ao usuario:
- Caminho completo da pasta criada
- Lista dos 3 arquivos gerados (`transcricao.vtt`, `analise.md`, `dashboard.html`)
- Resumo executivo de 2-3 frases
- Sugestao: abrir o `dashboard.html` no navegador com `open "<caminho>"`

Perguntar: **"Deseja aprofundar algum ponto ou fazer perguntas sobre a reuniao?"**

Se sim, continuar a conversa usando a transcricao como contexto.

---

## Regras gerais

- **SEMPRE** mostrar progresso ao usuario em cada fase (extracao, transcricao, analise, geracao de arquivos)
- **SEMPRE** citar trechos literais entre aspas com timestamp quando relevante
- **NUNCA** inventar informacao que nao esta na transcricao
- **NUNCA** usar emojis nos arquivos gerados
- Se a transcricao falhar, mostrar o erro completo ao usuario
- Usar binarios com path completo: `/opt/homebrew/bin/ffmpeg`, `/Library/Frameworks/Python.framework/Versions/Current/bin/python3`
- Slug da pasta: kebab-case, lowercase, sem acentos, 3-5 palavras
- Todos os artefatos em portugues brasileiro
- Pasta de analise criada dentro da raiz do repositorio `ata.ai` (`$CLAUDE_PROJECT_DIR`), NAO no diretorio do arquivo de entrada nem no CWD atual
