# Templates de dashboard

Biblioteca de modelos HTML self-contained para o dashboard gerado pelo `/analisar-reuniao`. Servem como **ponto de partida visual** — o agente escolhe um template por conteudo da reuniao, carrega o HTML, e regenera um dashboard novo adaptando a estrutura e a identidade visual ao dado real da transcricao.

## Catalogo

| Arquivo | Quando usar | Identidade visual |
| --- | --- | --- |
| `executivo-clean.html` | Reunioes de decisao, alinhamento executivo, comites diretivos, steering. Foco em KPIs, decisoes, acoes e riscos. Participantes seniores e agenda objetiva. | Indigo corporativo com gradiente roxo no header. Hero de KPIs colado no topo. Tabelas limpas. Espacamento generoso. |
| `tecnico-denso.html` | Arquitetura, code review, discussao tecnica profunda, incidentes, post-mortems tecnicos, RFCs. Foco em findings, fluxos, dependencias e problemas. | Indigo + chrome slate. Tipografia sans + mono (JetBrains Mono para codigos/timestamps). Densidade alta. Sparklines SVG, fluxos diagramaticos, matriz de risco em bubble. |
| `retrospectiva-warm.html` | Retrospectivas de sprint, post-mortems colaborativos, team healthchecks, 1-on-1 em grupo. Peso emocional, alinhamento de time, sentimento em primeiro plano. | Indigo primario + acentos quentes (coral, ambar, teal). Cards arredondados grandes. Mood gauge, donut emocional, colunas start/stop/continue, avatares coloridos. |
| `minimalista-editorial.html` | Reunioes de diretoria em tom reflexivo, estrategia de longo prazo, reunioes que viram documento institucional, boards. Pouco numero, muita reflexao e citacao. | Preto sobre creme, serif editorial (Charter/Georgia), indigo como unico acento, drop cap na abertura, pull quotes grandes. Layout de coluna unica, ritmo de revista. |

## Como o agente deve escolher

Durante a fase 4 de `analisar-reuniao.md` (analise do conteudo), apos extrair topicos, acoes, sentimento e tipo da reuniao, escolher o template por **peso dominante**:

- Muitas **acoes + decisoes + tom executivo** → `executivo-clean`
- Muita **discussao tecnica + findings + codigo/sistemas** → `tecnico-denso`
- **Retrospectiva** explicita OU sentimento dominante + participantes do mesmo time → `retrospectiva-warm`
- Poucos KPIs, muita reflexao, **citacoes longas**, decisoes estruturais de alto nivel → `minimalista-editorial`

Em caso de empate (raro), preferir `executivo-clean` como default corporativo.

## Regras para adaptacao

Ao usar um template como base para gerar o `dashboard.html` final:

1. **Preserve a identidade visual rigidamente**: paleta, tipografia, radius dos cards, densidade, estilo dos graficos. O usuario escolheu o template por essas qualidades.
2. **Substitua 100% dos dados de amostra** por conteudo real da transcricao. Nao deixar nenhum texto "Lancamento Q2", "Refatoracao API", "Sprint 12", "Revisao Estrategica 2026" ou nomes fake no output final.
3. **Remova secoes sem conteudo real**. Se nao houve Matriz de Risco identificavel, remova a secao inteira em vez de deixar um placeholder vazio.
4. **Mantenha todas as restricoes nao-negociaveis do CLAUDE.md**: light mode forcado, zero JS para dados, CSS-only charts (conic-gradient, width %, SVG estatico), transcricao embutida em HTML, nenhum CDN externo, sem emojis nos artefatos.
5. **Pode omitir JS de busca** (nao e obrigatorio). Se mantiver, deve ser progressive enhancement - a pagina continua util sem ele.
6. **Adicione/remova secoes** conforme fizer sentido para o template escolhido. Ex: `retrospectiva-warm` pode nao ter "Matriz de Risco"; `minimalista-editorial` pode comprimir varias secoes em blocos de texto corrido.

## Como criar um novo template

1. Copie o `.html` mais proximo do tom desejado.
2. Atualize o comentario HTML do topo: nome, quando usar, identidade.
3. Ajuste `:root`, header e componentes.
4. Popule com dados de amostra realistas (nao "Lorem ipsum") para que o arquivo seja pre-visualizavel no navegador de forma convincente.
5. Adicione uma linha no catalogo deste README.
6. Atualize `.claude/commands/analisar-reuniao.md` se a regra de selecao mudar.
