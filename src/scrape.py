"""
Etapa 1 - Web scraping de tabuademares.com/br/paraiba/joao-pessoa.

Coleta:
- Tábua de marés mensal de jan a dez de 2025 (4 mares/dia).
- Previsao horaria de altura de onda (~6 dias).
- Previsao horaria de velocidade do vento (~7 dias).

Salva tres CSVs em data/raw/. Rodar com: uv run python src/scrape.py
"""

import re
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL_BASE = "https://tabuademares.com/br/paraiba/joao-pessoa"
URL_ONDAS = f"{URL_BASE}/previsao/ondas"
URL_VENTO = f"{URL_BASE}/previsao/vento"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
PAUSA = 1.5
DIR_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

ABREV_MES = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
    7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ",
}


def parsear_mares(html: str, ano: int, mes: int) -> list[dict]:
    """Le a <table id=tabla_mareas> e devolve uma linha por evento de mare."""
    soup = BeautifulSoup(html, "lxml")
    tabela = soup.select_one("table#tabla_mareas")
    if tabela is None:
        raise ValueError("tabela #tabla_mareas nao encontrada")

    eventos = []
    # As 2 primeiras <tr> sao cabecalho.
    for tr in tabela.select("tr.tabla_mareas_fila")[2:]:
        td_dia = tr.select_one(".tabla_mareas_dia_numero")
        if td_dia is None:
            continue
        dia = int(td_dia.get_text(strip=True))

        coef = None
        td_coef = tr.select_one(".tabla_mareas_coeficiente_numero")
        if td_coef is not None:
            primeiro = next(td_coef.stripped_strings, "")
            coef = int(primeiro) if primeiro.isdigit() else None

        # Fase lunar: classe icon-hsN no span do icone (1=lua nova ... ~30).
        ciclo_lunar = None
        sp = tr.select_one('span[class*="icon-hs"]')
        if sp is not None:
            for c in sp.get("class", []):
                m = re.fullmatch(r"icon-hs(\d{1,2})", c)
                if m:
                    ciclo_lunar = int(m.group(1))
                    break

        for td in tr.select("td.tabla_mareas_marea"):
            hora_div = td.select_one(".tabla_mareas_marea_hora")
            altura_span = td.select_one(".tabla_mareas_marea_altura_numero")
            if hora_div is None or altura_span is None:
                continue

            if td.select_one(".tabla_mareas_marea_pleamar"):
                tipo = "alta"
            elif td.select_one(".tabla_mareas_marea_bajamar"):
                tipo = "baixa"
            elif "tabla_mareas_hora_bajamar" in (hora_div.get("class") or []):
                tipo = "baixa"
            else:
                tipo = "alta"

            eventos.append({
                "data": date(ano, mes, dia),
                "horario": hora_div.get_text(strip=True),
                "altura_m": float(altura_span.get_text(strip=True).replace(",", ".")),
                "tipo": tipo,
                "coeficiente": coef,
                "dia_ciclo_lunar": ciclo_lunar,
            })
    return eventos


def parsear_previsao(html: str, ano: int) -> list[dict]:
    """Le as <div class=ficha> (uma por dia) e devolve linhas horarias."""
    soup = BeautifulSoup(html, "lxml")
    leituras = []

    for ficha in soup.select("div.ficha"):
        sp_dia = ficha.select_one(".f_circulo .dia")
        sp_mes = ficha.select_one(".f_circulo .mes")
        if sp_dia is None or sp_mes is None:
            continue
        dia = int(sp_dia.get_text(strip=True))
        abrev = sp_mes.get_text(strip=True).upper()
        mes = next((n for n, a in ABREV_MES.items() if a == abrev), None)
        if mes is None:
            continue
        data_dia = date(ano, mes, dia)

        for linha in ficha.select(".f_temp_horas"):
            celulas = linha.select(".f_temp_hora")
            if len(celulas) < 2:
                continue
            try:
                hora = int(celulas[0].get_text(strip=True).split(":")[0])
            except ValueError:
                continue
            direcao = celulas[1].get_text(strip=True)

            # Ondas: <span altura_numero>1,3</span><span unidade>m</span>
            # Vento: texto direto "17 km/h" no .grafico_temp_barra_relleno
            valor_span = linha.select_one(".tabla_mareas_marea_altura_numero")
            if valor_span is not None:
                valor = float(valor_span.get_text(strip=True).replace(",", "."))
                unidade_span = linha.select_one(".prevision_unidad")
                unidade = unidade_span.get_text(strip=True) if unidade_span else ""
            else:
                relleno = linha.select_one(".grafico_temp_barra_relleno")
                if relleno is None:
                    continue
                m = re.match(r"([\d,.]+)\s*(.*)", relleno.get_text(" ", strip=True))
                if not m:
                    continue
                valor = float(m.group(1).replace(",", "."))
                unidade = m.group(2).strip()

            leituras.append({
                "data": data_dia,
                "hora": hora,
                "direcao": direcao,
                "valor": valor,
                "unidade": unidade,
            })
    return leituras


def baixar_mes_de_mares(ano: int, mes: int) -> list[dict]:
    """Faz POST para a pagina principal e parseia a tabela mensal."""
    fecha = f"{ano:04d}-{mes:02d}-01"
    print(f"  POST {fecha}")
    resp = requests.post(URL_BASE, headers=HEADERS, data={"fecha": fecha}, timeout=30)
    resp.raise_for_status()
    return parsear_mares(resp.text, ano, mes)


def main(ano: int = 2025) -> None:
    DIR_RAW.mkdir(parents=True, exist_ok=True)

    print(f"Baixando mares de {ano}...")
    eventos = []
    for mes in range(1, 13):
        eventos_mes = baixar_mes_de_mares(ano, mes)
        print(f"    {len(eventos_mes)} eventos em {ABREV_MES[mes]}/{ano}")
        eventos.extend(eventos_mes)
        time.sleep(PAUSA)
    df_mares = pd.DataFrame(eventos)
    caminho = DIR_RAW / f"mares_{ano}.csv"
    df_mares.to_csv(caminho, index=False)
    print(f"  -> {len(df_mares)} linhas em {caminho}")

    # Para juntar com ondas/vento (que cobrem os proximos ~7 dias) precisamos
    # tambem das mares do mes atual. Baixamos esse mes em um CSV separado.
    hoje = datetime.now()
    print(f"\nBaixando mares de {ABREV_MES[hoje.month]}/{hoje.year} (para juncao)...")
    df_mes_atual = pd.DataFrame(baixar_mes_de_mares(hoje.year, hoje.month))
    caminho = DIR_RAW / "mares_previsao.csv"
    df_mes_atual.to_csv(caminho, index=False)
    print(f"  -> {len(df_mes_atual)} linhas em {caminho}")

    # Previsao usa o ano atual (sao os proximos ~7 dias a partir de hoje).
    ano_prev = hoje.year

    print(f"\nBaixando previsao de ondas (ref. {ano_prev})...")
    resp = requests.get(URL_ONDAS, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    df_ondas = pd.DataFrame(parsear_previsao(resp.text, ano_prev))
    caminho = DIR_RAW / "ondas.csv"
    df_ondas.to_csv(caminho, index=False)
    print(f"  -> {len(df_ondas)} linhas em {caminho}")

    time.sleep(PAUSA)

    print(f"\nBaixando previsao de vento (ref. {ano_prev})...")
    resp = requests.get(URL_VENTO, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    df_vento = pd.DataFrame(parsear_previsao(resp.text, ano_prev))
    caminho = DIR_RAW / "vento.csv"
    df_vento.to_csv(caminho, index=False)
    print(f"  -> {len(df_vento)} linhas em {caminho}")

    print("\nPronto. CSVs em data/raw/.")


if __name__ == "__main__":
    main()
