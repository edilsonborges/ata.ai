from app.services.analysis.schemas import AnalysisResult, Topic, Decision
from app.services.renderer.markdown import render_markdown


def test_minimal_render():
    a = AnalysisResult(
        slug="x", title="Reuniao X", duration="12:34",
        summary="Discussao sobre api.",
    )
    md = render_markdown(a)
    assert "# Reuniao X" in md
    assert "Resumo Executivo" in md


def test_render_skips_empty_sections():
    a = AnalysisResult(slug="x", title="T", duration="01:00", summary="s")
    md = render_markdown(a)
    assert "## Decisoes" not in md
    assert "## Timeline" not in md


def test_render_topic_with_quote():
    a = AnalysisResult(
        slug="x", title="T", duration="01:00", summary="s",
        topics=[Topic(title="API", summary="rest vs grpc", relevance_pct=80,
                      quote="precisamos decidir", quote_ts="03:45")]
    )
    md = render_markdown(a)
    assert "### API (80%)" in md
    assert '"precisamos decidir"' in md
    assert "[03:45]" in md
