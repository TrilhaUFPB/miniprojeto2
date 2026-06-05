# Mini-Projeto 2 — Análise da Tábua das Marés para Surfar

> Refatoração completa do mini-projeto 2 da Trilha UFPB. Substitui a iteração
> anterior (Termômetro Eleitoral 2026 — ver
> `2026-06-04-termometro-eleitoral-design.md`).

## Contexto

O Trilha é um projeto de extensão da UFPB que ensina conceitos fundamentais de
computação para alunos do 1º período. Esse mini-projeto tem **uma semana** de
duração e cobre três etapas pedagógicas obrigatórias:

1. **Engenharia de dados** — Web Scraping + ETL
2. **Ciência de dados** — EDA
3. **Machine learning** — classificação (com modelos built-in do `scikit-learn`)

A história que motiva o projeto: Felipe Duarte e Nicholas, integrantes da
organização, gostam de surfar mas só vêm a João Pessoa em alguns períodos
do ano. O sistema responde: **quando devem voltar para aproveitar as melhores
ondas?**

## Escopo

- **Local**: João Pessoa, PB
- **Período de marés**: ano completo de 2025
- **Período de ondas**: janela de previsão disponível na fonte (~7–21 dias)
- **Fonte**: <https://tabuademares.com/br/paraiba/joao-pessoa>
- **Stack**: Python 3.14, `uv`, `pandas`, `matplotlib`/`seaborn`,
  `scikit-learn` (built-in), Jupyter

## Premissas verificadas no site

Antes de fechar o design, inspecionamos a página real. Achados:

- A **tabela de marés** é navegável mês a mês via `Day('YYYY-MM-01')` e cobre
  o ano de 2025 inteiro.
- A seção **"Ondas João Pessoa"** dá altura significativa, período, direção,
  vento na costa e vento no mar — **por hora** — para uma janela de cerca de
  7 a 21 dias à frente.
- **Não existe** uma classificação pronta de "ruim/bom/ótimo para surf" no
  site. As classificações textuais visíveis (`MUITO BOM/BOM/MAU`) referem-se
  a **estado para pesca**, que valoriza condições diferentes (mar calmo) do
  que o surf (onda formada). Não vamos reaproveitar esses rótulos.

Implicação de design: o label de surf será construído por nós a partir de
regras heurísticas aplicadas sobre as features cruas.

## Decisões de design (com justificativa)

| Decisão | Escolha | Por quê |
|---|---|---|
| Como rotular surf | Heurística por regras | Site não tem label pronto; pesca é proxy ruim. Regras de surf consagradas (altura, período, vento) são explicáveis e dão um problema de classificação real. |
| Janela de dados | Marés 2025 inteiro + ondas dos próximos dias | Único caminho honesto: marés são históricas, ondas são previsão. Documentar a limitação é parte do exercício. |
| Stack de scraping | Decidir na implementação (BeautifulSoup primeiro, Selenium se necessário) | Inspeção sugere HTML estático, mas confirmar olhando DevTools é parte da experiência. |
| Formato de entrega | 1 script `.py` + 2 notebooks (`eda.ipynb`, `ml.ipynb`) | Separação clara por etapa pedagógica. |
| Modelos de ML | `DecisionTreeClassifier`, `RandomForestClassifier`, `KNeighborsClassifier` | Built-in, interpretáveis (árvore plota), variedade suficiente para comparar. |

## Arquitetura

```
┌──────────────────────────┐    ┌──────────────────────────┐    ┌──────────────────────────┐
│   ETAPA 1 — ETL          │    │   ETAPA 2 — EDA          │    │   ETAPA 3 — ML           │
│   src/scrape.py          │ →  │   notebooks/eda.ipynb    │ →  │   notebooks/ml.ipynb     │
│                          │    │                          │    │                          │
│ • Marés mensais 2025     │    │ • Limpa & junta          │    │ • Cria label "surfável"  │
│ • Ondas horárias         │    │ • Estatísticas básicas   │    │   por regra heurística   │
│ • Salva CSVs em data/raw │    │ • Visualizações          │    │ • Treina 3 classifiers   │
│                          │    │ • Salva data/processed   │    │ • Avalia & responde     │
└──────────────────────────┘    └──────────────────────────┘    └──────────────────────────┘
```

### Fluxo de dados

- `data/raw/mares_2025.csv` — uma linha por evento de maré (alta/baixa) ao
  longo de 2025.
- `data/raw/ondas.csv` — uma linha por hora, da janela de previsão.
- `data/processed/dataset.csv` — junção horária de ondas + marés interpoladas
  + features temporais derivadas.
- `data/processed/dataset_rotulado.csv` — `dataset.csv` com a coluna
  `surfavel` (RUIM / BOM / ÓTIMO).
- `reports/*.png` — gráficos exportados pelos notebooks.

## Etapa 1 — Engenharia de Dados (Web Scraping + ETL)

**Entregável:** `src/scrape.py` e dois CSVs em `data/raw/`.

**Tarefas, em ordem:**

1. Inspecionar o HTML com DevTools — confirmar se BeautifulSoup basta ou se
   precisa de Selenium/Playwright.
2. Scraper de marés mensal — itera os 12 meses de 2025 navegando
   `Day('2025-MM-01')`. Extrai dia, horário, altura, fase lunar, coeficiente.
3. Scraper da seção "Ondas João Pessoa" — extrai a tabela horária com altura
   significativa, período, direção, vento na costa, vento no mar.
4. Politeness e tratamento de erro — `time.sleep(1-2s)` entre requests, header
   `User-Agent` próprio, retry simples em caso de falha de rede.

**Conceitos que os alunos aprendem:**

- HTTP requests, HTML parsing, estrutura do DOM
- Boas práticas de scraping (rate limit, identificação por UA, robots.txt)
- Persistência em CSV via `pandas.DataFrame.to_csv`

### Schema — `data/raw/mares_2025.csv`

| coluna | tipo | exemplo |
|---|---|---|
| `data` | date (`YYYY-MM-DD`) | `2025-06-05` |
| `horario` | time (`HH:MM`) | `06:55` |
| `altura_m` | float | `2.1` |
| `tipo` | str | `alta` / `baixa` |
| `coeficiente` | int | `78` |
| `fase_lunar` | str | `lua_cheia` |

### Schema — `data/raw/ondas.csv`

| coluna | tipo | exemplo |
|---|---|---|
| `datahora` | datetime ISO | `2026-06-05T14:00` |
| `altura_onda_m` | float | `1.2` |
| `periodo_s` | int | `9` |
| `direcao_onda_graus` | int | `130` |
| `vento_costa_kmh` | float | `12.3` |
| `vento_costa_direcao` | int | `90` |
| `vento_mar_kmh` | float | `18.0` |

## Etapa 2 — Ciência de Dados (EDA)

**Entregável:** `notebooks/eda.ipynb` + `data/processed/dataset.csv`.

**Tarefas, em ordem:**

1. Carregar e inspecionar — `pd.read_csv`, `.head()`, `.info()`, `.describe()`,
   verificar valores faltantes.
2. Limpeza — converter strings para `datetime`, vírgula decimal para ponto,
   tratar `NaN`, remover duplicatas.
3. Junção marés × ondas — para cada hora do `ondas.csv`, derivar:
   - `mare_subindo` (bool) — se está entre baixa e próxima alta
   - `altura_mare_interpolada` (float) — interpolação linear entre os 4
     eventos de maré do dia
   - `horas_ate_proxima_alta` (float)
4. Features temporais — `mes`, `dia_semana`, `hora`,
   `periodo_dia` (manhã/tarde/noite).
5. Visualizações:
   - Boxplot da altura de onda por mês
   - Heatmap mês × hora para velocidade de vento
   - Distribuição de períodos de onda (histograma)
   - Scatter altura de onda × altura de maré
   - Rosa dos ventos da direção das ondas
6. Insights documentados — célula markdown final com 3–5 conclusões.

**Conceitos que os alunos aprendem:**

- `pandas`: filtros, `groupby`, `merge`, manipulação de `datetime`
- Limpeza de dados reais (com sujeira)
- Visualização com `matplotlib` e `seaborn`
- Interpretação estatística básica

### Schema — `data/processed/dataset.csv` (uma linha por hora)

| categoria | colunas |
|---|---|
| Tempo | `datahora`, `data`, `mes`, `dia_semana`, `hora`, `periodo_dia` |
| Ondas | `altura_onda_m`, `periodo_s`, `direcao_onda_graus` |
| Vento | `vento_costa_kmh`, `vento_costa_direcao`, `vento_mar_kmh` |
| Maré | `altura_mare_interpolada`, `mare_subindo`, `coeficiente`, `fase_lunar` |

## Etapa 3 — Machine Learning

**Entregável:** `notebooks/ml.ipynb` + `data/processed/dataset_rotulado.csv` +
um markdown final respondendo "quando Felipe e Nicholas devem voltar?".

**Tarefas, em ordem:**

1. **Criar a label `surfavel`** — função pura em Python aplicando regras
   consagradas de surf:

   ```python
   def classificar(altura_m, periodo_s, vento_costa_kmh, mare_subindo):
       # vento forte na costa estraga qualquer onda
       if vento_costa_kmh > 25:
           return "RUIM"
       # onda muito pequena
       if altura_m < 0.5:
           return "RUIM"
       # janela ideal: onda formada, período longo (swell de qualidade)
       if 0.8 <= altura_m <= 2.0 and periodo_s >= 9:
           return "ÓTIMO"
       return "BOM"
   ```

   Os limiares ficam comentados e justificados no notebook.

2. Preparar `X` e `y` — separar features numéricas/categóricas, aplicar
   `train_test_split` (80/20).
3. Treinar três classificadores built-in:
   - `DecisionTreeClassifier(max_depth=4)` — interpretável, plotamos a árvore
   - `RandomForestClassifier(n_estimators=100)` — mais robusto
   - `KNeighborsClassifier(n_neighbors=5)` — comparação simples
4. Avaliar — `accuracy_score`, `classification_report`, `confusion_matrix`,
   `cross_val_score` com 5 folds. Plotar a árvore com
   `sklearn.tree.plot_tree`.
5. Importância de features — `feature_importances_` da Random Forest, gráfico
   de barras.
6. Aplicar o modelo no ano de 2025 — usar marés históricas + médias mensais
   das condições de onda/vento (com nota explícita sobre essa aproximação) e
   gerar:
   - Top 5 meses recomendados
   - Top 10 dias do próximo mês
   - Melhor horário médio do dia
7. Conclusão para Felipe e Nicholas — célula markdown final no notebook.

**Conceitos que os alunos aprendem:**

- Pipeline de ML: feature → label → split → train → evaluate
- Comparação entre classificadores
- Métricas: accuracy, precision, recall, matriz de confusão
- Cross-validation
- Interpretabilidade (árvore plotada, feature importance)

### Honestidade pedagógica

Como o site só fornece ~7–21 dias de previsão de ondas, o modelo "para o ano
todo" tem essa limitação clara. O notebook documenta isso e a Etapa 3 inclui
explicitamente uma seção `## Limitações`. Comunicar limitações é parte do
aprendizado.

## Estrutura final do repositório

```
miniprojeto2/
├── src/
│   └── scrape.py
├── notebooks/
│   ├── eda.ipynb
│   └── ml.ipynb
├── data/
│   ├── raw/                              # gitignored
│   │   ├── mares_2025.csv
│   │   └── ondas.csv
│   └── processed/                        # gitignored
│       ├── dataset.csv
│       └── dataset_rotulado.csv
├── reports/                              # gitignored, PNGs dos notebooks
├── pyproject.toml                        # deps via uv
├── README.md                             # explicação para os alunos
└── docs/superpowers/specs/
    └── 2026-06-05-surf-tabuademares-design.md   (este arquivo)
```

## Dependências (`pyproject.toml`)

```toml
[project]
name = "miniprojeto2"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
    "requests",
    "beautifulsoup4",
    "lxml",
    "pandas",
    "matplotlib",
    "seaborn",
    "scikit-learn",
    "jupyter",
]
```

Adicionamos `selenium` ou `playwright` apenas se a inspeção do HTML mostrar
que o conteúdo é JS-renderizado.

## Cronograma sugerido (1 semana)

| Dia | Atividade | Etapa |
|---|---|---|
| 1 (seg) | Setup do ambiente, inspecionar o site, entender o HTML | E1 |
| 2 (ter) | Scraper de marés (12 meses de 2025) | E1 |
| 3 (qua) | Scraper de ondas + salvar CSVs em `data/raw/` | E1 |
| 4 (qui) | EDA: limpeza, junção, visualizações | E2 |
| 5 (sex) | ML: label heurística, treino, avaliação | E3 |
| 6 (sáb) | Aplicação no ano + conclusão escrita + plot da árvore | E3 |
| 7 (dom) | Buffer, polimento, README final | — |

## Princípios e simplificações (YAGNI)

- Sem orquestrador (Airflow, Prefect) — `python src/scrape.py` resolve
- Sem banco de dados — CSVs bastam pro escopo
- Sem deep learning — apenas `scikit-learn` built-in
- Sem dashboard / app — gráficos no notebook + markdown final
- Código simples, comentado em português, focado em ensinar conceitos
- Sem testes automatizados formais — alunos do 1º período ainda não viram
  TDD; validação é por inspeção visual dos CSVs e gráficos

## Não-objetivos

- Não vamos modelar marés do ponto de vista físico/astronômico (já vem do
  site).
- Não vamos prever condições futuras a partir do modelo — o classificador só
  rotula condições conhecidas. "Quando voltar" sai da aplicação do modelo
  sobre o dataset disponível.
- Não vamos generalizar para outras praias — escopo é João Pessoa.
- Não vamos detectar swell ou tipos de onda — a heurística trabalha em cima
  de altura, período, vento e maré.
