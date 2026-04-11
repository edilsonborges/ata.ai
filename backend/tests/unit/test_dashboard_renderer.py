from app.services.analysis.schemas import AnalysisResult, Topic, Risk
from app.services.renderer.dashboard import render_dashboard


def test_dashboard_contains_title_and_meta_tags():
    a = AnalysisResult(slug="x", title="Minha Reuniao", duration="10:00", summary="s")
    html = render_dashboard(a, "transcricao")
    assert "<title>Minha Reuniao</title>" in html
    assert 'name="color-scheme" content="light"' in html
    assert "chart.js" not in html.lower()
    assert "conic-gradient" in html or "topics" not in html.lower()


def test_dashboard_omits_empty_sections():
    a = AnalysisResult(slug="x", title="T", duration="1:00", summary="s")
    html = render_dashboard(a, "")
    assert "Matriz de Risco" not in html
    assert "Timeline" not in html


def test_dashboard_renders_topic_bar():
    a = AnalysisResult(
        slug="x", title="T", duration="1:00", summary="s",
        topics=[Topic(title="API", summary="x", relevance_pct=80)],
    )
    html = render_dashboard(a, "")
    assert 'width:80%' in html
