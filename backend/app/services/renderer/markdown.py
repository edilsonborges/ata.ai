from app.services.analysis.schemas import AnalysisResult


def render_markdown(a: AnalysisResult) -> str:
    lines: list[str] = []
    lines.append(f"# {a.title}")
    lines.append("")
    lines.append(f"**Data**: {a.meeting_date or 'Nao identificada'}  ")
    lines.append(f"**Duracao**: {a.duration}  ")
    if a.participants:
        lines.append(f"**Participantes**: {', '.join(p.name for p in a.participants)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Resumo Executivo")
    lines.append("")
    lines.append(a.summary)
    lines.append("")

    if a.participants:
        lines.append("## Participantes")
        lines.append("")
        lines.append("| Nome | Papel | Tipo |")
        lines.append("|------|-------|------|")
        for p in a.participants:
            lines.append(f"| {p.name} | {p.role or '-'} | {p.type or '-'} |")
        lines.append("")
        lines.append("> Nota: Whisper nao separa locutores. Atribuicao inferida por contexto.")
        lines.append("")

    if a.topics:
        lines.append("## Topicos Discutidos")
        lines.append("")
        for t in a.topics:
            lines.append(f"### {t.title} ({t.relevance_pct}%)")
            lines.append("")
            lines.append(t.summary)
            if t.quote:
                ts = f" — [{t.quote_ts}]" if t.quote_ts else ""
                lines.append("")
                lines.append(f'> "{t.quote}"{ts}')
            lines.append("")

    if a.decisions:
        lines.append("## Decisoes Tomadas")
        lines.append("")
        for i, d in enumerate(a.decisions, 1):
            ts = f" [{d.quote_ts}]" if d.quote_ts else ""
            extra = f" — {d.context}" if d.context else ""
            lines.append(f"{i}. **{d.text}**{ts}{extra}")
        lines.append("")

    if a.findings:
        lines.append("## Findings")
        lines.append("")
        for i, f in enumerate(a.findings, 1):
            extra = f" — {f.detail}" if f.detail else ""
            lines.append(f"{i}. **{f.text}**{extra}")
        lines.append("")

    if a.actions:
        lines.append("## Acoes e Proximos Passos")
        lines.append("")
        lines.append("| Acao | Responsavel | Prazo | Prioridade | Status |")
        lines.append("|------|-------------|-------|------------|--------|")
        for ac in a.actions:
            lines.append(
                f"| {ac.title} | {ac.owner or '-'} | {ac.deadline or '-'} | "
                f"{ac.priority or '-'} | {ac.status or '-'} |"
            )
        lines.append("")

    if a.risks:
        lines.append("## Riscos Identificados")
        lines.append("")
        lines.append("| Risco | Probabilidade | Impacto |")
        lines.append("|-------|---------------|---------|")
        for r in a.risks:
            lines.append(f"| {r.text} | {r.probability}/10 | {r.impact}/10 |")
        lines.append("")

    if a.timeline:
        lines.append("## Timeline de Eventos")
        lines.append("")
        for ev in a.timeline:
            lines.append(f"- **{ev.range}** ({ev.tone}) — {ev.title}: {ev.summary}")
        lines.append("")

    if a.entities:
        lines.append("## Entidades Mencionadas")
        lines.append("")
        by_kind: dict[str, list[str]] = {}
        for e in a.entities:
            by_kind.setdefault(e.kind, []).append(e.name)
        for kind, names in by_kind.items():
            lines.append(f"- **{kind.capitalize()}**: {', '.join(names)}")
        lines.append("")

    if a.sentiment or a.engagement:
        lines.append("## Sentimento e Dinamica")
        lines.append("")
        if a.sentiment:
            lines.append(f"- Sentimento geral: {a.sentiment}")
        if a.engagement:
            lines.append(f"- Engajamento: {a.engagement}")
        lines.append("")

    if a.insights:
        lines.append("## Insights")
        lines.append("")
        for ins in a.insights:
            lines.append(f"- {ins}")
        lines.append("")

    if a.flow:
        lines.append("## Fluxo / Processo")
        lines.append("")
        for i, step in enumerate(a.flow, 1):
            lines.append(f"{i}. {step}")
        lines.append("")

    return "\n".join(lines)
