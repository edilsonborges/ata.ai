---
name: gerar-pdf-reuniao
description: Use quando precisar exportar o dashboard.html ou a analise.md de uma reuniao para PDF (A4 printable) usando Chrome headless. Opera sobre pasta analise_* existente ou sobre os artefatos ata_formal.html / slides.html gerados por outras skills.
---

# Gerar PDF da Reuniao

Voce e um conversor de HTML → PDF. A partir de um arquivo HTML gerado por `/analisar-reuniao` (ou skills derivadas), produza um **PDF printable** usando Chrome headless.

## Objetivo

Converter um arquivo HTML (`dashboard.html`, `ata_formal.html` ou `slides.html`) em PDF **na mesma pasta**, preservando cores, graficos e layout.

## Dependencias

Usar Chrome headless via path absoluto. Tentar nesta ordem:

1. `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
2. `/Applications/Chromium.app/Contents/MacOS/Chromium`
3. `/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge`

Se nenhum existir, abortar com mensagem clara sugerindo instalacao do Chrome.

```bash
CHROME=""
for candidate in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium" \
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"; do
  if [ -x "$candidate" ]; then CHROME="$candidate"; break; fi
done

if [ -z "$CHROME" ]; then
  echo "ERRO: Chrome/Chromium/Edge nao encontrado. Instale via 'brew install --cask google-chrome'"
  exit 1
fi
```

## Fase 0: Descobrir arquivo de origem

1. Se `$ARGUMENTS` for um caminho de arquivo HTML, usar direto.
2. Se `$ARGUMENTS` for uma pasta `analise_*`, perguntar ao usuario qual HTML converter:
   - `dashboard.html` (padrao — dashboard executivo com graficos)
   - `ata_formal.html` (se existir)
   - `slides.html` (se existir)
3. Se vazio, listar pastas `analise_*` recentes e perguntar.

## Fase 1: Detectar tipo e escolher perfil de impressao

Cada tipo de HTML precisa de parametros diferentes:

| Tipo | Formato | Margens | Paisagem? | Backgrounds |
|------|---------|---------|-----------|-------------|
| `dashboard.html` | A4 | 1cm | Nao | Sim (graficos) |
| `ata_formal.html` | A4 | 2cm | Nao | Sim |
| `slides.html` | A4 | 0 | Sim | Sim |

## Fase 2: Executar Chrome headless

```bash
INPUT="$PASTA/dashboard.html"          # ou outro
OUTPUT="$PASTA/dashboard.pdf"
INPUT_URL="file://$INPUT"

"$CHROME" \
  --headless=new \
  --disable-gpu \
  --no-sandbox \
  --run-all-compositor-stages-before-draw \
  --virtual-time-budget=10000 \
  --print-to-pdf-no-header \
  --no-pdf-header-footer \
  --print-to-pdf="$OUTPUT" \
  "$INPUT_URL"
```

**Notas tecnicas criticas:**

- `--headless=new` — usar o novo headless (Chrome 112+), que suporta CSS print corretamente
- `--virtual-time-budget=10000` — da tempo do Chart.js renderizar antes do screenshot (10 segundos virtuais)
- `--run-all-compositor-stages-before-draw` — garante que os graficos estejam desenhados
- `--no-pdf-header-footer` — remove cabecalho/rodape automaticos do Chrome (URL, data)
- `file://` — URL obrigatoria para Chrome headless ler HTML local
- Nao usar `--print-to-pdf-no-header` sozinho (flag antiga); combinar com `--no-pdf-header-footer`

## Fase 3: Slides (tratamento especial)

Para `slides.html` (reveal.js), precisa de ?print-pdf no query string para ativar o modo PDF do reveal:

```bash
INPUT_URL="file://$INPUT?print-pdf"
```

E tambem o flag `--window-size=1280,720` para bater com o tamanho dos slides.

```bash
"$CHROME" \
  --headless=new \
  --disable-gpu \
  --no-pdf-header-footer \
  --virtual-time-budget=15000 \
  --window-size=1280,720 \
  --print-to-pdf="$OUTPUT" \
  "$INPUT_URL"
```

## Fase 4: Validar e reportar

Apos conversao, validar:

```bash
if [ -f "$OUTPUT" ] && [ -s "$OUTPUT" ]; then
  SIZE=$(du -h "$OUTPUT" | cut -f1)
  echo "PDF gerado: $OUTPUT ($SIZE)"
else
  echo "ERRO: PDF nao foi gerado ou esta vazio"
  exit 1
fi
```

Informar ao usuario:
- Caminho do PDF
- Tamanho em KB/MB
- Contagem aproximada de paginas (opcional: `pdftotext` se disponivel)

## Fase 5: Ajustes de qualidade (quando aplicavel)

Se o usuario reportar problemas visuais no PDF:

**Graficos nao aparecem** — aumentar `--virtual-time-budget` para 15000 ou 20000 (Chart.js demora para renderizar canvas)

**Cores desbotadas** — garantir que o CSS do HTML tenha `-webkit-print-color-adjust: exact; print-color-adjust: exact;` nos elementos coloridos (isso e padrao no dashboard.html gerado por `/analisar-reuniao`, nao deveria acontecer)

**Transcricao cortada** — no dashboard.html, adicionar `@media print { .transcript-box { max-height: none !important; overflow: visible !important; } }` (ja deve existir no CSS padrao)

**Slides cortados** — conferir que o HTML tem `?print-pdf` na URL e `--window-size=1280,720`

## Regras nao-negociaveis

- **Chrome headless, nao Puppeteer ou Playwright** — eles exigem `npm install`, o projeto nao tem Node. Chrome CLI e suficiente.
- **Paths absolutos** do Chrome — nao confiar em `which google-chrome` (pode nao estar no PATH).
- **Nao modificar o HTML original** — se precisar ajustar CSS para print, criar copia temporaria em `/tmp/`.
- **Output na mesma pasta do input** por padrao (`ata_formal.html` → `ata_formal.pdf`).
- **Virtual time budget minimo de 10s** para dashboard (Chart.js demora).
- **Sem watermark de IA** no PDF — saida limpa.
- **Validar que o arquivo nao esta vazio** apos gerar — `--headless=new` as vezes falha silenciosamente.
