from datetime import date

from scraper.build import build_dataset, ibge_names
from scraper.sheet import PriceRow
from scraper.text import title_pt

IBGE = [
    {"UF-nome": "São Paulo", "UF-sigla": "SP", "municipio-nome": "São José dos Campos"},
    {"UF-nome": "São Paulo", "UF-sigla": "SP", "municipio-nome": "Araçatuba"},
]


def row(city, end, avg, product="gasolina"):
    return PriceRow(end, "SAO PAULO", city, product, 5, avg, avg - 0.1, avg + 0.1)


def test_uses_ibge_names_and_orders_weeks():
    states, cities = ibge_names(IBGE)
    rows = [
        row("SAO JOSE DOS CAMPOS", date(2026, 9, 12), 6.4),
        row("SAO JOSE DOS CAMPOS", date(2026, 9, 5), 6.3),
        row("ARACATUBA", date(2026, 9, 12), 6.1),
    ]
    data = build_dataset(rows, states, cities)

    assert data["meta"]["weeks"] == ["2026-09-05", "2026-09-12"]
    sp = data["states"]["SP"]
    assert [c["name"] for c in sp["cities"]] == ["Araçatuba", "São José dos Campos"]
    sjc = sp["cities"][1]
    assert sjc["slug"] == "sao-jose-dos-campos"
    assert [p[0] for p in sjc["prices"]["gasolina"]] == [0, 1]


def test_falls_back_to_formatted_name():
    states, cities = ibge_names(IBGE)
    data = build_dataset([row("SANTANA DO LIVRAMENTO", date(2026, 9, 12), 6.0)], states, cities)
    assert data["states"]["SP"]["cities"][0]["name"] == "Santana do Livramento"


def test_title_pt():
    assert title_pt("RIO DE JANEIRO") == "Rio de Janeiro"
    assert title_pt("DAS NEVES") == "Das Neves"
