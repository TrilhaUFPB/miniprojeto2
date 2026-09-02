# Mini-Projeto 2 — o que o tutorial cobre

Companheiro do [README](../README.md). Aqui estão os schemas da tabela
juntada, a heurística da label e as limitações que o exercício pede
para deixar explícitas.

## A pergunta

Felipe Duarte e Nicholas, da organização, gostam de surfar mas só vêm a
João Pessoa em alguns períodos do ano. **Quando devem voltar para
aproveitar as melhores ondas?**

O site não classifica condições para surf. Os rótulos visíveis
(`MUITO BOM` / `BOM` / `MAU`) são para **pesca**, que valoriza mar
calmo — o oposto do que um surfista quer. Por isso a Etapa 3 inventa
uma label `surfavel` com regras simples e treina classificadores para
reproduzi-la.

## Escopo

- **Local:** João Pessoa, PB
- **Marés históricas:** ano de 2025 (contexto na EDA)
- **Onda e vento:** janela de previsão do site (~7 dias)
- **Marés da junção:** mês corrente (`mares_previsao.csv`), para
  interpolar a altura da maré na mesma janela da previsão
- **Stack:** Python 3.14, `uv`, `pandas`, `matplotlib` / `seaborn`,
  `scikit-learn`, Jupyter

## Fluxo

```
Etapa 1  src/scrape.py
         mares 2025 + mares do mês + ondas + vento
              ↓  data/raw/*.csv
Etapa 2  notebooks/eda.ipynb
         limpa, explora, junta hora a hora
              ↓  data/processed/dataset.csv
Etapa 3  notebooks/ml.ipynb
         label heurística → 3 classificadores → ranking
              ↓  data/processed/dataset_rotulado.csv
```

## Schema — `data/processed/dataset.csv`

Uma linha por hora, só onde onda e vento se sobrepõem.

| categoria | colunas |
|---|---|
| Tempo | `datahora`, `data`, `hora`, `dia_semana`, `periodo_dia` |
| Ondas | `altura_onda_m`, `direcao_onda` |
| Vento | `vento_kmh`, `direcao_vento` |
| Maré | `altura_mare_m` (interpolada), `mare_subindo`, `coeficiente` |

A interpolação da maré liga os eventos alta/baixa por uma reta. A curva
real é senoidal; a reta basta para o exercício.

`dia_semana` vem de `pandas` em inglês (`Monday`, `Tuesday`, …).
`periodo_dia` é `madrugada` / `manha` / `tarde` / `noite`.

## Label `surfavel`

Regras usadas no notebook (limiares comentados lá):

| classe | quando |
|---|---|
| `RUIM` | vento ≥ 22 km/h **ou** altura da onda < 0,7 m |
| `ÓTIMO` | altura ≥ 1,0 m **e** vento < 18 km/h **e** maré subindo |
| `BOM` | o restante |

A lógica: vento forte na costa “mata” o swell; onda pequena não quebra
bem; maré subindo costuma deixar a onda mais formada nas praias da
região. São chutes informados, não medições de surfista.

O classificador **aprende a copiar essa regra**. Ele é tão bom quanto
ela — e isso faz parte do aprendizado.

## O que cada etapa ensina

**Etapa 1.** HTTP, parse de HTML, DOM, pausa entre requests, User-Agent,
persistir CSV.

**Etapa 2.** `pandas` (`head`, tipos, `merge`, `datetime`), limpeza,
interpolação simples, `matplotlib` / `seaborn`, ler um gráfico.

**Etapa 3.** Feature → label → split → treino → métricas, comparar
modelos, árvore plotada, importância de features, dizer o que o modelo
**não** responde.

## Limitações (vale deixar no notebook)

1. O site só publica ~7 dias de onda e vento. Não dá para eleger o
   melhor mês do ano sem coletar histórico ao longo do tempo.
2. Não há período de swell nem direção relativa a uma praia específica.
3. Sem labels reais de surfista, o teto do modelo é a heurística.
4. ~168 linhas é pouco. Accuracy alta aqui quase sempre significa “o
   modelo decorou a regra”, não “previmos o mar”.

A resposta para Felipe e Nicholas é o ranking da **janela de previsão
atual**, não um calendário anual.
