# Quanto tá a gasolina?

Site que mostra o preço médio da gasolina, etanol, diesel, GNV e gás de cozinha em 385 cidades brasileiras, usando o levantamento semanal da ANP.

Site: https://rafaelchagas01.github.io/quanto-ta-a-gasolina/

A ANP publica os dados em planilhas Excel numa página do gov.br, uma por semana. Dá pra usar, mas não é prático pra quem só quer saber se vale abastecer com etanol na própria cidade. O projeto baixa essas planilhas sozinho, limpa os dados e monta um painel simples em cima.

## Como funciona

```
página da ANP ──> scraper (Python) ──> site/data/*.json ──> site estático (GitHub Pages)
                        ^
              GitHub Actions, 2x por semana
```

1. O scraper lê a página da ANP e acha os links das planilhas `resumo_semanal_lpc_*.xlsx`. O nome dos arquivos não segue um padrão fixo (já apareceu `2026-08-30-2026-09-5.xlsx`), então as datas são lidas com uma regex tolerante e validadas.
2. Baixa as últimas 12 semanas, com cache local, intervalo entre downloads e User-Agent identificado.
3. Lê a aba `MUNICIPIOS`, encontra o cabeçalho pela posição das colunas (não por número de linha) e descarta linhas inválidas: preço fora da faixa, mínimo maior que a média, sem postos pesquisados.
4. A ANP escreve os nomes sem acento ("SAO PAULO"). Os nomes certos vêm da API de localidades do IBGE.
5. Gera um JSON por estado, pra página carregar só o que precisa.
6. O workflow `coleta e publica` roda toda terça e sexta, faz commit só se os dados mudaram e publica no GitHub Pages.

## No site

- Preço médio de cada combustível na cidade e quanto mudou na semana
- Se compensa etanol ou gasolina (regra dos 70%)
- Gráfico das últimas semanas com a faixa entre o posto mais barato e o mais caro
- As 10 cidades mais baratas do estado
- A URL guarda estado, cidade e combustível, dá pra compartilhar o link

## Rodando local

Precisa de Python 3.12+.

```bash
python -m venv .venv
.venv/Scripts/activate        # no Linux/Mac: source .venv/bin/activate
pip install -r requirements-dev.txt

python -m pytest
python -m scraper --weeks 12
python -m http.server 8000 --directory site
```

## Stack

- Python: requests, BeautifulSoup, openpyxl, pytest
- Front: HTML, CSS e JavaScript sem framework. O gráfico é SVG feito à mão
- GitHub Actions + GitHub Pages

## Segurança

- Só baixa arquivos de `https://www.gov.br`, com timeout, limite de tamanho e checagem de que o conteúdo é mesmo um xlsx
- Dados validados antes de virar JSON
- No front, nada vindo dos dados é inserido como HTML (só `textContent`), e os parâmetros da URL são conferidos contra a lista de estados e combustíveis
- Content Security Policy sem scripts inline nem de terceiros
- Actions fixadas por hash de commit, permissões mínimas por job
- `pip-audit` roda no CI
- Nenhuma chave ou segredo: tudo que o projeto usa é público

O GitHub Pages não permite configurar headers HTTP, então a CSP vai numa meta tag. Por isso `frame-ancestors` e HSTS ficam por conta do próprio GitHub.

## Limitações

- A ANP pesquisa uma amostra de postos, não todos. O preço de um posto específico pode ser bem diferente da média.
- Só entram as 385 cidades que a ANP pesquisa.
- Se a ANP mudar o formato da planilha, o scraper para com erro em vez de publicar dado errado.
