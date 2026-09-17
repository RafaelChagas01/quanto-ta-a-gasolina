from datetime import date

from scraper.links import parse_week_links

BASE = "https://www.gov.br/anp/pt-br/precos"
PATH = "https://www.gov.br/anp/pt-br/assuntos/precos/arquivos-lpc/2026/"


def page(*hrefs):
    return "".join(f'<a href="{h}">planilha</a>' for h in hrefs)


def test_reads_regular_and_irregular_names():
    html = page(
        PATH + "resumo_semanal_lpc_2026-09-06_2026-09-12.xlsx",
        PATH + "resumo_semanal_lpc_2026-08-30-2026-09-5.xlsx",
    )
    weeks = parse_week_links(html, BASE)
    assert [w.end for w in weeks] == [date(2026, 9, 5), date(2026, 9, 12)]


def test_ignores_other_files_and_hosts():
    html = page(
        PATH + "revendas_lpc_2026-09-06_2026-09-12.xlsx",
        "https://evil.example.com/resumo_semanal_lpc_2026-09-06_2026-09-12.xlsx",
        "http://www.gov.br/resumo_semanal_lpc_2026-09-06_2026-09-12.xlsx",
        PATH + "agenda.xlsx",
    )
    assert parse_week_links(html, BASE) == []


def test_ignores_invalid_dates_and_ranges():
    html = page(
        PATH + "resumo_semanal_lpc_2026-02-30_2026-03-05.xlsx",
        PATH + "resumo_semanal_lpc_2026-01-01_2026-03-01.xlsx",
    )
    assert parse_week_links(html, BASE) == []


def test_resolves_relative_links_and_dedupes():
    html = page(
        "/anp/arquivos/resumo_semanal_lpc_2026-09-06_2026-09-12.xlsx",
        PATH + "resumo_semanal_lpc_2026-09-06_2026-09-12.xlsx",
    )
    weeks = parse_week_links(html, BASE)
    assert len(weeks) == 1
    assert weeks[0].url.startswith("https://www.gov.br/")
