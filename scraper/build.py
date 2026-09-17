import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .sheet import PriceRow
from .text import key, slugify, title_pt

PRODUCT_INFO = {
    "gasolina": {"label": "Gasolina comum", "unit": "R$/l"},
    "gasolina_aditivada": {"label": "Gasolina aditivada", "unit": "R$/l"},
    "etanol": {"label": "Etanol", "unit": "R$/l"},
    "diesel_s10": {"label": "Diesel S10", "unit": "R$/l"},
    "diesel": {"label": "Diesel S500", "unit": "R$/l"},
    "gnv": {"label": "GNV", "unit": "R$/m³"},
    "glp": {"label": "Gás de cozinha (13kg)", "unit": "R$/13kg"},
}


def ibge_names(municipios: list[dict]) -> tuple[dict, dict]:
    """Monta os dicionarios de nomes a partir de /localidades/municipios?view=nivelado."""
    states: dict[str, dict] = {}
    cities: dict[tuple[str, str], str] = {}
    for m in municipios:
        state_key = key(m["UF-nome"])
        states[state_key] = {"uf": m["UF-sigla"], "name": m["UF-nome"]}
        cities[(state_key, key(m["municipio-nome"]))] = m["municipio-nome"]
    return states, cities


def build_dataset(rows: list[PriceRow], states: dict, cities: dict) -> dict:
    weeks = sorted({r.end for r in rows})
    week_index = {w: i for i, w in enumerate(weeks)}

    by_state: dict[str, dict] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for r in rows:
        by_state[r.state][r.city][r.product].append(
            [week_index[r.end], r.avg, r.min, r.max, r.stations]
        )

    state_files = {}
    state_list = []
    for state_key, city_map in by_state.items():
        info = states.get(state_key)
        if info is None:
            continue

        city_list = []
        for city_key, products in city_map.items():
            name = cities.get((state_key, city_key)) or title_pt(city_key)
            city_list.append({
                "name": name,
                "slug": slugify(name),
                "prices": {p: sorted(points) for p, points in products.items()},
            })
        city_list.sort(key=lambda c: key(c["name"]))

        state_files[info["uf"]] = {"uf": info["uf"], "name": info["name"], "cities": city_list}
        state_list.append({"uf": info["uf"], "name": info["name"], "cities": len(city_list)})

    state_list.sort(key=lambda s: key(s["name"]))
    meta = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "ANP - Levantamento de Preços de Combustíveis",
        "weeks": [w.isoformat() for w in weeks],
        "products": PRODUCT_INFO,
        "states": state_list,
    }
    return {"meta": meta, "states": state_files}


def write_dataset(dataset: dict, out_dir: Path) -> None:
    uf_dir = out_dir / "uf"
    uf_dir.mkdir(parents=True, exist_ok=True)

    for old in uf_dir.glob("*.json"):
        if old.stem not in dataset["states"]:
            old.unlink()

    for uf, content in dataset["states"].items():
        _dump(content, uf_dir / f"{uf}.json")
    _dump(dataset["meta"], out_dir / "meta.json")


def _dump(content: dict, path: Path) -> None:
    text = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text + "\n", encoding="utf-8")
