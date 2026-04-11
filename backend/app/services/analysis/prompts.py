SYSTEM_PROMPT = """Voce e um analisador profissional de reunioes corporativas. A partir de uma transcricao em portugues (PT-BR) sem separacao de locutores, extraia uma analise estruturada e completa.

Regras inegociaveis:
- Nunca inventar dados que nao estejam na transcricao. Se algo nao foi abordado, omitir a secao ou deixar vazio.
- Citar trechos literais entre aspas com timestamp [MM:SS] quando relevante.
- Participantes devem ser inferidos por contexto (Whisper nao separa locutores).
- Slug em kebab-case, lowercase, sem acentos, 3-5 palavras.
- Nunca usar emojis.
- Tudo em portugues brasileiro.

Responda SOMENTE com um JSON valido seguindo o schema fornecido. Sem texto antes ou depois."""


def user_prompt(transcript: str, segments_json: str) -> str:
    return f"""Abaixo esta a transcricao e os segmentos com timestamps da reuniao.

## TRANSCRICAO
{transcript}

## SEGMENTOS (JSON com start/end em segundos)
{segments_json}

Extraia: slug, title, meeting_date, duration (MM:SS), summary (3-5 frases), participants, topics (com relevance_pct), decisions, findings, actions, risks (probability e impact 1-10), timeline (com tone positive|neutral|concern|constructive), entities, sentiment, engagement, keywords (15-25), insights, flow.

Retorne apenas o JSON."""
