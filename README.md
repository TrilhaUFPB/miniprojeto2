# Mini-Projeto 2 — Análise da Tábua das Marés para Surfar

> Trilha UFPB — projeto da semana para alunos do 1º período. Vamos ajudar
> Felipe e Nicholas a descobrir o melhor momento para voltar a João Pessoa
> e surfar.

A solução tem três etapas pedagógicas:

| Etapa | Tema | Entregável |
|---|---|---|
| 1 | Engenharia de dados (Web Scraping + ETL) | `src/scrape.py` |
| 2 | Ciência de dados (EDA) | `notebooks/eda.ipynb` |
| 3 | Machine learning (classificação) | `notebooks/ml.ipynb` *(em breve)* |

> 📄 Spec completo em
> [`docs/superpowers/specs/2026-06-05-surf-tabuademares-design.md`](docs/superpowers/specs/2026-06-05-surf-tabuademares-design.md).

## Como rodar

Requer [`uv`](https://docs.astral.sh/uv/) instalado.

```bash
# 1. Instalar dependências (cria .venv automaticamente)
uv sync

# 2. Rodar a Etapa 1 — coleta dos dados
uv run python src/scrape.py

# 3. Rodar a Etapa 2 — EDA
uv run jupyter notebook notebooks/eda.ipynb
```

A coleta leva cerca de 30 segundos (12 requests para marés do ano + 1
para o mês corrente + 2 para previsão, com pausa de 1.5s entre cada um
para não bater no servidor).

Ao final da Etapa 1, quatro CSVs aparecem em `data/raw/`:

| Arquivo | O que tem | Linhas típicas |
|---|---|---|
| `mares_2025.csv` | 4 marés/dia para o ano de 2025 inteiro | ~1.410 |
| `mares_previsao.csv` | 4 marés/dia do mês corrente (para a junção da EDA) | ~120 |
| `ondas.csv` | altura de onda hora a hora dos próximos ~6 dias | ~144 |
| `vento.csv` | velocidade do vento hora a hora dos próximos ~7 dias | ~168 |

A Etapa 2 (`notebooks/eda.ipynb`) consome esses CSVs, faz limpeza,
explora cada dataset, junta tudo numa tabela horária e salva
`data/processed/dataset.csv` (~144 linhas) — pronto para a Etapa 3.

## Schema dos CSVs

### `data/raw/mares_2025.csv`

| coluna | tipo | descrição |
|---|---|---|
| `data` | `date` | data do evento (YYYY-MM-DD) |
| `horario` | `str` | hora da maré, formato `HH:MM` |
| `altura_m` | `float` | altura da água em metros |
| `tipo` | `str` | `alta` ou `baixa` |
| `coeficiente` | `int` | coeficiente de maré (27–114) |
| `dia_ciclo_lunar` | `int` | dia dentro do ciclo lunar (1 = lua nova) |

### `data/raw/ondas.csv` e `data/raw/vento.csv`

| coluna | tipo | descrição |
|---|---|---|
| `data` | `date` | data da leitura |
| `hora` | `int` | hora do dia (0–23) |
| `direcao` | `str` | direção cardeal (`N`, `NE`, `ESE`, ...) |
| `valor` | `float` | altura da onda (m) ou velocidade do vento (km/h) |
| `unidade` | `str` | `m` para ondas, `km/h` para vento |

## Estrutura

```
miniprojeto2/
├── src/
│   └── scrape.py              # Etapa 1: web scraping + ETL
├── notebooks/                 # Etapas 2 e 3 (em breve)
├── data/
│   └── raw/                   # CSVs gerados pelo scraper (gitignored)
├── docs/superpowers/specs/    # design doc do projeto
├── pyproject.toml             # dependências (uv)
└── README.md
```

## Fonte dos dados

<https://tabuademares.com/br/paraiba/joao-pessoa>

A página tem três seções relevantes:

1. **Tabela mensal de marés** — renderizada pelo servidor a cada POST
   com `fecha=YYYY-MM-01`. Por isso conseguimos pegar 2025 inteiro.
2. **Previsão de ondas** (`/previsao/ondas`) — janela de ~6 dias à frente.
3. **Previsão de vento** (`/previsao/vento`) — janela de ~7 dias à frente.

A previsão de surf é uma janela curta porque é forward-looking. As
marés do ano todo dão contexto para a EDA, enquanto a previsão dá os
dados de onda/vento que serão usados no classificador da Etapa 3.
