"""
Coleta de tweets sobre candidatos à presidência 2026 via twikit.

Etapa 1 (engenharia de dados) do mini-projeto 2 — Termômetro Eleitoral.

Lê config.yaml + .env, autentica no X, busca tweets por candidato e salva
um CSV padronizado em data/raw/tweets.csv pro notebook de análise consumir.

Uso:
    cp .env.example .env       # preencher credenciais
    python src/collect.py      # roda a coleta inteira
"""

from __future__ import annotations

import asyncio
import csv
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv
from twikit import Client
from twikit.errors import TooManyRequests, TwitterException

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"

# Schema fixo do CSV de saída — contrato com o notebook de EDA.
CSV_FIELDS = [
    "tweet_id",
    "candidate",
    "query_matched",
    "text",
    "created_at",
    "lang",
    "likes",
    "retweets",
    "replies",
    "author_id",
]

# twikit limita cada chamada de search_tweet a 20 resultados.
PAGE_SIZE = 20

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("collect")


@dataclass
class Candidate:
    name: str
    party: str
    handle: str
    aliases: list[str]


@dataclass
class CollectionConfig:
    tweets_per_candidate: int
    language: str
    product: str
    since: str | None
    rate_limit_sleep_seconds: float
    output_csv: Path
    cookies_file: Path


def load_config() -> tuple[CollectionConfig, list[Candidate]]:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    c = raw["collection"]
    cfg = CollectionConfig(
        tweets_per_candidate=int(c["tweets_per_candidate"]),
        language=c["language"],
        product=c.get("product", "Latest"),
        since=str(c["since"]) if c.get("since") else None,
        rate_limit_sleep_seconds=float(c.get("rate_limit_sleep_seconds", 5)),
        output_csv=ROOT / c["output_csv"],
        cookies_file=ROOT / c["cookies_file"],
    )
    candidates = [
        Candidate(
            name=item["name"],
            party=item["party"],
            handle=item["handle"],
            aliases=list(item.get("aliases", [])),
        )
        for item in raw["candidates"]
    ]
    return cfg, candidates


def build_query(candidate: Candidate, cfg: CollectionConfig) -> str:
    """
    Monta a query enviada ao X. Operadores são forwarded direto pro endpoint
    SearchTimeline, então funcionam: lang:, -is:retweet, since:, OR, aspas.
    """
    terms = [f"@{candidate.handle}"] + [f'"{a}"' for a in candidate.aliases]
    or_group = " OR ".join(terms)
    parts = [f"({or_group})", f"lang:{cfg.language}", "-is:retweet"]
    if cfg.since:
        parts.append(f"since:{cfg.since}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Wrappers async com retry em rate limit
# ---------------------------------------------------------------------------

async def _sleep_until_reset(e: TooManyRequests) -> None:
    reset = e.rate_limit_reset or (int(time.time()) + 15 * 60)
    wait = max(5, reset - int(time.time()) + 5)
    log.warning("rate limit atingido; dormindo %ss até reset", wait)
    await asyncio.sleep(wait)


async def _search_with_retry(client: Client, query: str, product: str):
    while True:
        try:
            return await client.search_tweet(query, product, count=PAGE_SIZE)
        except TooManyRequests as e:
            await _sleep_until_reset(e)


async def _next_with_retry(page):
    while True:
        try:
            return await page.next()
        except TooManyRequests as e:
            await _sleep_until_reset(e)


# ---------------------------------------------------------------------------
# Extração e classificação por alias
# ---------------------------------------------------------------------------

def _matched_term(tweet_text: str, candidate: Candidate) -> str:
    """
    Identifica qual termo da query casou no texto. Útil pro CSV
    (rastreabilidade) e pra EDA. Fallback = handle.
    """
    lowered = tweet_text.lower()
    if f"@{candidate.handle.lower()}" in lowered:
        return f"@{candidate.handle}"
    for alias in candidate.aliases:
        if alias.lower() in lowered:
            return alias
    return f"@{candidate.handle}"


def _tweet_to_row(tweet, candidate: Candidate) -> dict:
    return {
        "tweet_id": tweet.id,
        "candidate": candidate.name,
        "query_matched": _matched_term(tweet.full_text or tweet.text or "", candidate),
        # full_text cobre tweets longos (note_tweet); o text comum trunca.
        "text": (tweet.full_text or tweet.text or "").replace("\n", " ").strip(),
        "created_at": tweet.created_at_datetime.isoformat() if tweet.created_at_datetime else "",
        "lang": tweet.lang or "",
        "likes": tweet.favorite_count or 0,
        "retweets": tweet.retweet_count or 0,
        "replies": tweet.reply_count or 0,
        "author_id": tweet.user.id if tweet.user else "",
    }


# ---------------------------------------------------------------------------
# Coleta por candidato
# ---------------------------------------------------------------------------

async def collect_candidate(
    client: Client, candidate: Candidate, cfg: CollectionConfig
) -> list[dict]:
    query = build_query(candidate, cfg)
    log.info("⮕ %s — query: %s", candidate.name, query)

    rows: list[dict] = []
    seen_ids: set[str] = set()

    page = await _search_with_retry(client, query, cfg.product)

    while page is not None and len(rows) < cfg.tweets_per_candidate:
        if len(page) == 0:
            log.info("   página vazia — fim dos resultados")
            break

        for tweet in page:
            if tweet.id in seen_ids:
                continue
            seen_ids.add(tweet.id)
            rows.append(_tweet_to_row(tweet, candidate))
            if len(rows) >= cfg.tweets_per_candidate:
                break

        log.info("   coletados %d/%d", len(rows), cfg.tweets_per_candidate)

        if len(rows) >= cfg.tweets_per_candidate:
            break

        await asyncio.sleep(cfg.rate_limit_sleep_seconds)
        next_page = await _next_with_retry(page)
        # Result.next() retorna Result vazio quando esgota.
        page = next_page if len(next_page) > 0 else None

    log.info("✓ %s — total: %d tweets", candidate.name, len(rows))
    return rows


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------

def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    log.info("CSV salvo em %s (%d linhas)", path, len(rows))


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

async def main() -> int:
    load_dotenv(ROOT / ".env")
    username = os.getenv("X_USERNAME")
    email = os.getenv("X_EMAIL")
    password = os.getenv("X_PASSWORD")
    if not (username and password):
        log.error("Defina X_USERNAME e X_PASSWORD no .env (veja .env.example).")
        return 1

    cfg, candidates = load_config()
    log.info("Coletando %d candidatos × até %d tweets",
             len(candidates), cfg.tweets_per_candidate)

    client = Client("pt-BR")
    try:
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
            cookies_file=str(cfg.cookies_file),
        )
    except TwitterException as e:
        log.error("Falha no login: %s", e)
        return 2

    all_rows: list[dict] = []
    for cand in candidates:
        try:
            rows = await collect_candidate(client, cand, cfg)
            all_rows.extend(rows)
        except TwitterException as e:
            # Não aborta a coleta inteira por erro num candidato (ex.: handle
            # inválido / conta suspensa). Loga e segue.
            log.error("Erro coletando %s: %s", cand.name, e)
            continue
        await asyncio.sleep(cfg.rate_limit_sleep_seconds)

    if not all_rows:
        log.error("Nenhum tweet coletado — verifique config e credenciais.")
        return 3

    write_csv(all_rows, cfg.output_csv)
    log.info("Pronto. Próximo passo: notebooks/analise.ipynb")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
