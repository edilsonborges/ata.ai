---
name: analisar-1on1
description: Use quando precisar analisar uma reuniao 1:1 (entrevista, feedback pessoal, review com gestor, mentoria). Foco em rapport, compromissos pessoais, feedback recebido e dado, temas de carreira. Gera pasta analise_1on1_* com markdown especializado e dashboard focado em 2 pessoas, sem matriz de risco nem multiplos participantes.
---

# Analisar Reuniao 1:1

Voce e um analisador de conversas 1:1. Versao especializada para **reunioes entre duas pessoas** (entrevista, feedback, 1:1 com gestor, mentoria, review de carreira). Foco diferente de reunioes em grupo: menos matriz de risco, mais rapport, compromissos pessoais, feedback.

## Quando usar (vs /analisar-reuniao)

| Situacao | Comando |
|----------|---------|
| Reuniao de equipe, tecnica, multi-stakeholder | `/analisar-reuniao` |
| 1:1 com gestor | `/analisar-1on1` |
| Entrevista de emprego | `/analisar-1on1` |
| Feedback pessoal / performance review | `/analisar-1on1` |
| Sessao de mentoria | `/analisar-1on1` |
| Coaching | `/analisar-1on1` |

## Dependencias

Iguais a `/analisar-reuniao`:
- `/opt/homebrew/bin/ffmpeg`
- `/Library/Frameworks/Python.framework/Versions/Current/bin/python3` com `whisper`

## Fase 0: Validacao e nomes

Alem do caminho do arquivo, perguntar os **dois nomes** envolvidos (se puder inferir da transcricao, confirmar):

- **Pessoa A** — quem voce e / quem esta sendo analisada
- **Pessoa B** — a outra parte (gestor, entrevistador, mentor, mentee)

Sem os nomes, a analise fica generica demais para ser util.

## Fase 1-2: Audio e Transcricao

Iguais ao `/analisar-reuniao` completo, mas modelo **`medium`** (importante: 1:1 costuma ter mais silencios, fala sobreposta e mudancas rapidas de tema — precisa da precisao do medium).

Saidas: `/tmp/1on1_audio.wav`, `/tmp/1on1_out/transcricao.vtt`, `/tmp/1on1_transcript.txt`, `/tmp/1on1_segments.json`.

## Fase 3: Analise especifica para 1:1

Ler transcricao e extrair:

### 3.1 Metadados

- Data, duracao
- Nome dos dois participantes
- Tipo inferido: {1:1 rotina / feedback formal / entrevista / mentoria / coaching}

### 3.2 Resumo executivo

3-4 frases: o que foi a conversa, tom geral, principais takeaways.

### 3.3 Temas abordados

Lista ordenada por tempo gasto (em %). Diferente do `/analisar-reuniao` onde sao "topicos tecnicos", aqui sao **temas conversacionais**:
- Carreira / crescimento
- Performance / entrega atual
- Bloqueios / frustracoes
- Relacionamento / time
- Expectativas / alinhamento
- Pessoal / saude mental (tratar com sensibilidade)
- Projetos especificos

### 3.4 Feedback dado e recebido

Duas listas separadas:

**Feedback que Pessoa A recebeu**:
- {ponto} — tom: {positivo/construtivo/critico} — [MM:SS]
- ...

**Feedback que Pessoa A deu**:
- {ponto} — sobre: {alguem/processo/projeto} — [MM:SS]
- ...

Se nao houver feedback em alguma direcao, omitir a secao.

### 3.5 Compromissos e proximos passos

Diferente de "acoes" de reunioes em grupo. Aqui sao **compromissos pessoais bilaterais**:

| Quem | Vai fazer | Ate quando |
|------|-----------|------------|
| Pessoa A | {compromisso} | {prazo} |
| Pessoa B | {compromisso} | {prazo} |

### 3.6 Rapport e dinamica

Analise qualitativa (1-2 paragrafos):

- Como foi o tom da conversa? (formal/informal, cordial/tensa)
- Balanceamento de fala (estimativa: ~60% A / ~40% B)
- Momentos de alinhamento
- Momentos de divergencia ou friccao
- Indicadores de confianca ou descontentamento

### 3.7 Pontos de atencao (se houver)

Observacoes sensiveis a destacar:

- Sinais de burnout/sobrecarga
- Conflitos mencionados
- Expectativas desalinhadas
- Promessas feitas sem contexto claro
- Feedback emocional forte (positivo ou negativo)

**Tom**: analitico, sem julgamento. Nao dar conselho psicologico, so descrever o que foi dito.

### 3.8 Citacoes memoraveis

3-5 trechos literais com timestamp que resumem a conversa. Preferencia por falas que capturam:
- Decisoes importantes
- Feedback claro
- Insights pessoais
- Compromissos explicitos

## Fase 4: Criar pasta

```bash
DATA=$(date +"%d-%m-%Y")
HORA=$(date +"%H-%M-%S")
SLUG="<slug-contextual>"  # ex: "1on1-joao-fevereiro", "feedback-trimestral", "mentoria-carreira"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
PASTA="${PROJECT_DIR}/analise_1on1_${DATA}_${HORA}_${SLUG}"
mkdir -p "$PASTA"
cp /tmp/1on1_out/transcricao.vtt "$PASTA/transcricao.vtt"
```

Prefixo **`analise_1on1_`** para diferenciar no `ls`.

## Fase 5: Gerar `analise_1on1.md`

```markdown
# 1:1 — {Pessoa A} & {Pessoa B}

**Data**: {DD/MM/YYYY}
**Duracao**: {MM:SS}
**Tipo**: {1:1 rotina / feedback formal / entrevista / mentoria / coaching}

---

## Resumo

{3-4 frases sobre o que foi a conversa}

## Temas Abordados

### 1. {Tema} ({X}%)
{Resumo do que foi dito sobre esse tema}

> "{citacao}" — [MM:SS]

## Feedback Recebido por {Pessoa A}

- **{ponto}** — {tom} — [MM:SS]

## Feedback Dado por {Pessoa A}

- **{ponto}** — sobre {alvo} — [MM:SS]

## Compromissos

| Quem | Vai fazer | Ate quando |
|------|-----------|------------|
| {Pessoa A} | {compromisso} | {prazo} |
| {Pessoa B} | {compromisso} | {prazo} |

## Rapport e Dinamica

{1-2 paragrafos analiticos sobre o tom e balanceamento}

**Distribuicao de fala estimada**: {A}% / {B}%

## Pontos de Atencao

- {observacao sensivel se houver}

## Citacoes Memoraveis

1. > "{trecho}" — [MM:SS]
2. > "{trecho}" — [MM:SS]
3. > "{trecho}" — [MM:SS]

---

*Analise 1:1 gerada a partir de transcricao Whisper (modelo medium, pt-BR). Esta analise e privada por natureza — evite compartilhar sem o consentimento das duas pessoas.*
```

## Fase 6: Gerar `dashboard_1on1.html`

Dashboard simplificado seguindo as convencoes do CLAUDE.md do projeto:

- **Zero CDN, zero JS para dados, zero dependencia externa**
- Paleta indigo + semanticos
- Modo light forcado
- Layout 1-pager compacto

### Estrutura

```
<header class="header gradient-indigo">
  <div class="badge">Conversa 1:1</div>
  <h1>{Pessoa A} & {Pessoa B}</h1>
  <div class="meta">{data} · {duracao} · {tipo}</div>
</header>
<div class="container">

  <div class="grid-3">
    <meta-card>Duracao</meta-card>
    <meta-card>Tom geral</meta-card>
    <meta-card>Compromissos</meta-card>
  </div>

  <div class="grid-2">
    <div class="card">
      <h3>Balanceamento de fala</h3>
      <!-- Barra HTML puro com width:% -->
      <div class="bar-split">
        <div class="bar-a" style="width:60%"></div>
        <div class="bar-b" style="width:40%"></div>
      </div>
      <div class="legend">
        <span>{A}: 60%</span>
        <span>{B}: 40%</span>
      </div>
    </div>
    <div class="card">
      <h3>Temas (minutos gastos)</h3>
      <!-- Barras horizontais HTML puro -->
      <div class="hbar">
        <span class="label">Carreira</span>
        <div class="fill" style="width:40%"></div>
        <span class="val">12min</span>
      </div>
    </div>
  </div>

  <div class="grid-2">
    <div class="card insight-card verde">
      <h3>Feedback Recebido</h3>
      <ul> ... </ul>
    </div>
    <div class="card insight-card azul">
      <h3>Feedback Dado</h3>
      <ul> ... </ul>
    </div>
  </div>

  <div class="card">
    <h3>Compromissos</h3>
    <table>
      <thead><tr><th>Quem</th><th>Vai fazer</th><th>Ate</th></tr></thead>
      <tbody> ... </tbody>
    </table>
  </div>

  <div class="card">
    <h3>Citacoes Memoraveis</h3>
    <blockquote class="quote"> ... </blockquote>
  </div>

  <div class="card">
    <h3>Transcricao</h3>
    <input class="search-input" placeholder="Buscar na transcricao...">
    <div class="transcript-box">
      <!-- Transcricao renderizada direto no HTML, nao em string JS -->
      {transcricao_vtt_convertida_em_p_com_timestamps}
    </div>
  </div>

</div>
```

**Atencao especial**: NAO usar matriz de risco, NAO usar word cloud, NAO usar timeline de eventos (inapropriado para 1:1). Usar apenas: balanceamento de fala, temas, feedback cards, compromissos, citacoes, transcricao.

## Regras nao-negociaveis

- **Privacidade primeiro**: adicionar nota no rodape do markdown e do dashboard: "Esta analise e privada por natureza — evite compartilhar sem o consentimento das duas pessoas envolvidas."
- **Nunca diagnosticar** estado emocional em termos clinicos (ex: "A pessoa esta deprimida"). Descrever apenas o que foi dito literalmente.
- **Nunca inventar feedback** — se nao houve feedback em uma direcao, omitir a secao.
- **Tom descritivo, nao prescritivo** — nao dar conselhos, nao sugerir acoes alem das explicitamente mencionadas.
- **Sempre identificar os dois nomes** — 1:1 anonimo perde o sentido. Perguntar se nao estiverem claros.
- **Pasta com prefixo `analise_1on1_`**.
- **Modelo Whisper `medium`** (nao small) — precisao importa em 1:1.
- **Zero CDN, zero JS para dados, zero dependencia externa** no dashboard.
- **Modo light forcado**.
- **Nunca gerar matriz de risco, word cloud, ou timeline** em 1:1 (reservados para reunioes em grupo).
- **Portugues brasileiro, sem emojis**.
- **Pasta dentro da raiz do repo**.
