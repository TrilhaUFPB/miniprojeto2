# Mini-Projeto 2 — Quando voltar a João Pessoa para surfar?

Felipe Duarte e Nicholas gostam de surfar, mas só vêm a João Pessoa em alguns
períodos do ano. A pergunta do projeto: **quando eles devem voltar para pegar
as melhores ondas?**

![Felipe Duarte e Nicholas surfando na orla de João Pessoa](assets/surfistas.jpg)

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
| [`beautifulsoup4`](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) | Navega no HTML e localiza os elementos com o dado |
| [`pandas`](https://pandas.pydata.org/docs/) | Tabelas, limpeza, junções, CSV |
| [`matplotlib`](https://matplotlib.org/) / [`seaborn`](https://seaborn.pydata.org/) | Gráficos |
| [`scikit-learn`](https://scikit-learn.org/stable/) | Split, treino, métricas, modelos |
| Jupyter | Os notebooks das Etapas 2 e 3 |

Tudo isso já está em `pyproject.toml`. Se quiser trocar por algo equivalente
(`httpx` no lugar de `requests`, `polars` no lugar de `pandas`, `plotly` nos
gráficos), pode — só justifique e adicione a dependência.

## Setup

### 1. Fazer um fork do repositório

Comece fazendo um **fork** deste repositório para a sua conta no GitHub:

1. Clique no botão **Fork** no canto superior direito desta página.
2. Clone o seu fork para a máquina:
   ```bash
   git clone https://github.com/[seu-usuario]/miniprojeto2.git
   cd miniprojeto2
   ```

Assim você terá uma cópia do projeto na sua conta, e conseguirá fazer push das
suas soluções.

### 2. Instalar dependências

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

> [!WARNING]
> Siga as etapas em ordem. A Etapa 2 precisa dos CSVs da Etapa 1, e a Etapa 3
> precisa do dataset processado da Etapa 2.

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

Por onde começar:

1. Abra a página no navegador e o DevTools (F12, ou Cmd+Opt+I no Mac).
2. Clique com o botão direito no número que você quer e escolha "Inspecionar".
   Olhe o `id` e as `class` do elemento e dos elementos que o contêm — é isso
   que você vai usar como seletor.
3. Baixe a página com `requests` e confirme que o dado está no HTML devolvido.

O resto do caminho é com você.

Uma preocupação a menos: esse site entrega tudo renderizado pelo servidor,
inclusive os meses anteriores da tábua de marés. `requests` + `BeautifulSoup`
dão conta das três fontes — **não é preciso Selenium** nem navegador
automatizado.

<details>
<summary><b>Dicas, se travar</b></summary>

- A tábua de marés mostra o mês atual por padrão. Para pedir outro mês, veja na
  aba **Network** do DevTools o que o navegador envia quando você troca o mês.
  É isso que permite baixar um ano inteiro.
- As páginas de onda e de vento têm o mesmo layout — uma função só resolve as
  duas.
- Antes de parsear, imprima `resp.status_code` e `len(resp.text)`. Metade dos
  bugs de scraping é a resposta não ser o que você imagina.

</details>

### Regras de convivência

Web scraping mexe com o servidor de outra pessoa. Não negociável:

- **Identifique-se** com um `User-Agent` real (já está no esqueleto).
- **Pause entre requisições** (1 a 2 segundos). Sem pausa, uma sequência de
  requests parece ataque.
- **Trabalhe no arquivo local.** Baixe uma vez, salve, e desenvolva o parse no
  HTML salvo — não rode o scraper em loop enquanto depura.
- **Leia o [`robots.txt`](https://tabuademares.com/robots.txt) do site.** Ele
  diz quais caminhos o servidor libera para acesso automatizado.

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
subindo ou descendo. Escolha, justifique no notebook, e diga onde a suposição
erra.

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

## Entregáveis

- `src/scrape.py` funcionando de ponta a ponta.
- `notebooks/eda.ipynb` com a limpeza, a junção e as conclusões.
- `notebooks/ml.ipynb` com a label definida, o modelo avaliado e o ranking de
  horários.
- A resposta para Felipe e Nicholas, em uma frase, na conclusão da Etapa 3.

Na correção eu vou ler o código: como vocês fizeram a coleta, como trataram os
dados, e se esse tratamento ficou bom o suficiente para o modelo prever bem. Se
não ficar, Felipe e Nicholas vão se frustrar e desistir da vida de surfistas.

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

**Vídeos**

[Playlist de web scraping com Python](https://www.youtube.com/watch?v=42sTntMEn6o&list=PLg3ZPsW_sghSkRacynznQeEs-vminyTQk)
— foi essa que eu assisti na minha época na Tail. Se quiserem, assistam: os
**4 primeiros vídeos** já cobrem tudo que este projeto precisa, o resto vai
além do necessário aqui.

E se preferirem ir direto ao ponto: uma boa conversa com o ChatGPT sobre como
funcionam o `requests` e o `BeautifulSoup` — e como pegar informação do HTML de
uma página — já resolve :)

**Documentação**

- [requests — Quickstart](https://requests.readthedocs.io/en/latest/user/quickstart/)
- [BeautifulSoup — searching the tree](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#searching-the-tree)
- [pandas — 10 minutes to pandas](https://pandas.pydata.org/docs/user_guide/10min.html)
- [pandas — merge, join, concatenate](https://pandas.pydata.org/docs/user_guide/merging.html)
- [scikit-learn — getting started](https://scikit-learn.org/stable/getting_started.html)
