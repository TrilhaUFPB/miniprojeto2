# Mini-Projeto 2 — Quando voltar a João Pessoa para surfar?

Felipe Duarte e Nicholas gostam de surfar, mas só vêm a João Pessoa em alguns
períodos do ano. A pergunta do projeto: **quando eles devem voltar para pegar
as melhores ondas?**

Os dados para responder isso existem e são públicos.
[tabuademares.com](https://tabuademares.com/br/paraiba/joao-pessoa) publica,
para João Pessoa, a tábua de marés com coeficiente e fase da lua, e a previsão
de altura de onda e de vento hora a hora. O que o site **não** publica é a
resposta: os rótulos que aparecem lá (`MUITO BOM`, `BOM`, `MAU`) são para
**pesca**, que valoriza mar calmo — quase o oposto do que um surfista procura.

Ou seja: o dado está lá, a resposta não. Construir a resposta é o projeto.

## O que você vai fazer

| Etapa | Tarefa | Entrega |
|---|---|---|
| 1 | Engenharia de dados — web scraping do site | CSVs em `data/raw/` |
| 2 | Ciência de dados — limpeza, junção e EDA | `data/processed/dataset.csv`, gráficos e conclusões em `notebooks/eda.ipynb` |
| 3 | Machine learning — classificar condições e ranquear horários | modelo avaliado e interpretado em `notebooks/ml.ipynb` |

Nada aqui está resolvido, e é de propósito. Os arquivos são esqueletos:
docstrings, assinaturas de função, seções e perguntas. As decisões — quais
seletores usar, como juntar tabelas de granularidade diferente, o que conta
como onda boa, qual modelo treinar — são suas, e é nelas que está o
aprendizado.

## Ferramentas

| Ferramenta | Para quê |
|---|---|
| [`uv`](https://docs.astral.sh/uv/) | Gerencia o ambiente virtual e as dependências |
| [`requests`](https://requests.readthedocs.io/) | Faz as requisições HTTP e baixa o HTML |
| [`beautifulsoup4`](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) + `lxml` | Navega no HTML e localiza os elementos com o dado |
| [`pandas`](https://pandas.pydata.org/docs/) | Tabelas, limpeza, junções, CSV |
| [`matplotlib`](https://matplotlib.org/) / [`seaborn`](https://seaborn.pydata.org/) | Gráficos |
| [`scikit-learn`](https://scikit-learn.org/stable/) | Split, treino, métricas, modelos |
| Jupyter | Os notebooks das Etapas 2 e 3 |

Tudo isso já está em `pyproject.toml`. Se quiser trocar por algo equivalente
(`httpx` no lugar de `requests`, `polars` no lugar de `pandas`, `plotly` nos
gráficos), pode — só justifique e adicione a dependência.

## Setup

Requer `uv` instalado e Python `>= 3.14`.

```bash
# instala as dependências e cria o .venv
uv sync

# Etapa 1
uv run python src/scrape.py

# Etapas 2 e 3 — abra o Jupyter de dentro de notebooks/
cd notebooks
uv run jupyter notebook
```

Os caminhos nos notebooks são relativos a `notebooks/` (`../data/raw`). Se você
abrir o Jupyter na raiz do repositório, vai tomar `FileNotFoundError`.

Rode as etapas em ordem: a 2 precisa dos CSVs da 1, a 3 precisa do dataset
processado da 2.

## Etapa 1 — Coleta (web scraping)

Fonte: <https://tabuademares.com/br/paraiba/joao-pessoa>

Três partes do site interessam:

1. **Tábua mensal de marés** (página principal) — cerca de 4 marés por dia, com
   horário, altura, coeficiente de maré e fase da lua.
2. **Previsão de ondas** (`/previsao/ondas`) — altura hora a hora, ~7 dias à
   frente.
3. **Previsão de vento** (`/previsao/vento`) — velocidade e direção hora a hora,
   ~7 dias à frente.

O esqueleto está em [`src/scrape.py`](src/scrape.py): as URLs, os headers, a
pausa entre requisições e as funções que você precisa preencher. Os seletores
não estão lá — descobri-los é o exercício.

Um caminho que funciona:

1. Abra a página no navegador e o DevTools (F12, ou Cmd+Opt+I no Mac).
2. Clique com o botão direito no número que você quer e escolha "Inspecionar".
   Olhe o `id` e as `class` do elemento e dos elementos que o contêm — é isso
   que você vai usar como seletor.
3. Baixe a página com `requests` e **confirme que o dado está no HTML
   devolvido**. Se não estiver, ele foi renderizado por JavaScript e você vai
   precisar olhar a aba Network.
4. Com `BeautifulSoup`, localize os elementos (`select`, `select_one`,
   `find_all`) e extraia o texto.
5. Normalize: vírgula decimal vira ponto, `HH:MM` vira hora, dia + mês viram
   uma data completa.
6. Monte um `DataFrame` e salve em `data/raw/`.

<details>
<summary><b>Dicas, se travar</b></summary>

- A tábua de marés mostra o mês atual por padrão. Para pedir outro mês, veja na
  aba **Network** do DevTools o que o navegador envia quando você troca o mês:
  o corpo da requisição carrega um campo de data. É isso que permite baixar um
  ano inteiro.
- As páginas de onda e de vento têm o mesmo layout — um bloco por dia, com uma
  linha por hora dentro. Uma função só resolve as duas.
- O coeficiente de maré e a fase da lua não estão no texto: estão no **nome da
  classe** do ícone. `elemento.get("class")` devolve a lista de classes.
- Antes de parsear, imprima `resp.status_code` e `len(resp.text)`. Metade dos
  bugs de scraping é a resposta não ser o que você imagina.
- Um CSV vazio é o erro mais silencioso que existe. Sempre imprima o número de
  linhas gravadas.

</details>

### Regras de convivência

Web scraping mexe com o servidor de outra pessoa. Não negociável:

- **Identifique-se** com um `User-Agent` real (já está no esqueleto).
- **Pause entre requisições** (1 a 2 segundos). Você vai fazer ~14 requests;
  sem pausa isso parece ataque.
- **Trabalhe em cima do arquivo local.** Baixe uma vez, salve, e desenvolva o
  parse no HTML/CSV salvo. Não rode o scraper em loop enquanto depura.
- **Leia o `robots.txt` do site.** Coletar para estudar é uma coisa; volume é
  outra.

### O que os CSVs precisam ter

O formato é seu, mas as etapas seguintes precisam de, no mínimo:

- **marés:** data, horário do evento, altura, e se é maré alta ou baixa;
- **ondas e vento:** data, hora, valor e direção.

Coeficiente de maré e fase da lua são opcionais — mas rendem análise na
Etapa 2.

## Etapa 2 — EDA

Roteiro em [`notebooks/eda.ipynb`](notebooks/eda.ipynb). Você vai carregar os
CSVs, limpar, explorar cada fonte, juntar tudo numa tabela horária e salvar em
`data/processed/dataset.csv`.

A parte difícil é a junção, e ela não tem resposta única: onda e vento são
leituras horárias, maré são ~4 eventos por dia (os instantes de máxima e
mínima). Levar a maré para uma grade horária exige uma decisão — interpolar
entre os eventos, repetir o último valor, ou guardar apenas se ela está
subindo ou descendo. Cada opção assume algo sobre a curva real da maré.
Escolha, justifique no notebook, e diga onde a suposição erra.

Um gráfico por pergunta, e cada gráfico com uma frase dizendo o que você leu
nele. Gráfico sem leitura não conta.

## Etapa 3 — Modelagem

Roteiro em [`notebooks/ml.ipynb`](notebooks/ml.ipynb).

Como o site rotula para pesca, **não existe label pronta**. Sua primeira tarefa
é escrever em código a regra que separa condição ruim, boa e ótima: quais
variáveis entram (altura da onda, vento, maré, direção), quais limiares, e de
onde vem cada número. Um chute informado é aceitável desde que declarado.

Depois disso é o fluxo padrão: features e alvo, split, treinar pelo menos dois
modelos de famílias diferentes, avaliar e **interpretar** — plotar a árvore,
olhar a importância das features, checar se o que o modelo aprendeu parece com
a sua regra.

Um ponto que costuma passar batido: o modelo aprende a copiar a sua
heurística, então ele é no máximo tão bom quanto ela. Acurácia de 0,99 aqui
significa que o modelo decorou o seu `if`, não que você previu o mar. Dizer
isso na conclusão vale mais do que a acurácia.

## Limites dos dados (isso faz parte da avaliação)

1. O site publica onda e vento só para os próximos ~7 dias. **Não dá para
   eleger o melhor mês do ano** com isso. A tábua de marés cobre o ano inteiro
   e permite discutir sazonalidade de maré e coeficiente — não de swell.
2. Não há período de swell nem direção relativa a uma praia específica, que é o
   que um surfista de verdade olha.
3. Sem rótulos de surfista real, o teto do modelo é a heurística que você
   inventou.
4. Uma janela de ~7 dias dá poucas linhas. Métrica alta em pouco dado quase
   sempre significa outra coisa.

Uma entrega boa responde **qual a melhor janela dentro da previsão atual** e
explica por que a versão anual da pergunta não é respondível com esses dados —
ou propõe como seria (por exemplo, rodar o scraper todo dia por alguns meses e
acumular histórico).

## Entregáveis

- `src/scrape.py` funcionando de ponta a ponta.
- `notebooks/eda.ipynb` com a limpeza, a junção justificada, os gráficos e as
  conclusões escritas.
- `notebooks/ml.ipynb` com a label definida e documentada, os modelos
  avaliados, a interpretação e o ranking de horários.
- A resposta para Felipe e Nicholas, em uma frase, na conclusão da Etapa 3.

O que se avalia: o scraper aguenta uma segunda execução sem quebrar; as
decisões de limpeza e junção estão justificadas; os gráficos respondem
perguntas em vez de enfeitar; a label é explícita e defensável; a avaliação do
modelo é honesta; e os limites dos dados aparecem na conclusão em vez de serem
varridos para debaixo do tapete.

## Estrutura

```
miniprojeto2/
├── src/scrape.py          # Etapa 1 — esqueleto
├── notebooks/
│   ├── eda.ipynb          # Etapa 2 — roteiro
│   └── ml.ipynb           # Etapa 3 — roteiro
├── data/                  # gerado ao rodar (fora do git)
│   ├── raw/
│   └── processed/
├── pyproject.toml
└── README.md
```

## Referências

**Vídeos sobre web scraping**

<!-- TODO: adicionar os links dos vídeos de referência -->

**Documentação**

- [requests — Quickstart](https://requests.readthedocs.io/en/latest/user/quickstart/)
- [BeautifulSoup — searching the tree](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#searching-the-tree)
- [Seletores CSS (MDN)](https://developer.mozilla.org/pt-BR/docs/Web/CSS/CSS_selectors)
- [pandas — 10 minutes to pandas](https://pandas.pydata.org/docs/user_guide/10min.html)
- [pandas — merge, join, concatenate](https://pandas.pydata.org/docs/user_guide/merging.html)
- [scikit-learn — getting started](https://scikit-learn.org/stable/getting_started.html)
- [uv — guia de projetos](https://docs.astral.sh/uv/guides/projects/)
