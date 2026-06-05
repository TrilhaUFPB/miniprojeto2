"""
Scraper da Tábua de Marés de João Pessoa.

Etapa 1 do mini-projeto: Engenharia de Dados.

Coleta dois conjuntos de dados a partir de https://tabuademares.com:

1. **Tábua de marés** mensal de janeiro a dezembro de 2025
   (4 marés por dia, com altura, horário e coeficiente).
2. **Previsão de ondas e vento** horária para os próximos ~7 dias
   (altura de onda, direção, velocidade do vento).

Os arquivos são salvos em ``data/raw/``:

- ``data/raw/mares_2025.csv``
- ``data/raw/ondas.csv``
- ``data/raw/vento.csv``

Como rodar::

    uv run python src/scrape.py

Estrutura:

- ``baixar_mares_mes(ano, mes)`` — POST para a página principal.
- ``baixar_previsao_horaria(tipo)`` — GET para ``/previsao/ondas`` ou
  ``/previsao/vento``.
- ``main()`` — orquestra tudo, salva CSVs.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag

# -----------------------------------------------------------------------------
# Configuração
# -----------------------------------------------------------------------------

URL_BASE = "https://tabuademares.com/br/paraiba/joao-pessoa"
URL_PREVISAO_ONDAS = f"{URL_BASE}/previsao/ondas"
URL_PREVISAO_VENTO = f"{URL_BASE}/previsao/vento"

# User-Agent realista. Sites costumam bloquear UA do tipo "python-requests".
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Pausa entre requests para não sobrecarregar o servidor.
PAUSA_ENTRE_REQUESTS_SEG = 1.5

# Onde os CSVs vão parar.
DIR_DADOS_BRUTOS = Path(__file__).resolve().parent.parent / "data" / "raw"

# Dicionário de meses em português -> número (usado nos cabeçalhos da página).
MESES_PT = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "ABRIL": 4,
    "MAIO": 5, "JUNHO": 6, "JULHO": 7, "AGOSTO": 8,
    "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12,
}
ABREV_MES = {v: k[:3] for k, v in MESES_PT.items()}  # 1 -> "JAN", ...


# -----------------------------------------------------------------------------
# Camada HTTP — uma sessão reutilizável
# -----------------------------------------------------------------------------

def criar_sessao() -> requests.Session:
    """Cria uma sessão do requests com User-Agent já configurado.

    Reutilizar a sessão entre requests é mais rápido (mantém conexão TCP) e
    permite definir headers padrão uma vez só.
    """
    sessao = requests.Session()
    sessao.headers.update({"User-Agent": USER_AGENT})
    return sessao


def buscar_html(sessao: requests.Session, url: str, *, dados_post: dict | None = None) -> str:
    """Faz um GET ou POST e devolve o HTML em string.

    Se ``dados_post`` for fornecido, faz POST; caso contrário, GET.
    Levanta exceção se a resposta não for 200.
    """
    if dados_post is None:
        resp = sessao.get(url, timeout=30)
    else:
        resp = sessao.post(url, data=dados_post, timeout=30)
    resp.raise_for_status()
    return resp.text


# -----------------------------------------------------------------------------
# Parser — tabela de marés mensal
# -----------------------------------------------------------------------------

@dataclass
class EventoMare:
    """Uma maré (alta ou baixa) num dia específico.

    O dataset final tem uma linha por evento — em geral 4 por dia.
    """
    data: date
    horario: str  # formato "HH:MM"
    altura_m: float
    tipo: str  # "alta" ou "baixa"
    coeficiente: int | None
    dia_ciclo_lunar: int | None  # 1..~30, dia dentro do ciclo lunar


def _to_float_pt(texto: str) -> float:
    """Converte string com vírgula decimal em float. Ex: '2,1' -> 2.1."""
    return float(texto.strip().replace(",", "."))


def _to_int_safe(texto: str) -> int | None:
    """Tenta converter para int, devolve None se falhar."""
    try:
        return int(texto.strip())
    except (ValueError, AttributeError):
        return None


def _extrair_fase_lunar(td: Tag) -> int | None:
    """Lê o dia do ciclo lunar (1 a 30) a partir das classes do ícone.

    O HTML usa um span do tipo
    ``<span class="icon-text-color-print icon-hs7 icon-lunar_ajuste">``.
    A classe ``icon-hsN`` indica o dia do ciclo (1=lua nova, ~15=cheia, etc).
    Devolvemos esse N como inteiro — alunos podem mapear para nomes textuais
    na EDA se quiserem.
    """
    span = td.select_one('span[class*="icon-hs"]')
    if span is None:
        return None
    for classe in span.get("class", []):
        match = re.fullmatch(r"icon-hs(\d{1,2})", classe)
        if match:
            return int(match.group(1))
    return None


def _parse_linha_mes(linha: Tag, ano: int, mes: int) -> list[EventoMare]:
    """Converte uma <tr> da tabela mensal em lista de eventos.

    Cada linha de dados tem 4 <td class="tabla_mareas_marea"> — uma para cada
    maré do dia. Algumas linhas podem ter menos de 4 marés (raro, mas pode
    acontecer no fim do mês).
    """
    td_dia = linha.select_one(".tabla_mareas_dia_numero")
    if td_dia is None:
        return []

    dia = int(td_dia.get_text(strip=True))
    data_dia = date(ano, mes, dia)

    coef_td = linha.select_one(".tabla_mareas_coeficiente_numero")
    coeficiente: int | None = None
    if coef_td is not None:
        # Pegar só o primeiro fragmento de texto: "81 alto" → "81".
        primeiro = next(coef_td.stripped_strings, None)
        coeficiente = _to_int_safe(primeiro) if primeiro else None

    fase = _extrair_fase_lunar(linha)

    eventos: list[EventoMare] = []
    for td_mare in linha.select("td.tabla_mareas_marea"):
        hora_div = td_mare.select_one(".tabla_mareas_marea_hora")
        altura_span = td_mare.select_one(".tabla_mareas_marea_altura_numero")
        if hora_div is None or altura_span is None:
            continue

        # O tipo é distinguido por uma sub-div com classe ``_pleamar`` ou
        # ``_bajamar``. Nem todos os <td> têm a div explícita, então caímos
        # de volta na classe da hora (``tabla_mareas_hora_bajamar``).
        if td_mare.select_one(".tabla_mareas_marea_pleamar"):
            tipo = "alta"
        elif td_mare.select_one(".tabla_mareas_marea_bajamar"):
            tipo = "baixa"
        elif "tabla_mareas_hora_bajamar" in (hora_div.get("class") or []):
            tipo = "baixa"
        else:
            tipo = "alta"

        eventos.append(EventoMare(
            data=data_dia,
            horario=hora_div.get_text(strip=True),
            altura_m=_to_float_pt(altura_span.get_text(strip=True)),
            tipo=tipo,
            coeficiente=coeficiente,
            dia_ciclo_lunar=fase,
        ))

    return eventos


def parsear_tabela_mares(html: str, ano_esperado: int, mes_esperado: int) -> list[EventoMare]:
    """Extrai todos os eventos de maré da tabela mensal.

    A página só renderiza um mês por vez. Antes de parsear, validamos que o
    mês retornado bate com o pedido — a página as vezes ignora a data se ela
    for futura demais e cai num default.
    """
    soup = BeautifulSoup(html, "lxml")

    # Validar o mês exibido pela página.
    titulo = soup.select_one(
        "#_tabela_mares ~ .titulo_seccion_fecha .titulo_seccion_fecha_texto"
    )
    if titulo is not None:
        texto = titulo.get_text(" ", strip=True).upper()
        match_mes = re.search(r"([A-ZÇ]+)\s+DE\s+(\d{4})", texto)
        if match_mes:
            mes_real = MESES_PT.get(match_mes.group(1))
            ano_real = int(match_mes.group(2))
            if mes_real != mes_esperado or ano_real != ano_esperado:
                raise ValueError(
                    f"Página retornou {match_mes.group(0)}, "
                    f"esperado {ABREV_MES[mes_esperado]} {ano_esperado}"
                )

    tabela = soup.select_one("table#tabla_mareas")
    if tabela is None:
        raise ValueError("Tabela #tabla_mareas não encontrada no HTML")

    # As 2 primeiras <tr> são cabeçalho (DIA / FASE / 1ª MARÉ ...).
    linhas = tabela.select("tr.tabla_mareas_fila")[2:]

    todos: list[EventoMare] = []
    for linha in linhas:
        todos.extend(_parse_linha_mes(linha, ano_esperado, mes_esperado))
    return todos


# -----------------------------------------------------------------------------
# Parser — previsão horária (ondas e vento)
# -----------------------------------------------------------------------------

@dataclass
class LeituraHoraria:
    """Uma linha horária de previsão (onda OU vento)."""
    data: date
    hora: int            # 0..23
    direcao: str         # ex: "ESE", "SSW"
    valor: float         # altura em m (ondas) OU velocidade em km/h (vento)
    unidade: str         # "m" ou "km/h"


def _parse_data_ficha(ficha: Tag, ano_referencia: int) -> date | None:
    """Lê o header de uma ficha (ex: ``05 JUN``) e devolve a data."""
    span_dia = ficha.select_one(".f_circulo .dia")
    span_mes = ficha.select_one(".f_circulo .mes")
    if span_dia is None or span_mes is None:
        return None
    try:
        dia = int(span_dia.get_text(strip=True))
    except ValueError:
        return None
    abrev = span_mes.get_text(strip=True).upper()
    # Achar o número do mês a partir da abreviação (JAN..DEZ).
    mes = next((n for n, a in ABREV_MES.items() if a == abrev), None)
    if mes is None:
        return None
    return date(ano_referencia, mes, dia)


def _parse_ficha_horaria(ficha: Tag, ano_referencia: int) -> list[LeituraHoraria]:
    """Extrai todas as linhas horárias de uma ficha (1 dia)."""
    data_dia = _parse_data_ficha(ficha, ano_referencia)
    if data_dia is None:
        return []

    leituras: list[LeituraHoraria] = []
    for linha in ficha.select(".f_temp_horas"):
        # Estrutura: <div f_temp_hora>HORA</div>
        #            <div f_temp_hora>DIRECAO</div>
        #            <div f_temp_graf2> ... <span altura_numero>VALOR</span>
        #                                   <span prevision_unidad>m|km/h</span>
        celulas_texto = linha.select(".f_temp_hora")
        if len(celulas_texto) < 2:
            continue

        # As horas vêm como "0:00", "1:00"... pegamos só o número antes do ":".
        try:
            hora = int(celulas_texto[0].get_text(strip=True).split(":")[0])
        except ValueError:
            continue

        direcao = celulas_texto[1].get_text(strip=True)

        valor_span = linha.select_one(".tabla_mareas_marea_altura_numero")
        unidade_span = linha.select_one(".prevision_unidad")
        if valor_span is not None:
            # Caminho das ondas: <span altura_numero>1,3</span><span unidade>m</span>
            valor = _to_float_pt(valor_span.get_text(strip=True))
            unidade = unidade_span.get_text(strip=True) if unidade_span else ""
        else:
            # Caminho do vento: o texto do .grafico_temp_barra_relleno é "17 km/h".
            relleno = linha.select_one(".grafico_temp_barra_relleno")
            if relleno is None:
                continue
            texto = relleno.get_text(" ", strip=True)
            match = re.match(r"([\d,\.]+)\s*(.*)", texto)
            if not match:
                continue
            valor = _to_float_pt(match.group(1))
            unidade = match.group(2).strip()

        leituras.append(LeituraHoraria(
            data=data_dia,
            hora=hora,
            direcao=direcao,
            valor=valor,
            unidade=unidade,
        ))
    return leituras


def parsear_previsao_horaria(html: str, ano_referencia: int) -> list[LeituraHoraria]:
    """Extrai todas as leituras de todas as fichas (todos os dias) da página."""
    soup = BeautifulSoup(html, "lxml")
    fichas = soup.select("div.ficha")

    leituras: list[LeituraHoraria] = []
    for ficha in fichas:
        leituras.extend(_parse_ficha_horaria(ficha, ano_referencia))
    return leituras


# -----------------------------------------------------------------------------
# Funções de alto nível — uma por fonte
# -----------------------------------------------------------------------------

def baixar_mares_mes(sessao: requests.Session, ano: int, mes: int) -> list[EventoMare]:
    """Baixa e parseia a tabela mensal de marés."""
    fecha = f"{ano:04d}-{mes:02d}-01"
    print(f"  → POST mares mês {fecha}")
    html = buscar_html(sessao, URL_BASE, dados_post={"fecha": fecha})
    return parsear_tabela_mares(html, ano, mes)


def baixar_mares_ano(sessao: requests.Session, ano: int) -> pd.DataFrame:
    """Baixa todos os 12 meses do ano e devolve um DataFrame único."""
    todos: list[EventoMare] = []
    for mes in range(1, 13):
        eventos = baixar_mares_mes(sessao, ano, mes)
        print(f"    {len(eventos)} eventos em {ABREV_MES[mes]}/{ano}")
        todos.extend(eventos)
        time.sleep(PAUSA_ENTRE_REQUESTS_SEG)

    return pd.DataFrame([e.__dict__ for e in todos])


def baixar_previsao(sessao: requests.Session, url: str, ano_referencia: int) -> pd.DataFrame:
    """Baixa a previsão horária de uma página de previsão (ondas OU vento)."""
    print(f"  → GET {url}")
    html = buscar_html(sessao, url)
    leituras = parsear_previsao_horaria(html, ano_referencia)
    print(f"    {len(leituras)} leituras horárias")
    return pd.DataFrame([leitura.__dict__ for leitura in leituras])


# -----------------------------------------------------------------------------
# Orquestrador
# -----------------------------------------------------------------------------

def main(ano: int = 2025) -> None:
    """Roda o pipeline inteiro e salva os CSVs."""
    DIR_DADOS_BRUTOS.mkdir(parents=True, exist_ok=True)
    sessao = criar_sessao()

    print(f"\n📅 Baixando marés de {ano}...")
    df_mares = baixar_mares_ano(sessao, ano)
    caminho_mares = DIR_DADOS_BRUTOS / f"mares_{ano}.csv"
    df_mares.to_csv(caminho_mares, index=False)
    print(f"✓ {len(df_mares)} eventos de maré → {caminho_mares}")

    # Para a previsão usamos o ano corrente (a página mostra os próximos
    # ~7 dias a partir de hoje). Se rodarmos o scraper em 2026, queremos
    # que as datas das fichas tenham 2026, não ``ano`` de marés.
    from datetime import datetime
    ano_previsao = datetime.now().year

    print(f"\n🌊 Baixando previsão de ondas (ref. {ano_previsao})...")
    df_ondas = baixar_previsao(sessao, URL_PREVISAO_ONDAS, ano_previsao)
    caminho_ondas = DIR_DADOS_BRUTOS / "ondas.csv"
    df_ondas.to_csv(caminho_ondas, index=False)
    print(f"✓ {len(df_ondas)} leituras de onda → {caminho_ondas}")

    time.sleep(PAUSA_ENTRE_REQUESTS_SEG)

    print(f"\n💨 Baixando previsão de vento (ref. {ano_previsao})...")
    df_vento = baixar_previsao(sessao, URL_PREVISAO_VENTO, ano_previsao)
    caminho_vento = DIR_DADOS_BRUTOS / "vento.csv"
    df_vento.to_csv(caminho_vento, index=False)
    print(f"✓ {len(df_vento)} leituras de vento → {caminho_vento}")

    print("\n🏁 Pronto! Os CSVs estão em data/raw/")


if __name__ == "__main__":
    main()
