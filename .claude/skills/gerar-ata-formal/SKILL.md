---
name: gerar-ata-formal
description: Use quando precisar transformar uma analise de reuniao em ata formal assinavel (HTML printable A4 com cabecalho institucional, pauta, deliberacoes, encerramento e linhas de assinatura). Opera sobre uma pasta analise_* existente gerada por /analisar-reuniao.
---

# Gerar Ata Formal

Voce e um redator juridico-corporativo. A partir de uma pasta `analise_DATA_HORA_slug/` existente gerada pelo comando `/analisar-reuniao`, produza uma **ata formal assinavel** em HTML printable (A4 retrato).

## Objetivo

Gerar o arquivo `ata_formal.html` **dentro da mesma pasta da analise**, com estrutura juridica formal: cabecalho institucional, identificacao, pauta, presenca, deliberacoes numeradas, encaminhamentos, encerramento e linhas de assinatura.

## Fase 0: Descobrir pasta de origem

1. Se o usuario passou um caminho de pasta `analise_*` em `$ARGUMENTS`, usar.
2. Se nao, listar pastas `analise_*` na raiz do repositorio (`$CLAUDE_PROJECT_DIR`) e usar a **mais recente** por data/hora no nome. Perguntar confirmacao antes de prosseguir se houver duvida.

```bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
ls -1d "$PROJECT_DIR"/analise_* 2>/dev/null | sort -r | head -5
```

Informar ao usuario qual pasta sera usada.

## Fase 1: Ler artefatos de origem

Ler os arquivos da pasta escolhida:

1. `analise.md` — fonte primaria de conteudo (resumo, topicos, decisoes, acoes, participantes)
2. `transcricao.vtt` — consulta opcional para validar citacoes

Extrair:
- Titulo e data da reuniao
- Duracao total
- Participantes com papel
- Pauta (topicos discutidos)
- Decisoes tomadas (numeradas)
- Acoes/encaminhamentos
- Observacoes relevantes

## Fase 2: Perguntar dados institucionais ausentes

Se `analise.md` nao contem os seguintes campos, perguntar ao usuario (uma pergunta por vez):

1. **Nome da instituicao/empresa** (ex: "Prefeitura de X", "Empresa Y", "Diretoria de Z")
2. **Local da reuniao** (ex: "Sala de reunioes da STI", "Online - Google Meet")
3. **Presidente/Condutor da reuniao** (nome + cargo)
4. **Secretario/Relator** (nome + cargo) — quem redigiu/relatou

Se o usuario nao souber, usar valores genericos explicitos (ex: "A definir", "Condutor: nao identificado na transcricao").

## Fase 3: Gerar ata_formal.html

Criar arquivo **self-contained** com CSS inline. Usar fonte serifada (Georgia/Times), layout A4 retrato, margens generosas para impressao.

### 3.1 Requisitos tecnicos

- `<html lang="pt-BR">`, charset UTF-8
- `@page { size: A4 portrait; margin: 2.5cm 2cm; }` para impressao
- Fonte serifa: `Georgia, 'Times New Roman', Times, serif`
- Cor de texto: `#1a1a1a` sobre fundo `#ffffff`
- **Modo light forcado**: `<meta name="color-scheme" content="light">` + `color-scheme: light` no `:root`
- Numero de paginas automatico via `@page`
- Print-friendly: tudo deve caber em paginas A4 com quebras naturais

### 3.2 Estrutura obrigatoria (ordem fixa)

```
1. Cabecalho institucional
   - Nome da instituicao (maiusculas, centralizado)
   - Subtitulo (unidade/diretoria)
2. Titulo: "ATA DE REUNIAO Nº {numero}/{ano}"
3. Preambulo padrao:
   "Aos {DD dias do mes de MM do ano de YYYY}, as {HH:MM} horas, reuniram-se
    em {local} os participantes abaixo identificados para tratar dos assuntos
    pautados nesta ata."
4. Secao "PARTICIPANTES" — tabela com Nome, Cargo/Papel, Presenca
5. Secao "PAUTA" — lista numerada dos topicos tratados
6. Secao "DELIBERACOES" — decisoes numeradas com contexto formal
7. Secao "ENCAMINHAMENTOS" — tabela de acoes (nº, descricao, responsavel, prazo)
8. Secao "OBSERVACOES" — informacoes relevantes (opcional, omitir se vazia)
9. Encerramento:
   "Nada mais havendo a tratar, foi encerrada a reuniao as {HH:MM}, da qual eu,
    {nome do relator}, lavrei a presente ata que, apos lida e aprovada, sera
    assinada pelos presentes."
10. Linhas de assinatura — uma por participante ativo (min. 2)
```

### 3.3 CSS base (copiar integralmente)

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
:root { color-scheme: light; }
@page { size: A4 portrait; margin: 2.5cm 2cm; }
html, body {
  background: #fff;
  color: #1a1a1a;
  font-family: Georgia, 'Times New Roman', Times, serif;
  font-size: 12pt;
  line-height: 1.55;
}
.page {
  max-width: 17cm;
  margin: 2rem auto;
  padding: 2rem 2.5rem;
  background: #fff;
  box-shadow: 0 0 10px rgba(0,0,0,.08);
}
.inst-header {
  text-align: center;
  border-bottom: 2px solid #1a1a1a;
  padding-bottom: 1rem;
  margin-bottom: 1.5rem;
}
.inst-header h1 {
  font-size: 14pt;
  letter-spacing: .06em;
  text-transform: uppercase;
  font-weight: 700;
}
.inst-header .subtitle {
  font-size: 11pt;
  margin-top: .3rem;
  font-style: italic;
}
.ata-title {
  text-align: center;
  font-size: 13pt;
  font-weight: 700;
  text-transform: uppercase;
  margin: 1.5rem 0 1rem;
  letter-spacing: .05em;
}
.preambulo {
  text-align: justify;
  text-indent: 2em;
  margin-bottom: 1.5rem;
}
.section-title {
  font-size: 12pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .04em;
  margin: 1.2rem 0 .6rem;
  border-bottom: 1px solid #1a1a1a;
  padding-bottom: .2rem;
}
ol.pauta, ol.deliberacoes {
  padding-left: 2em;
  text-align: justify;
}
ol.pauta li, ol.deliberacoes li {
  margin-bottom: .5rem;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: .5rem 0 1rem;
  font-size: 11pt;
}
th, td {
  border: 1px solid #1a1a1a;
  padding: .4rem .6rem;
  text-align: left;
  vertical-align: top;
}
th { background: #f0f0f0; font-weight: 700; }
.encerramento {
  text-align: justify;
  text-indent: 2em;
  margin: 1.5rem 0 2rem;
}
.assinaturas {
  margin-top: 3rem;
  page-break-inside: avoid;
}
.assinatura-linha {
  margin-bottom: 2.5rem;
  text-align: center;
}
.assinatura-linha .linha {
  border-top: 1px solid #1a1a1a;
  width: 70%;
  margin: 0 auto .2rem;
  padding-top: .3rem;
}
.assinatura-linha .nome { font-weight: 700; }
.assinatura-linha .cargo { font-size: 10pt; color: #555; font-style: italic; }
@media print {
  .page { box-shadow: none; margin: 0; padding: 0; max-width: none; }
  .section-title, .ata-title { page-break-after: avoid; }
  table, .assinatura-linha { page-break-inside: avoid; }
}
```

### 3.4 Template HTML completo

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="color-scheme" content="light">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ata de Reuniao — {titulo-curto}</title>
<style>{CSS acima}</style>
</head>
<body>
<div class="page">
  <div class="inst-header">
    <h1>{NOME DA INSTITUICAO}</h1>
    <div class="subtitle">{unidade/diretoria}</div>
  </div>

  <div class="ata-title">Ata de Reuniao — {Titulo}</div>

  <p class="preambulo">
    Aos {DD} dias do mes de {MM por extenso} do ano de {YYYY}, as {HH}h{MM},
    reuniram-se em {local} os participantes abaixo identificados para tratar
    dos assuntos constantes da pauta. A reuniao foi conduzida por
    {condutor}, tendo como relator(a) {relator}.
  </p>

  <div class="section-title">1. Participantes</div>
  <table>
    <thead><tr><th>Nome</th><th>Cargo / Papel</th><th>Presenca</th></tr></thead>
    <tbody>
      <tr><td>{nome}</td><td>{cargo}</td><td>Presente</td></tr>
      <!-- ... -->
    </tbody>
  </table>

  <div class="section-title">2. Pauta</div>
  <ol class="pauta">
    <li>{topico 1}</li>
    <li>{topico 2}</li>
  </ol>

  <div class="section-title">3. Deliberacoes</div>
  <ol class="deliberacoes">
    <li>
      <strong>{Titulo curto da decisao}.</strong>
      {Descricao formal em prosa, com contexto e motivacao. Usar linguagem
       juridica: "Deliberou-se por", "Ficou decidido que", "Restou acordado
       que", "O colegiado aprovou".}
    </li>
  </ol>

  <div class="section-title">4. Encaminhamentos</div>
  <table>
    <thead><tr><th style="width:5%">#</th><th>Descricao</th><th style="width:20%">Responsavel</th><th style="width:15%">Prazo</th></tr></thead>
    <tbody>
      <tr><td>1</td><td>{acao}</td><td>{resp}</td><td>{prazo}</td></tr>
    </tbody>
  </table>

  <!-- Observacoes (omitir se vazio) -->
  <div class="section-title">5. Observacoes</div>
  <p style="text-align:justify">{observacoes relevantes}</p>

  <p class="encerramento">
    Nada mais havendo a tratar, a reuniao foi encerrada as {HH}h{MM}, da qual
    eu, {relator}, lavrei a presente ata que, apos lida e aprovada, sera
    assinada pelos presentes.
  </p>

  <div class="assinaturas">
    <div class="assinatura-linha">
      <div class="linha"></div>
      <div class="nome">{Nome do participante 1}</div>
      <div class="cargo">{Cargo}</div>
    </div>
    <div class="assinatura-linha">
      <div class="linha"></div>
      <div class="nome">{Nome do participante 2}</div>
      <div class="cargo">{Cargo}</div>
    </div>
    <!-- ... uma por participante ativo -->
  </div>
</div>
</body>
</html>
```

## Fase 4: Salvar e reportar

```bash
# Escrever o HTML na pasta de origem
cat > "$PASTA/ata_formal.html" << 'EOF'
{...conteudo...}
EOF
```

Informar ao usuario:
- Caminho completo do arquivo gerado
- Tamanho em KB
- Sugestao: "Abra no navegador e use Ctrl+P / Cmd+P para imprimir ou salvar como PDF (A4 retrato)."

## Regras nao-negociaveis

- **Nunca inventar deliberacoes** que nao estejam na analise original. Se algo e ambiguo, formular em linguagem que deixa isso explicito ("Discutiu-se a possibilidade de...").
- **Nunca colocar emojis** no arquivo gerado.
- **Sempre incluir a pasta de origem** no caminho de saida (`{pasta}/ata_formal.html`).
- **Linguagem juridica-formal** em portugues brasileiro: usar "deliberou-se", "restou acordado", "o colegiado", "ficou estabelecido".
- **Modo light forcado** (meta tag + CSS) para garantir legibilidade em impressao/mobile.
- **Numero da ata**: se o usuario nao fornecer, usar sequencia baseada em quantas pastas `analise_*` existem no repo (ex: se e a 4a, numero 04/{ano}).
- **Sem rodape de IA**: a ata nao deve mencionar que foi gerada por IA ou Whisper. E um documento formal.
- **Omitir secoes vazias**: se nao houve observacoes, omitir a secao 5.
