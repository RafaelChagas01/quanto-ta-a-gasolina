import argparse
import hashlib
import logging
import sys
import time
from pathlib import Path

import requests

from .build import build_dataset, ibge_names, write_dataset
from .links import parse_week_links
from .sheet import SheetFormatError, read_city_prices

ANP_PAGE = (
    "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/"
    "levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas"
)
IBGE_MUNICIPIOS = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado"
USER_AGENT = "quanto-ta-a-gasolina/1.0 (+https://github.com/RafaelChagas01/quanto-ta-a-gasolina)"
MAX_FILE_BYTES = 20 * 1024 * 1024
DELAY_SECONDS = 2.0

log = logging.getLogger("scraper")


def get(session: requests.Session, url: str, max_bytes: int = MAX_FILE_BYTES) -> bytes:
    for attempt in range(1, 4):
        try:
            with session.get(url, timeout=30, stream=True) as resp:
                resp.raise_for_status()
                chunks, size = [], 0
                for chunk in resp.iter_content(64 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError(f"arquivo maior que o limite: {url}")
                    chunks.append(chunk)
                return b"".join(chunks)
        except requests.RequestException as exc:
            if attempt == 3:
                raise
            log.warning("falha em %s (%s), tentando de novo", url, exc)
            time.sleep(DELAY_SECONDS * attempt * 2)
    raise RuntimeError("unreachable")


def download_week(session: requests.Session, url: str, cache_dir: Path) -> bytes:
    cache_file = cache_dir / hashlib.sha256(url.encode()).hexdigest()
    if cache_file.exists():
        return cache_file.read_bytes()

    content = get(session, url)
    if not content.startswith(b"PK"):
        raise ValueError(f"resposta nao parece xlsx: {url}")
    cache_file.write_bytes(content)
    time.sleep(DELAY_SECONDS)
    return content


def main() -> int:
    parser = argparse.ArgumentParser(description="Baixa o levantamento semanal da ANP e gera os JSON do site.")
    parser.add_argument("--weeks", type=int, default=12)
    parser.add_argument("--out", type=Path, default=Path("site/data"))
    parser.add_argument("--cache", type=Path, default=Path(".cache"))
    args = parser.parse_args()

    if not 1 <= args.weeks <= 52:
        parser.error("--weeks precisa estar entre 1 e 52")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args.cache.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    page = get(session, ANP_PAGE, max_bytes=5 * 1024 * 1024).decode("utf-8", errors="replace")
    weeks = parse_week_links(page, ANP_PAGE)[-args.weeks:]
    if not weeks:
        log.error("nenhuma planilha encontrada na pagina da ANP")
        return 1
    log.info("%d semanas encontradas, de %s a %s", len(weeks), weeks[0].end, weeks[-1].end)

    rows = []
    for week in weeks:
        try:
            week_rows, skipped = read_city_prices(download_week(session, week.url, args.cache))
        except (SheetFormatError, ValueError, requests.RequestException) as exc:
            log.warning("semana %s ignorada: %s", week.end, exc)
            continue
        log.info("semana %s: %d linhas, %d descartadas", week.end, len(week_rows), skipped)
        rows.extend(week_rows)

    if not rows:
        log.error("nenhum dado valido")
        return 1

    municipios = requests.get(IBGE_MUNICIPIOS, timeout=30, headers={"User-Agent": USER_AGENT})
    municipios.raise_for_status()
    states, cities = ibge_names(municipios.json())

    dataset = build_dataset(rows, states, cities)
    write_dataset(dataset, args.out)
    log.info("%d estados gravados em %s", len(dataset["states"]), args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
