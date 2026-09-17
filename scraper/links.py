import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

ALLOWED_HOSTS = {"www.gov.br", "gov.br"}

# a ANP nao segue um padrao fixo: ja apareceu "2026-08-30-2026-09-5"
FILE_RE = re.compile(
    r"resumo_semanal_lpc_(\d{4})-(\d{1,2})-(\d{1,2})[_-](\d{4})-(\d{1,2})-(\d{1,2})\.xlsx$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class WeekFile:
    start: date
    end: date
    url: str


def parse_week_links(html: str, base_url: str) -> list[WeekFile]:
    soup = BeautifulSoup(html, "html.parser")
    found: dict[date, WeekFile] = {}

    for a in soup.find_all("a", href=True):
        url = urljoin(base_url, a["href"].strip())
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            continue

        match = FILE_RE.search(parsed.path)
        if not match:
            continue

        y1, m1, d1, y2, m2, d2 = map(int, match.groups())
        try:
            start, end = date(y1, m1, d1), date(y2, m2, d2)
        except ValueError:
            continue
        if not 5 <= (end - start).days <= 7:
            continue

        found.setdefault(end, WeekFile(start, end, url))

    return sorted(found.values(), key=lambda w: w.end)
