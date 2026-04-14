---
name: gerar-slides
description: Use quando precisar gerar um slide deck executivo HTML self-contained a partir de uma analise de reuniao existente, para apresentar a lideranca ou stakeholders. Slides puro HTML+CSS (zero dependencias, sem JS, sem CDN), navegaveis por scroll-snap e printaveis 1 slide por pagina A4 paisagem. Opera sobre pasta analise_* gerada por /analisar-reuniao.
---

# Gerar Slides Executivos (HTML puro)

Voce e um designer de apresentacoes executivas. A partir de uma pasta `analise_DATA_HORA_slug/` existente, produza um **slide deck HTML** **self-contained sem nenhuma dependencia externa** — nem CDN, nem JS para dados, nem fontes remotas.

## Restricoes criticas (heranca do CLAUDE.md)

- **Zero CDN. Zero <script src="http...">. Zero @import remoto.** Nada de reveal.js, Swiper, Chart.js.
- **JS proibido para renderizar conteudo.** Todo o texto/dados deve vir no HTML estatico. JS so pode existir como progressive enhancement (ex: `scrollTo` em clique de indice) e a pagina deve ser 100% utilizavel sem JS.
- **iOS Quick Look / AirDrop preview** desativam JS em HTML local — a apresentacao precisa funcionar nesse modo.
- **Modo light forcado**: `<meta name="color-scheme" content="light">` + `color-scheme: light` no CSS.
- **Paleta identica ao dashboard**: indigo `#4f46e5`, gradient `#312e81 → #4f46e5 → #7c3aed`, semanticos verde/vermelho/ambar/azul/roxo.
- **Print 1 slide por pagina**: A4 paisagem, page-break-after: always em cada slide.
- **Fontes system stack** (sem Google Fonts): `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`.

## Objetivo

Gerar `slides.html` **dentro da pasta da analise original**, com 8-12 slides navegaveis via scroll-snap (rolar pra ver proximo slide) e printaveis (1 slide por pagina A4 paisagem).

## Fase 0: Descobrir pasta de origem

```bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
ls -1d "$PROJECT_DIR"/analise_* 2>/dev/null | sort -r | head -5
```

Usar `$ARGUMENTS` se fornecido; senao, a mais recente ou perguntar.

## Fase 1: Extrair dados de `analise.md`

Obrigatorios:

- Titulo e data da reuniao
- Duracao, participantes (top 5)
- Resumo executivo (3-5 frases)
- Top 3-5 topicos discutidos com relevancia
- Top 5 decisoes tomadas
- Top 5 acoes com responsavel e prazo
- Top 3 riscos (se houver)
- Proximos passos

## Fase 2: Estrutura obrigatoria dos slides (ordem fixa)

1. **Capa** — titulo grande + data/duracao/participantes (meta line)
2. **Contexto** — 2-4 bullets do porque da reuniao (opcional se nao claro no resumo)
3. **Agenda / Topicos** — lista numerada com relevancia visual
4. **Resumo Executivo** — 3-5 frases em bullets no meio do slide
5. **Participantes** — tabela compacta nome + papel (opcional, omitir se so 2)
6. **Decisoes Tomadas** — 1-2 slides, cards verdes com border-left
7. **Acoes e Prazos** — tabela com colunas: acao, responsavel, prazo, prioridade
8. **Riscos** — (opcional) cards vermelhos com Prob/Impacto
9. **Proximos Passos** — bullets
10. **Encerramento** — "Obrigado / Perguntas?"

Slides opcionais (2, 5, 8) sao **omitidos** se nao houver conteudo relevante.

## Fase 3: HTML template (copiar integralmente, preencher placeholders)

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="color-scheme" content="light">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{Titulo} — Slides</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  color-scheme: light;
  --bg: #f5f6fa;
  --card: #ffffff;
  --text: #1a1a2e;
  --text-muted: #6b7280;
  --accent: #4f46e5;
  --accent-dark: #312e81;
  --accent-light: #eef2ff;
  --green: #10b981;
  --red: #ef4444;
  --amber: #f59e0b;
  --blue: #3b82f6;
  --purple: #8b5cf6;
  --border: #e5e7eb;
}
html, body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.55;
  -webkit-text-size-adjust: 100%;
}
.deck {
  scroll-snap-type: y mandatory;
  height: 100vh;
  overflow-y: scroll;
  scroll-behavior: smooth;
}
.slide {
  scroll-snap-align: start;
  min-height: 100vh;
  padding: 4rem 5rem 3rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  position: relative;
  background: var(--bg);
}
.slide::after {
  content: counter(slide-num) ' / ' var(--total);
  counter-increment: slide-num;
  position: absolute;
  bottom: 1.5rem; right: 2rem;
  font-size: .75rem;
  color: var(--text-muted);
  letter-spacing: .05em;
}
.slide .kicker {
  font-size: .75rem;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: .08em;
  font-weight: 700;
  margin-bottom: .5rem;
}
.slide h1 {
  font-size: 3rem;
  font-weight: 800;
  line-height: 1.1;
  margin-bottom: .5rem;
  color: var(--accent-dark);
  letter-spacing: -.01em;
}
.slide h2 {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
  color: var(--accent-dark);
}
.slide .meta-line {
  font-size: 1rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: .06em;
  margin-top: 1rem;
}
.slide.title-slide {
  align-items: center;
  text-align: center;
  background: linear-gradient(135deg, #312e81, #4f46e5, #7c3aed);
  color: #fff;
}
.slide.title-slide h1 {
  font-size: 3.8rem;
  color: #fff;
  max-width: 80%;
}
.slide.title-slide .meta-line {
  color: rgba(255,255,255,.85);
}
.slide.title-slide::after { color: rgba(255,255,255,.5); }
.slide.closing {
  align-items: center;
  text-align: center;
  background: linear-gradient(135deg, #312e81, #4f46e5, #7c3aed);
  color: #fff;
}
.slide.closing h1 { color: #fff; font-size: 4.5rem; }
.slide.closing p { color: rgba(255,255,255,.85); font-size: 1.3rem; margin-top: 1rem; }
.slide.closing::after { color: rgba(255,255,255,.5); }
.bullets {
  list-style: none;
  padding-left: 0;
  font-size: 1.3rem;
  max-width: 90%;
}
.bullets li {
  padding: .6em 0 .6em 1.6em;
  position: relative;
}
.bullets li::before {
  content: '';
  position: absolute;
  left: 0; top: 1.1em;
  width: .6em; height: .6em;
  background: var(--accent);
  border-radius: 2px;
  transform: rotate(45deg);
}
.bullets li.num {
  counter-increment: bullet-num;
  padding-left: 2.4em;
}
.bullets li.num::before {
  content: counter(bullet-num);
  background: transparent;
  color: var(--accent);
  font-weight: 800;
  font-size: 1.3em;
  top: .3em;
  transform: none;
  width: auto; height: auto;
}
.callout {
  background: var(--accent-light);
  border-left: 5px solid var(--accent);
  padding: 1.5rem 2rem;
  border-radius: 0 12px 12px 0;
  font-size: 1.2rem;
  max-width: 85%;
  margin: 0 auto;
}
.card {
  background: var(--card);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
  margin-bottom: .8rem;
  border-left: 4px solid var(--accent);
}
.card.decision { border-left-color: var(--green); }
.card.decision strong { color: #065f46; }
.card.risk { border-left-color: var(--red); }
.card.risk strong { color: #991b1b; }
.card .sub {
  color: var(--text-muted);
  font-size: .92rem;
  margin-top: .3rem;
}
.card-grid {
  display: grid;
  gap: .8rem;
  width: 95%;
}
table {
  width: 95%;
  border-collapse: collapse;
  background: var(--card);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
  font-size: 1.05rem;
}
th {
  background: var(--accent-light);
  color: var(--accent);
  padding: .9rem 1.1rem;
  text-align: left;
  font-weight: 700;
  font-size: .95rem;
  text-transform: uppercase;
  letter-spacing: .04em;
}
td {
  padding: .9rem 1.1rem;
  border-bottom: 1px solid var(--border);
}
tr:last-child td { border-bottom: none; }
.pill {
  display: inline-block;
  padding: .2rem .7rem;
  border-radius: 999px;
  font-size: .8rem;
  font-weight: 700;
}
.pill-red   { background: #fee2e2; color: #991b1b; }
.pill-amber { background: #fef3c7; color: #92400e; }
.pill-green { background: #d1fae5; color: #065f46; }
.pill-blue  { background: #dbeafe; color: #1e40af; }

/* Navegacao sem JS: indice clicavel na capa */
.toc {
  list-style: none;
  padding-left: 0;
  font-size: 1rem;
  margin-top: 2rem;
}
.toc li { padding: .3rem 0; }
.toc a { color: inherit; text-decoration: none; opacity: .8; }
.toc a:hover { text-decoration: underline; opacity: 1; }

@media (max-width: 800px) {
  .slide { padding: 3rem 2rem 2.5rem; }
  .slide h1 { font-size: 2rem; }
  .slide.title-slide h1 { font-size: 2.4rem; }
  .slide h2 { font-size: 1.5rem; }
  .bullets { font-size: 1rem; }
  table { font-size: .85rem; }
  th, td { padding: .6rem .7rem; }
}

@media print {
  .deck { height: auto; overflow: visible; scroll-snap-type: none; }
  .slide {
    min-height: auto;
    height: auto;
    padding: 2cm;
    page-break-after: always;
    page-break-inside: avoid;
    background: #fff !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .slide:last-child { page-break-after: auto; }
  .slide::after { display: none; }
  @page { size: A4 landscape; margin: 0; }
}
body { counter-reset: slide-num; }
</style>
</head>
<body>
<div class="deck" style="--total:'{N_SLIDES}'">

  <!-- Slide 1: Capa -->
  <section class="slide title-slide">
    <div class="kicker">{Data · {DD/MM/YYYY}}</div>
    <h1>{Titulo da reuniao}</h1>
    <div class="meta-line">{duracao} · {N} participantes</div>
  </section>

  <!-- Slide 2: Contexto -->
  <section class="slide">
    <div class="kicker">Contexto</div>
    <h2>Por que essa reuniao aconteceu</h2>
    <ul class="bullets">
      <li>{bullet 1}</li>
      <li>{bullet 2}</li>
    </ul>
  </section>

  <!-- Slide 3: Agenda -->
  <section class="slide">
    <div class="kicker">Agenda</div>
    <h2>Topicos Discutidos</h2>
    <ul class="bullets">
      <li class="num">{topico 1}</li>
      <li class="num">{topico 2}</li>
    </ul>
  </section>

  <!-- Slide 4: Resumo Executivo -->
  <section class="slide">
    <div class="kicker">Resumo Executivo</div>
    <h2>O que voce precisa saber</h2>
    <div class="callout">
      <p>{frase 1}</p>
      <p style="margin-top:.8em">{frase 2}</p>
    </div>
  </section>

  <!-- Slide 5: Participantes (opcional) -->
  <section class="slide">
    <div class="kicker">Participantes</div>
    <h2>Quem estava na mesa</h2>
    <table>
      <thead><tr><th>Nome</th><th>Papel</th></tr></thead>
      <tbody>
        <tr><td>{nome}</td><td>{papel}</td></tr>
      </tbody>
    </table>
  </section>

  <!-- Slide 6: Decisoes -->
  <section class="slide">
    <div class="kicker">Decisoes</div>
    <h2>O que foi decidido</h2>
    <div class="card-grid">
      <div class="card decision">
        <strong>{Decisao 1}</strong>
        <div class="sub">{contexto curto}</div>
      </div>
      <div class="card decision">
        <strong>{Decisao 2}</strong>
        <div class="sub">{contexto}</div>
      </div>
    </div>
  </section>

  <!-- Slide 7: Acoes -->
  <section class="slide">
    <div class="kicker">Acoes</div>
    <h2>O que sera feito</h2>
    <table>
      <thead><tr><th>Acao</th><th>Responsavel</th><th>Prazo</th><th>Prio.</th></tr></thead>
      <tbody>
        <tr>
          <td>{acao}</td><td>{resp}</td><td>{prazo}</td>
          <td><span class="pill pill-red">Alta</span></td>
        </tr>
      </tbody>
    </table>
  </section>

  <!-- Slide 8: Riscos (opcional) -->
  <section class="slide">
    <div class="kicker">Riscos</div>
    <h2>Pontos de atencao</h2>
    <div class="card-grid">
      <div class="card risk">
        <strong>{Risco 1}</strong>
        <div class="sub">Probabilidade: {X}/10 · Impacto: {Y}/10</div>
      </div>
    </div>
  </section>

  <!-- Slide 9: Proximos Passos -->
  <section class="slide">
    <div class="kicker">Proximos Passos</div>
    <h2>O que vem a seguir</h2>
    <ul class="bullets">
      <li>{passo 1}</li>
      <li>{passo 2}</li>
    </ul>
  </section>

  <!-- Slide 10: Encerramento -->
  <section class="slide closing">
    <h1>Obrigado</h1>
    <p>Perguntas?</p>
  </section>

</div>
</body>
</html>
```

## Fase 4: Salvar e reportar

Escrever em `$PASTA/slides.html`. Reportar:

- Caminho completo
- Numero de slides gerados (excluindo omitidos)
- Sugestao: "Abra no navegador, role para navegar. Cmd+P / Ctrl+P para imprimir em A4 paisagem."

## Regras nao-negociaveis

- **Zero dependencia externa**: sem CDN, sem reveal.js, sem Chart.js, sem Google Fonts, sem SWiper, sem Swiper. Zero.
- **Zero JS para dados**: todo conteudo esta no HTML estatico. JS so pode ser um bloco curto de progressive enhancement e a pagina deve funcionar sem ele.
- **Funciona em iOS Quick Look** (AirDrop preview): testar mentalmente — a pagina renderiza sem JS ativo? Tem que sim.
- **Maximo 7 bullets por slide** — se houver mais, quebrar em 2 slides.
- **Textos curtos**: ate 15 palavras por bullet.
- **Nunca inventar slides**: se nao ha riscos, omitir o slide 8. Se participantes sao so 1-2, omitir o slide 5.
- **Sem emojis**.
- **Modo light forcado** (meta tag + CSS).
- **Paleta identica ao dashboard**.
- **Print A4 paisagem** com page-break-after em cada slide.
- **Salvar na pasta de origem**, nao na raiz do repo.
- **Scroll-snap** para navegacao moderna (desktop e mobile); em iOS Safari funciona nativo.
