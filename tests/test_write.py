import json

from scraper.build import write_dataset


def dataset(price, updated="2026-09-16T10:00:00Z"):
    return {
        "meta": {"updated_at": updated, "weeks": ["2026-09-12"], "states": []},
        "states": {"SP": {"uf": "SP", "cities": [{"name": "Campinas", "prices": {"gasolina": [[0, price, 6, 7, 5]]}}]}},
    }


def test_keeps_updated_at_when_nothing_changed(tmp_path):
    assert write_dataset(dataset(6.5), tmp_path) is True
    assert write_dataset(dataset(6.5, updated="2026-09-20T10:00:00Z"), tmp_path) is False
    meta = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
    assert meta["updated_at"] == "2026-09-16T10:00:00Z"


def test_updates_when_prices_change(tmp_path):
    write_dataset(dataset(6.5), tmp_path)
    assert write_dataset(dataset(6.6, updated="2026-09-20T10:00:00Z"), tmp_path) is True
    meta = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
    assert meta["updated_at"] == "2026-09-20T10:00:00Z"


def test_removes_states_that_left(tmp_path):
    (tmp_path / "uf").mkdir()
    (tmp_path / "uf" / "XX.json").write_text("{}", encoding="utf-8")
    write_dataset(dataset(6.5), tmp_path)
    assert not (tmp_path / "uf" / "XX.json").exists()
