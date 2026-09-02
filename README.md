# Mini-Projeto 2 — Análise da Tábua das Marés para Surfar

Tutorial em 3 etapas para os alunos do Trilha. Felipe Duarte e Nicholas
gostam de surfar, mas só vêm a João Pessoa em alguns períodos do ano. A
pergunta do projeto: **quando eles devem voltar para pegar as melhores
ondas?**

O repositório já traz a solução completa — é de propósito. A ideia é
rodar cada etapa, ler os comentários e conferir os CSVs e gráficos. O
detalhamento (schemas processados, heurística, limitações) está em
[`docs/projeto.md`](docs/projeto.md).

| Etapa | Tema | Arquivo |
|---|---|---|
| 1 | Engenharia de dados (web scraping + ETL) | `src/scrape.py` |
| 2 | Ciência de dados (EDA) | `notebooks/eda.ipynb` |
| 3 | Machine learning (classificação) | `notebooks/ml.ipynb` |

## Como rodar

Requer [`uv`](https://docs.astral.sh/uv/) instalado. Python `>= 3.14`
(veja `pyproject.toml`).

```bash
# 1. Instalar dependências (cria .venv automaticamente)
uv sync

# 2. Etapa 1 — coleta (~30 s, com pausa entre requests)
uv run python src/scrape.py

# 3. Etapas 2 e 3 — abrir o Jupyter a partir de notebooks/
#    Os caminhos dos CSVs são relativos: ../data/raw
cd notebooks
uv run jupyter notebook eda.ipynb
# depois: File → Open → ml.ipynb
```

A Etapa 2 precisa dos CSVs da Etapa 1. A Etapa 3 precisa do
`data/processed/dataset.csv` gerado na Etapa 2. Rode nessa ordem.

### Se algo der errado

| Sintoma | Causa comum |
|---|---|
| `FileNotFoundError` nos notebooks | Jupyter aberto na raiz do repo, não em `notebooks/` — ou a etapa anterior ainda não rodou |
| Scraper sem tabela / HTML inesperado | O site mudou o markup. Os seletores estão em `src/scrape.py`; inspecione a página e ajuste |
| Rede / timeout | Tente de novo. O script faz 14 requests com pausa de 1,5 s para não sobrecarregar o servidor |

## O que cada etapa produz

**Etapa 1** grava quatro CSVs em `data/raw/`:

| Arquivo | O que tem | Linhas típicas |
|---|---|---|
| `mares_2025.csv` | 4 marés/dia de 2025 inteiro (contexto histórico) | ~1.410 |
| `mares_previsao.csv` | 4 marés/dia do mês corrente (para juntar com a previsão) | ~120 |
| `ondas.csv` | altura de onda hora a hora dos próximos ~6 dias | ~144 |
| `vento.csv` | velocidade do vento hora a hora dos próximos ~7 dias | ~168 |

**Etapa 2** limpa, explora e junta tudo numa tabela horária
`data/processed/dataset.csv` (~144 linhas) — só na janela em que existem
onda e vento.

**Etapa 3** cria a label `surfavel` (RUIM / BOM / ÓTIMO) por heurística,
treina `DecisionTree`, `RandomForest` e `KNN` para reproduzi-la, e
ranqueia os melhores dias e horários da janela. Salva
`data/processed/dataset_rotulado.csv`.

As pastas `data/` e `reports/` são geradas na hora e não entram no git.

## Schema dos CSVs brutos

`mares_2025.csv` e `mares_previsao.csv` têm as mesmas colunas:

| coluna | tipo | descrição |
|---|---|---|
| `data` | `date` | data do evento (`YYYY-MM-DD`) |
| `horario` | `str` | hora da maré (`HH:MM`) |
| `altura_m` | `float` | altura da água em metros |
| `tipo` | `str` | `alta` ou `baixa` |
| `coeficiente` | `int` | coeficiente de maré (cerca de 27–114) |
| `dia_ciclo_lunar` | `int` | dia do ciclo lunar (1 = lua nova) |

`ondas.csv` e `vento.csv` também compartilham o schema:

| coluna | tipo | descrição |
|---|---|---|
| `data` | `date` | data da leitura |
| `hora` | `int` | hora do dia (0–23) |
| `direcao` | `str` | direção cardeal (`N`, `NE`, `ESE`, …) |
| `valor` | `float` | altura da onda (m) ou velocidade do vento (km/h) |
| `unidade` | `str` | `m` para ondas, `km/h` para vento |

O schema da tabela juntada e a regra da label `surfavel` estão em
[`docs/projeto.md`](docs/projeto.md).

## Estrutura

```
miniprojeto2/
├── src/scrape.py              # Etapa 1
├── notebooks/
│   ├── eda.ipynb              # Etapa 2
│   └── ml.ipynb               # Etapa 3
├── data/                      # gerado ao rodar (gitignored)
│   ├── raw/
│   └── processed/
├── docs/projeto.md            # schemas, heurística, limitações
├── pyproject.toml
└── README.md
```

## Fonte dos dados

<https://tabuademares.com/br/paraiba/joao-pessoa>

Três seções importam:

1. **Tabela mensal de marés** — o servidor devolve o mês pedido num POST
   com `fecha=YYYY-MM-01`. Por isso dá para baixar 2025 inteiro.
2. **Previsão de ondas** (`/previsao/ondas`) — ~6 dias à frente.
3. **Previsão de vento** (`/previsao/vento`) — ~7 dias à frente.

Marés históricas e previsão de onda/vento cobrem períodos diferentes.
Isso não é um defeito do tutorial: o classificador só ranqueia a janela
curta. Não dá para responder honestamente “qual o melhor mês do ano”
com o que o site publica hoje.
