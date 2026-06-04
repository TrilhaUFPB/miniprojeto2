# Mini-Projeto 2 — Termômetro Eleitoral 2026

**Status:** Aprovado
**Data:** 2026-06-04
**Autor:** Luigi Schmitt (TrilhaUFPB)

## Contexto

A versão anterior do mini-projeto 2 era sobre reconhecimento de emoções em
áudio (RAVDESS + TensorFlow + Streamlit). Foi descontinuada e o repositório
limpo. Este documento descreve a refatoração completa do mini-projeto com um
novo tema: **análise de sentimento político** sobre tweets dos candidatos à
presidência do Brasil em 2026.

## Objetivo

Construir um "termômetro eleitoral" que, a partir de tweets coletados sobre
os candidatos, responde:

1. **Quantidade de menções por candidato.**
2. **Palavras mais frequentes associadas a cada candidato.**
3. **Proporção de comentários positivos, negativos e neutros por candidato.**

A entrega segue as três etapas pedagógicas da trilha:

- **Engenharia de dados** — coleta via [`twikit`](https://github.com/d60/twikit) e ETL pra CSV.
- **Ciência de dados** — EDA sobre o CSV coletado.
- **Machine Learning** — classificação de sentimento com modelo pré-treinado.

## Decisões de escopo

| Decisão | Escolha |
|---|---|
| Tipo de entrega | Solução de referência completa (gabarito) |
| Coleta | Script `twikit` real, **CSV não comitado** — usuário precisa rodar a coleta com a própria conta X |
| Configuração | `config.yaml` com candidatos + parâmetros de coleta (aluno pode editar) |
| Modelo de sentimento | [`pysentimiento`](https://github.com/pysentimiento/pysentimiento) (PT) — modelo pré-treinado, sem treino custom |
| Formato da entrega | Notebook único (`analise.ipynb`) com EDA + ML + termômetro embutidos |
| Interface visual (Streamlit/Next.js) | **Extra opcional** mencionado no README; não faz parte da solução de referência |

## Arquitetura

```
config.yaml ──┐
              ▼
        ┌──────────────┐    data/raw/tweets.csv     ┌──────────────────┐
.env ──▶│ collect.py   │ ─────────────────────────▶ │ analise.ipynb    │
        │  (twikit)    │                            │  EDA + sentiment │
        └──────────────┘                            │  + termômetro    │
                                                    └──────────────────┘
                                                          │
                                                          ▼
                                              data/processed/tweets_scored.csv
                                                          +
                                                  reports/*.png
```

## Estrutura do repositório

```
miniprojeto2/
├── src/
│   └── collect.py              # ETL com twikit
├── notebooks/
│   └── analise.ipynb           # EDA + sentimento + termômetro
├── data/                       # gitignored
│   ├── raw/
│   │   └── tweets.csv          # gerado pela coleta
│   └── processed/
│       └── tweets_scored.csv   # gerado pelo notebook
├── reports/                    # gitignored, PNGs do termômetro
├── config.yaml                 # candidatos + parâmetros de coleta
├── .env.example                # X_USERNAME, X_EMAIL, X_PASSWORD
├── .gitignore                  # ignora data/, reports/, .env, cookies
├── requirements.txt
└── README.md
```

## Candidatos (lista de referência — 2026)

A solução de referência traz os candidatos à presidência 2026 já populados no
`config.yaml`. O aluno pode editar livremente.

- Lula (PT)
- Flávio Bolsonaro (PL)
- Ronaldo Caiado (PSD)
- Romeu Zema (Novo)
- Renan Santos (Missão)
- Aldo Rebelo (Democracia Cristã)
- Cabo Daciolo (Mobiliza)
- Augusto Cury (Avante)
- Hertz Dias (PSTU)
- Samara Martins (UP)
- Rui Costa Pimenta (PCO)
- Edmilson Costa (PCB)

## Etapa 1 — Coleta (`src/collect.py`)

### Configuração

**`config.yaml`:**

```yaml
collection:
  tweets_per_candidate: 200
  language: pt
  product: Latest               # twikit: Latest | Top
  since: 2026-01-01             # opcional
  rate_limit_sleep_seconds: 5

candidates:
  - name: Lula
    party: PT
    handle: LulaOficial
    aliases: [Lula, "Luiz Inácio", presidente Lula]
  - name: Flávio Bolsonaro
    party: PL
    handle: FlavioBolsonaro
    aliases: ["Flávio Bolsonaro", "Flavio Bolsonaro"]
  # ... demais candidatos
```

**`.env.example`:**

```
X_USERNAME=
X_EMAIL=
X_PASSWORD=
```

Cookies de sessão são persistidos em `.twikit_cookies.json` (gitignored) pra
não exigir re-login a cada execução.

### Comportamento do script

- Lê `config.yaml` e `.env`.
- Autentica via `twikit` (usa cookies se existirem; senão login completo).
- Pra cada candidato, monta query `(@handle OR "alias1" OR "alias2") lang:pt -is:retweet` e coleta até `tweets_per_candidate` tweets.
- Aplica `rate_limit_sleep_seconds` entre páginas/candidatos.
- Trata `TooManyRequests` com backoff (espera + retry).
- Normaliza tudo num DataFrame com schema fixo e salva em `data/raw/tweets.csv` (sobrescreve — sem estado entre execuções).
- Loga progresso por candidato (`X de Y tweets coletados`).

### Schema `data/raw/tweets.csv`

| coluna | tipo | descrição |
|---|---|---|
| `tweet_id` | str | ID único do tweet (chave primária; usado pra dedup) |
| `candidate` | str | nome canônico do candidato (`name` da config) |
| `query_matched` | str | qual termo da query casou (handle/alias) |
| `text` | str | texto bruto do tweet |
| `created_at` | datetime ISO | timestamp do tweet |
| `lang` | str | idioma detectado pelo X |
| `likes` | int | curtidas no momento da coleta |
| `retweets` | int | retweets no momento da coleta |
| `replies` | int | respostas no momento da coleta |
| `author_id` | str | ID do autor |

## Etapa 2+3 — Notebook `notebooks/analise.ipynb`

### `## 0. Setup`
Imports (`pandas`, `numpy`, `matplotlib`, `seaborn`, `wordcloud`, `nltk`,
`pysentimiento`, `re`, `tqdm`). Carrega CSV bruto, sanity check.

### `## 1. Limpeza e pré-processamento`
- Dedup por `tweet_id`.
- Filtro `lang == "pt"`.
- Cria `text_clean`: lowercase, remove URLs/menções/emojis/especiais; remove
  `#` mantendo o termo; colapsa espaços. `text` original é preservado.
- Cria `created_date` (granularidade dia).
- Tabela: volume antes/depois por candidato.

### `## 2. EDA`
- **2.1** Volume por candidato (barplot horizontal).
- **2.2** Volume ao longo do tempo (lineplot por candidato).
- **2.3** Engajamento médio (likes/retweets/replies) por candidato.
- **2.4** Top hashtags & menções globais e por candidato (regex no `text` original).
- Markdown interpretando cada gráfico.

### `## 3. Análise de sentimento`
- `analyzer = create_analyzer(task="sentiment", lang="pt")` (pysentimiento).
- Inferência em batches com `tqdm`.
- Cria `sentiment` (`POS`/`NEG`/`NEU`) e `sentiment_score` (prob da classe vencedora).
- Salva `data/processed/tweets_scored.csv`.
- Validação manual: imprime 5 amostras de cada classe.

### `## 4. Termômetro Eleitoral`
Os 3 produtos do enunciado:

- **4.1 Menções por candidato** — barplot horizontal "produto final".
- **4.2 Palavras mais frequentes** — tokeniza `text_clean`, remove stopwords PT
  (`nltk` + custom: nomes dos candidatos, "rt", etc.). Pra cada candidato,
  wordcloud + barplot top-15. Grid de subplots com todos.
- **4.3 Proporção pos/neg/neu** — barras empilhadas 100% por candidato
  (verde=POS, vermelho=NEG, cinza=NEU).

Salva PNGs em `reports/`.

### `## 5. Conclusões`
Ranking de menções, candidato mais positivo/negativo, palavras-chave
dominantes, limitações da análise.

### Schema `data/processed/tweets_scored.csv`
Mesmo schema de `tweets.csv` + `text_clean`, `sentiment`, `sentiment_score`.

### Contratos entre etapas
- Notebook **nunca** chama `twikit`.
- Se `data/raw/tweets.csv` não existir, célula 0 falha com mensagem clara:
  *"Rode `python src/collect.py` primeiro."*

## Reprodutibilidade & performance

- `random_state=42` em qualquer amostragem.
- `pysentimiento` é determinístico em modo eval.
- Volume típico (12 candidatos × 200 tweets = 2.4k): inferência em CPU ~2–3 min.
- GPU é usada automaticamente quando disponível.

## `requirements.txt`

```
twikit
pyyaml
python-dotenv
pandas
numpy
matplotlib
seaborn
wordcloud
nltk
pysentimiento
tqdm
jupyter
```

## README (pontos principais)

1. Visão geral do projeto + as 3 etapas.
2. Como rodar:
   - `pip install -r requirements.txt`
   - `cp .env.example .env` e preencher credenciais X.
   - Editar `config.yaml` com os candidatos desejados.
   - `python src/collect.py`
   - `jupyter notebook notebooks/analise.ipynb`
3. Estrutura do repo.
4. Limitações conhecidas: `twikit` é não-oficial, sujeito a rate limit / quebra.
5. **Desafio extra (opcional)**: criar interface visual em Streamlit ou Next.js
   consumindo `tweets_scored.csv`.

## Out of scope

- Treinamento de modelo de sentimento custom.
- Dashboard interativo (Streamlit/Next.js) — fica como desafio extra.
- Coleta incremental / persistência de estado entre execuções.
- Coleta de outras redes sociais além do X.
- Análise de imagens/vídeos.
