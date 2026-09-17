import io
from datetime import datetime

import pytest
from openpyxl import Workbook

from scraper.sheet import SheetFormatError, read_city_prices

HEADER = [
    "DATA INICIAL", "DATA FINAL", "ESTADO", "MUNICÍPIO", "PRODUTO",
    "NÚMERO DE POSTOS PESQUISADOS", "UNIDADE DE MEDIDA", "PREÇO MÉDIO REVENDA",
    "DESVIO PADRÃO REVENDA", "PREÇO MÍNIMO REVENDA", "PREÇO MÁXIMO REVENDA",
    "COEF DE VARIAÇÃO REVENDA",
]


def xlsx(rows, sheet="MUNICIPIOS", header=HEADER):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(["AGÊNCIA NACIONAL DO PETRÓLEO"])
    ws.append([])
    ws.append(header)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def line(product="GASOLINA COMUM", stations=10, avg=6.5, lo=6.2, hi=6.9, city="SAO PAULO"):
    d = datetime(2026, 9, 12)
    return [datetime(2026, 9, 6), d, "SAO PAULO", city, product, stations, "R$/l", avg, 0.1, lo, hi, 0.02]


def test_reads_valid_rows():
    rows, skipped = read_city_prices(xlsx([line(), line(product="ÓLEO DIESEL S10")]))
    assert skipped == 0
    assert [r.product for r in rows] == ["gasolina", "diesel_s10"]
    assert rows[0].city == "SAO PAULO"
    assert rows[0].stations == 10


@pytest.mark.parametrize("bad", [
    line(product="QUEROSENE"),
    line(stations=0),
    line(avg=None),
    line(avg=7.5, lo=6.2, hi=6.9),
    line(avg=-1, lo=-2, hi=1),
    line(avg=5000, lo=4000, hi=6000),
    line(city=None),
])
def test_discards_invalid_rows(bad):
    rows, skipped = read_city_prices(xlsx([bad]))
    assert rows == []
    assert skipped == 1


def test_accepts_prices_as_brazilian_text():
    rows, _ = read_city_prices(xlsx([line(avg="6,49", lo="6,19", hi="6,99")]))
    assert rows[0].avg == 6.49


def test_missing_sheet():
    with pytest.raises(SheetFormatError):
        read_city_prices(xlsx([line()], sheet="ESTADOS"))


def test_missing_column():
    header = [h for h in HEADER if h != "PREÇO MÉDIO REVENDA"]
    with pytest.raises(SheetFormatError):
        read_city_prices(xlsx([], header=header))
