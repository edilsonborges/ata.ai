---
name: consolidar-acoes
description: Use quando precisar de um painel unico com todas as acoes/encaminhamentos pendentes de todas as reunioes analisadas no repositorio, agrupadas por responsavel. Varre todas as pastas analise_*, extrai a secao "Acoes e Proximos Passos" e consolida.
---

# Consolidar Acoes Pendentes

Voce e um assistente de follow-up. Varre **todas as pastas `analise_*/`** na raiz do repositorio `ata.ai`, extrai acoes pendentes de cada `analise.md` e gera um painel consolidado com todas as pendencias agrupadas por responsavel.

## Objetivo

Gerar `acoes_consolidadas_YYYY-MM-DD.html` na **raiz do repositorio** com:

- Contador: total de acoes pendentes, por status, por responsavel, por prioridade
- Tabela unificada de todas as acoes pendentes
- Grupos por responsavel
- Link para reuniao de origem de cada acao

## Fase 0: Varrer pastas

```bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
find "$PROJECT_DIR" -maxdepth 2 -type d -name "analise_*" | sort
```

Cada pasta tem o formato `analise_DD-MM-YYYY_HH-MM-SS_slug`. Extrair:
- Data/hora
- Slug
- Caminho para `analise.md`

## Fase 1: Extrair acoes de cada analise.md

Cada `analise.md` tem uma secao com uma das seguintes estruturas (o formato pode variar ligeiramente):

```markdown
## Acoes e Proximos Passos

| Acao | Responsavel | Prazo | Prioridade | Status |
|------|-------------|-------|------------|--------|
| ... | ... | ... | ... | ... |
```

Ou com coluna `#` adicional. Ler cada analise.md e parsear a tabela.

**Regra para "pendente":** status NAO pode estar em `['Concluida', 'Concluido', 'Feito', 'Feita', 'Done']`. Tudo mais (A fazer, Em andamento, Bloqueada, Pendente, vazio, `-`) e considerado pendente.

Usar Python para parsear:

```python
import os, re, json, glob
from pathlib import Path

PROJECT_DIR = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
STATUS_CONCLUIDOS = {'concluida', 'concluido', 'feito', 'feita', 'done', 'ok'}

pastas = sorted(glob.glob(f"{PROJECT_DIR}/analise_*"), reverse=True)

acoes = []
for pasta in pastas:
    md_path = Path(pasta) / 'analise.md'
    if not md_path.exists():
        continue

    content = md_path.read_text(encoding='utf-8')

    # Extrair titulo e data
    titulo_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    titulo = titulo_match.group(1).strip() if titulo_match else Path(pasta).name

    data_match = re.search(r'\*\*Data\*\*:\s*(.+)', content)
    data_reuniao = data_match.group(1).strip() if data_match else ''

    # Extrair tabela de acoes
    acoes_section = re.search(
        r'##\s+A[cç][oõ]es\s+e?\s*Pr[oó]ximos\s+Passos.*?\n(.*?)(?=\n##\s|\Z)',
        content, re.DOTALL | re.IGNORECASE
    )
    if not acoes_section:
        continue

    # Parsear linhas da tabela (formato markdown)
    linhas = acoes_section.group(1).strip().split('\n')
    header_idx = None
    for i, linha in enumerate(linhas):
        if '|' in linha and 'Acao' in linha.replace('ç', 'c').replace('ã', 'a'):
            header_idx = i
            break

    if header_idx is None:
        continue

    headers = [h.strip().lower() for h in linhas[header_idx].strip('|').split('|')]
    # Pular linha de separador ---
    for linha in linhas[header_idx + 2:]:
        if not linha.strip() or not linha.strip().startswith('|'):
            continue
        cols = [c.strip() for c in linha.strip('|').split('|')]
        if len(cols) < 2:
            continue

        # Mapear colunas por header
        acao_dict = dict(zip(headers, cols))
        # Normalizar chaves (aliases comuns)
        acao = acao_dict.get('acao') or acao_dict.get('açao') or acao_dict.get('ação') or cols[0]
        responsavel = acao_dict.get('responsavel') or acao_dict.get('responsável') or ''
        prazo = acao_dict.get('prazo') or ''
        prioridade = acao_dict.get('prioridade') or ''
        status = acao_dict.get('status') or ''

        # Filtrar apenas pendentes
        status_norm = re.sub(r'[^a-z]', '', status.lower())
        if status_norm in STATUS_CONCLUIDOS:
            continue
        if not acao.strip() or acao.strip() in ('#', '-'):
            continue

        acoes.append({
            'acao': acao,
            'responsavel': responsavel or 'Nao atribuido',
            'prazo': prazo or '-',
            'prioridade': prioridade or 'Nao definida',
            'status': status or 'A fazer',
            'reuniao': titulo,
            'data_reuniao': data_reuniao,
            'pasta': Path(pasta).name,
        })

print(f"Total de acoes pendentes: {len(acoes)}")
with open('/tmp/acoes_consolidadas.json', 'w', encoding='utf-8') as f:
    json.dump(acoes, f, ensure_ascii=False, indent=2)
```

## Fase 2: Agrupar e estatisticas

Com a lista de acoes, calcular:

- Total de acoes pendentes
- Total por responsavel (top 5)
- Total por prioridade
- Total de reunioes com pendencias
- Acoes mais antigas (por data da reuniao)

## Fase 3: Gerar HTML consolidado

Criar `acoes_consolidadas_YYYY-MM-DD.html` usando a **mesma paleta do dashboard** (indigo, semanticos).

### 3.1 Estrutura

```
Header (gradient indigo)
├─ Titulo "Acoes Pendentes Consolidadas"
├─ Subtitulo com data de geracao

Meta cards (grid-4)
├─ Total pendentes
├─ Responsaveis unicos
├─ Reunioes com pendencias
├─ Acoes com prioridade alta

Tabela completa (filtravel)
├─ colunas: #, Acao, Responsavel, Prazo, Prioridade, Status, Reuniao, Data
├─ hover destaca linha
├─ input de busca filtra por qualquer coluna

Grupos por Responsavel (accordion ou cards)
├─ Card por responsavel com count
├─ Lista de acoes daquele responsavel
├─ Link para pasta analise_* de cada acao

Grupos por Prioridade
├─ Alta (vermelho), Media (ambar), Baixa (verde), N/D (cinza)
```

### 3.2 CSS

Copiar o CSS base do dashboard.html (ver `.claude/commands/analisar-reuniao.md` secao 6.3). Adicionar:

```css
.filter-bar {
  display: flex; gap: 1rem; align-items: center;
  margin-bottom: 1rem; flex-wrap: wrap;
}
.filter-bar .search-input { flex: 1; min-width: 200px; }
.filter-bar select {
  padding: .5rem .8rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card);
  color: var(--text);
  font-size: .9rem;
}
.resp-card {
  background: var(--card);
  border-radius: var(--radius);
  padding: 1.25rem;
  margin-bottom: 1rem;
  border-left: 4px solid var(--accent);
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.resp-card h3 {
  font-size: 1.05rem;
  color: var(--accent);
  margin-bottom: .6rem;
}
.resp-card .count {
  display: inline-block;
  background: var(--accent-light);
  color: var(--accent);
  padding: .1rem .6rem;
  border-radius: 999px;
  font-size: .8rem;
  font-weight: 600;
  margin-left: .5rem;
}
.resp-card ul { list-style: none; padding-left: 0; }
.resp-card li {
  padding: .5rem 0;
  border-bottom: 1px solid var(--border);
  font-size: .9rem;
}
.resp-card li:last-child { border-bottom: none; }
.resp-card .origem {
  font-size: .75rem;
  color: var(--text-muted);
  margin-top: .2rem;
}
.resp-card .origem a { color: var(--accent); text-decoration: none; }
```

### 3.3 JS para filtro

```js
const searchInput = document.getElementById('search');
const prioFilter = document.getElementById('prio-filter');
const rows = document.querySelectorAll('table tbody tr');

function applyFilter() {
  const term = searchInput.value.toLowerCase();
  const prio = prioFilter.value;
  rows.forEach(row => {
    const text = row.textContent.toLowerCase();
    const rowPrio = row.dataset.prio || '';
    const matchText = !term || text.includes(term);
    const matchPrio = !prio || rowPrio === prio;
    row.style.display = (matchText && matchPrio) ? '' : 'none';
  });
}
searchInput.addEventListener('input', applyFilter);
prioFilter.addEventListener('change', applyFilter);
```

## Fase 4: Salvar e reportar

```bash
DATA=$(date +"%Y-%m-%d")
OUTPUT="$PROJECT_DIR/acoes_consolidadas_${DATA}.html"
```

Informar:
- Total de acoes encontradas
- Total de responsaveis unicos
- Reunioes varridas (contagem)
- Caminho do HTML gerado
- Responsavel com mais acoes pendentes (top 1)

## Regras nao-negociaveis

- **Zero CDN, zero dependencia externa, zero JS para dados**: a tabela com todas as acoes deve vir renderizada **direto no HTML estatico**. O JS de filtro e apenas progressive enhancement — a pagina deve ser 100% legivel e navegavel sem JS (compativel com iOS Quick Look, AirDrop preview e Files.app preview).
- **Varrer apenas pastas na raiz do projeto** (`$CLAUDE_PROJECT_DIR`), nao recursivamente em subdiretorios profundos.
- **Incluir TODAS as reunioes** — nao filtrar por data a menos que o usuario peca explicitamente.
- **Normalizar responsaveis** — `"Joao"`, `"joao"`, `"João"` sao o mesmo. Usar `unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode().lower()` para comparacao, mas **manter o nome original** como label.
- **Agrupar "Time dev"/"Equipe"** como um responsavel coletivo separado.
- **Nunca modificar as analise.md originais**, so ler.
- **Paleta identica ao dashboard** — indigo + semanticos.
- **Modo light forcado** — `<meta name="color-scheme" content="light">` + CSS.
- **Salvar na raiz do repo**, nao dentro de uma pasta de analise especifica.
- **Se nao ha nenhuma acao pendente**, gerar pagina de "Parabens, nenhuma acao pendente" em vez de pagina vazia.
