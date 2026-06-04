# Mini-Projeto 2 — Termômetro Eleitoral 2026

> Análise de sentimento político sobre os candidatos à presidência do Brasil
> em 2026, a partir de tweets coletados na rede X.

A proposta é construir um **termômetro eleitoral** que responde:

1. **Quantidade de menções por candidato.**
2. **Palavras mais frequentes associadas a cada candidato.**
3. **Proporção de comentários positivos, negativos e neutros.**

O projeto é dividido nas três etapas pedagógicas da trilha:

| Etapa | Tema | Entregável |
|---|---|---|
| 1 | Engenharia de Dados (ETL) | `src/collect.py` — coleta via [`twikit`](https://github.com/d60/twikit) |
| 2 | Ciência de Dados (EDA) | `notebooks/analise.ipynb` (parte 1) |
| 3 | Machine Learning | `notebooks/analise.ipynb` (parte 2) — sentimento via [`pysentimiento`](https://github.com/pysentimiento/pysentimiento) |

> 📄 Spec completo em [`docs/superpowers/specs/2026-06-04-termometro-eleitoral-design.md`](docs/superpowers/specs/2026-06-04-termometro-eleitoral-design.md).

## Estrutura

```
miniprojeto2/
├── src/
│   └── collect.py              # Etapa 1: coleta com twikit
├── notebooks/
│   └── analise.ipynb           # Etapas 2 e 3: EDA + sentimento + termômetro
├── data/                       # gitignored, gerado pelo pipeline
│   ├── raw/tweets.csv          # ← saída da Etapa 1
│   └── processed/tweets_scored.csv  # ← saída da Etapa 3
├── reports/                    # gitignored, PNGs do termômetro
├── config.yaml                 # candidatos + parâmetros de coleta
├── .env.example                # credenciais X (copiar pra .env)
├── requirements.txt
└── README.md
```

## Como rodar

### 1. Instalar dependências

```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar credenciais X

A coleta usa `twikit`, uma biblioteca **não-oficial** que faz scraping
autenticado do X. Você precisa de uma conta — recomendamos **uma conta
secundária de teste**, pois existe risco de bloqueio.

```bash
cp .env.example .env
# edite .env com seu usuário, email e senha
```

Após o primeiro login, os cookies são salvos em `.twikit_cookies.json`
(gitignored) e reutilizados nas execuções seguintes.

### 3. Editar a lista de candidatos (opcional)

`config.yaml` traz os 12 candidatos à presidência 2026 com handles e
aliases. **Verifique os handles antes de rodar** — eles foram preenchidos
como referência inicial e podem estar desatualizados. Adicione/remova
candidatos à vontade.

### 4. Coletar os tweets

```bash
python src/collect.py
```

Ao final, o arquivo `data/raw/tweets.csv` é gerado.

> ⚠️ Rate limit: `search_tweet` no X é capado em **50 chamadas / 15 min**.
> Pra 12 candidatos × 200 tweets, a coleta leva alguns minutos com pausas
> automáticas.

### 5. Rodar a análise

```bash
jupyter notebook notebooks/analise.ipynb
```

O notebook faz limpeza, EDA, classificação de sentimento e gera os
gráficos do termômetro em `reports/`.

## Schema do CSV (`data/raw/tweets.csv`)

| Coluna | Tipo | Descrição |
|---|---|---|
| `tweet_id` | str | ID único (chave primária) |
| `candidate` | str | nome canônico do candidato |
| `query_matched` | str | termo da query que casou (handle/alias) |
| `text` | str | texto do tweet |
| `created_at` | datetime ISO | timestamp |
| `lang` | str | idioma detectado pelo X |
| `likes` | int | curtidas |
| `retweets` | int | retweets |
| `replies` | int | respostas |
| `author_id` | str | ID do autor |

## Limitações

- `twikit` é uma biblioteca não-oficial e pode quebrar a qualquer momento
  com mudanças do X.
- Contas usadas pra scraping podem ser bloqueadas. Use conta secundária.
- A análise de sentimento herda os vieses do modelo `pysentimiento`.
- Volume coletado é uma amostra recente, não exaustivo.

## Desafio extra (opcional)

Construir uma interface visual sobre o `tweets_scored.csv`:

- **Streamlit** — `streamlit run app.py` com filtros por candidato e gráficos interativos.
- **Next.js / React** — dashboard web servindo o CSV via API.

Não faz parte da entrega oficial — fica como bônus pra quem quiser ir além.

## Tecnologias

- **Python 3.10+**
- **twikit** — coleta de tweets
- **pandas / numpy** — manipulação de dados
- **matplotlib / seaborn / wordcloud** — visualizações
- **nltk** — stopwords PT
- **pysentimiento** — análise de sentimento em português
