from html import escape
from app.services.analysis.schemas import AnalysisResult


CSS = """
:root {
  color-scheme: light;
  --primary: #4f46e5;
  --primary-dark: #312e81;
  --purple: #7c3aed;
  --bg: #f8fafc;
  --surface: #ffffff;
  --text: #0f172a;
  --muted: #64748b;
  --border: #e2e8f0;
  --decisao: #16a34a;
  --finding: #d97706;
  --problema: #dc2626;
  --info: #2563eb;
  --construtivo: #7c3aed;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.5; }
.header { background: linear-gradient(135deg, #312e81, #4f46e5, #7c3aed);
  color: #fff; padding: 48px 32px; }
.header h1 { margin: 0 0 8px; font-size: 28px; }
.header .meta { opacity: 0.85; font-size: 14px; }
main { max-width: 1100px; margin: 0 auto; padding: 32px; }
section { background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 24px; margin-bottom: 24px; }
section h2 { margin: 0 0 16px; font-size: 20px; }
.meta-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
.meta-card { padding: 16px; border: 1px solid var(--border); border-radius: 8px; background: #fafbff; }
.meta-card .label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
.meta-card .value { font-size: 22px; font-weight: 600; margin-top: 4px; }
.bar { height: 8px; background: #eef2ff; border-radius: 4px; overflow: hidden; }
.bar > span { display: block; height: 100%; background: var(--primary); }
.topic { margin-bottom: 16px; }
.topic .title { display: flex; justify-content: space-between; font-weight: 600; }
.topic .summary { color: var(--muted); margin: 4px 0 8px; }
.donut { width: 160px; height: 160px; border-radius: 50%; margin: 0 auto; }
.donut-label { text-align: center; margin-top: 8px; font-size: 14px; color: var(--muted); }
.insight-card { padding: 16px; border-left: 4px solid var(--primary); background: #fafbff;
  margin-bottom: 12px; border-radius: 0 8px 8px 0; }
.insight-card.decisao { border-left-color: var(--decisao); background: #f0fdf4; }
.insight-card.finding { border-left-color: var(--finding); background: #fffbeb; }
.insight-card.problema { border-left-color: var(--problema); background: #fef2f2; }
.insight-card.acao { border-left-color: var(--info); background: #eff6ff; }
.timeline-item { display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--border); }
.timeline-item:last-child { border-bottom: none; }
.timeline-item .range { font-family: ui-monospace, monospace; color: var(--muted);
  min-width: 120px; font-size: 13px; }
.timeline-item.positive { border-left: 3px solid var(--decisao); padding-left: 12px; }
.timeline-item.neutral { border-left: 3px solid var(--muted); padding-left: 12px; }
.timeline-item.concern { border-left: 3px solid var(--problema); padding-left: 12px; }
.timeline-item.constructive { border-left: 3px solid var(--construtivo); padding-left: 12px; }
.tag { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px;
  font-weight: 500; margin: 2px; background: #eef2ff; color: var(--primary-dark); }
.tag-sistema { background: #dbeafe; color: #1d4ed8; }
.tag-orgao { background: #fae8ff; color: #86198f; }
.tag-tech { background: #dcfce7; color: #166534; }
.tag-ferramenta { background: #fef3c7; color: #92400e; }
.tag-pessoa { background: #fee2e2; color: #991b1b; }
.actions-table { width: 100%; border-collapse: collapse; }
.actions-table th, .actions-table td { text-align: left; padding: 10px;
  border-bottom: 1px solid var(--border); font-size: 14px; }
.actions-table th { background: #f1f5f9; }
.risk-matrix { display: grid; grid-template-columns: repeat(10, 1fr); gap: 2px;
  aspect-ratio: 1; max-width: 400px; margin: 0 auto; }
.risk-cell { background: #f1f5f9; border-radius: 2px; position: relative; }
.risk-dot { position: absolute; width: 14px; height: 14px; background: var(--problema);
  border-radius: 50%; top: 50%; left: 50%; transform: translate(-50%, -50%);
  border: 2px solid #fff; }
.transcript { font-family: ui-monospace, monospace; font-size: 13px;
  background: #f8fafc; padding: 16px; border-radius: 8px; max-height: 600px;
  overflow-y: auto; white-space: pre-wrap; }
.search-input { width: 100%; padding: 12px; border: 1px solid var(--border);
  border-radius: 8px; font-size: 14px; margin-bottom: 12px;
  background: #ffffff; color: #0f172a; }
footer { text-align: center; padding: 32px; color: var(--muted); font-size: 12px; }
"""


def _donut_conic(sentiment: str | None) -> str:
    # Representação visual simples do sentimento em conic-gradient.
    if not sentiment:
        return "background: conic-gradient(#e2e8f0 0 100%);"
    s = sentiment.lower()
    if "positiv" in s:
        return "background: conic-gradient(#16a34a 0 75%, #e2e8f0 75% 100%);"
    if "negativ" in s or "preoc" in s:
        return "background: conic-gradient(#dc2626 0 40%, #e2e8f0 40% 100%);"
    return "background: conic-gradient(#4f46e5 0 55%, #e2e8f0 55% 100%);"


def _kind_class(kind: str) -> str:
    mapping = {
        "sistema": "tag-sistema", "orgao": "tag-orgao", "tech": "tag-tech",
        "ferramenta": "tag-ferramenta", "pessoa": "tag-pessoa",
    }
    return mapping.get(kind, "")


def render_dashboard(a: AnalysisResult, transcript_text: str) -> str:
    meta_cards = [
        ("Duracao", a.duration),
        ("Data", a.meeting_date or "Nao identificada"),
        ("Participantes", str(len(a.participants))),
        ("Decisoes", str(len(a.decisions))),
        ("Acoes", str(len(a.actions))),
        ("Riscos", str(len(a.risks))),
    ]

    sections: list[str] = []

    sections.append(f"""
    <section>
      <h2>Visao Geral</h2>
      <div class="meta-cards">
        {''.join(f'<div class="meta-card"><div class="label">{escape(l)}</div><div class="value">{escape(v)}</div></div>' for l, v in meta_cards)}
      </div>
      <p style="margin-top: 20px; color: var(--muted);">{escape(a.summary)}</p>
    </section>
    """)

    if a.sentiment or a.engagement:
        style = _donut_conic(a.sentiment)
        sections.append(f"""
        <section>
          <h2>Sentimento e Dinamica</h2>
          <div class="donut" style="{style}"></div>
          <div class="donut-label">{escape(a.sentiment or '')}</div>
          {f'<p style="text-align:center;color:var(--muted);">Engajamento: {escape(a.engagement)}</p>' if a.engagement else ''}
        </section>
        """)

    if a.participants:
        chips = "".join(
            f'<span class="tag tag-pessoa">{escape(p.name)}'
            f'{f" ({escape(p.role)})" if p.role else ""}</span>'
            for p in a.participants
        )
        sections.append(f"""
        <section>
          <h2>Participantes</h2>
          {chips}
          <p style="color:var(--muted);font-size:13px;margin-top:12px;">Whisper nao separa locutores. Atribuicao inferida por contexto.</p>
        </section>
        """)

    if a.topics:
        items = "".join(
            f'<div class="topic">'
            f'<div class="title"><span>{escape(t.title)}</span><span>{t.relevance_pct}%</span></div>'
            f'<div class="summary">{escape(t.summary)}</div>'
            f'<div class="bar"><span style="width:{t.relevance_pct}%"></span></div>'
            f'</div>'
            for t in a.topics
        )
        sections.append(f'<section><h2>Topicos Discutidos</h2>{items}</section>')

    if a.entities:
        chips = "".join(
            f'<span class="tag {_kind_class(e.kind)}">{escape(e.name)}</span>'
            for e in a.entities
        )
        sections.append(f'<section><h2>Entidades</h2>{chips}</section>')

    if a.flow:
        steps = "".join(f"<li>{escape(s)}</li>" for s in a.flow)
        sections.append(f'<section><h2>Fluxo / Processo</h2><ol>{steps}</ol></section>')

    if a.timeline:
        items = "".join(
            f'<div class="timeline-item {escape(ev.tone)}">'
            f'<div class="range">{escape(ev.range)}</div>'
            f'<div><strong>{escape(ev.title)}</strong><br><span style="color:var(--muted);font-size:13px;">{escape(ev.summary)}</span></div>'
            f'</div>'
            for ev in a.timeline
        )
        sections.append(f'<section><h2>Timeline</h2>{items}</section>')

    cards: list[str] = []
    for d in a.decisions:
        cards.append(f'<div class="insight-card decisao"><strong>Decisao</strong><br>{escape(d.text)}</div>')
    for f in a.findings:
        cards.append(f'<div class="insight-card finding"><strong>Finding</strong><br>{escape(f.text)}</div>')
    for ins in a.insights:
        cards.append(f'<div class="insight-card"><strong>Insight</strong><br>{escape(ins)}</div>')
    if cards:
        sections.append(f'<section><h2>Insights e Decisoes</h2>{"".join(cards)}</section>')

    if a.risks:
        # Renderiza uma grade 10x10 com pontos nas coordenadas (prob, impact).
        cells = []
        for imp in range(10, 0, -1):
            for prob in range(1, 11):
                dot = next((r for r in a.risks if r.probability == prob and r.impact == imp), None)
                inner = '<div class="risk-dot"></div>' if dot else ""
                cells.append(f'<div class="risk-cell">{inner}</div>')
        grid = "".join(cells)
        sections.append(f"""
        <section>
          <h2>Matriz de Risco (Probabilidade x Impacto)</h2>
          <div class="risk-matrix">{grid}</div>
          <ul style="margin-top:16px;">
            {''.join(f'<li>{escape(r.text)} (P{r.probability}/I{r.impact})</li>' for r in a.risks)}
          </ul>
        </section>
        """)

    if a.actions:
        rows = "".join(
            f'<tr><td>{escape(ac.title)}</td><td>{escape(ac.owner or "-")}</td>'
            f'<td>{escape(ac.deadline or "-")}</td><td>{escape(ac.priority or "-")}</td>'
            f'<td>{escape(ac.status or "-")}</td></tr>'
            for ac in a.actions
        )
        sections.append(f"""
        <section>
          <h2>Acoes e Proximos Passos</h2>
          <table class="actions-table">
            <thead><tr><th>Acao</th><th>Responsavel</th><th>Prazo</th><th>Prioridade</th><th>Status</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </section>
        """)

    sections.append(f"""
    <section>
      <h2>Transcricao</h2>
      <input type="text" class="search-input" placeholder="Buscar na transcricao (enhancement JS)" id="q">
      <div class="transcript" id="t">{escape(transcript_text)}</div>
    </section>
    """)

    enhancement_js = """
    <script>
      (function() {
        var q = document.getElementById('q');
        var t = document.getElementById('t');
        if (!q || !t) return;
        var original = t.textContent;
        q.addEventListener('input', function() {
          var term = q.value.trim();
          if (!term) { t.textContent = original; return; }
          var re = new RegExp(term.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&'), 'gi');
          var rendered = original.replace(re, function(m) {
            return '<<<MARK>>>' + m + '<<<ENDMARK>>>';
          });
          t.innerHTML = rendered
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/&lt;&lt;&lt;MARK&gt;&gt;&gt;/g, '<mark>')
            .replace(/&lt;&lt;&lt;ENDMARK&gt;&gt;&gt;/g, '</mark>');
        });
      })();
    </script>
    """

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light">
<title>{escape(a.title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="header">
  <h1>{escape(a.title)}</h1>
  <div class="meta">{escape(a.meeting_date or '')} · {escape(a.duration)}</div>
</div>
<main>
{''.join(sections)}
</main>
<footer>Gerado por ata.ai · Nao inventa dados, cita trechos literais</footer>
{enhancement_js}
</body>
</html>
"""
    return html
