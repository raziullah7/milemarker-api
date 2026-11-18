"""Make data/large_places.csv from the US Census Bureau's city and town estimates.

    uv run python scripts/extract_large_places.py path/to/sub-est2023.csv

The file is the Vintage 2023 table of incorporated places (public domain):
https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/cities/totals/sub-est2023.csv

Rows kept: incorporated places (SUMLEV 162) in the covered states with 50,000 people or
more in July 2023. Each city is spelt as the places table spells it, so that
(state, _city_key(city)) is a key of the table. The suggestions in stations/places.py use
the file to put the biggest city first.

A census place the table does not have is left out and listed: it could not be resolved
if suggested. The script fails if a hand mapping below points at a place the table lacks,
or if two census rows land on one table key.
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stations.places import COVERED_STATES, _city_key, _read_table  # noqa: E402

MIN_POPULATION = 50_000
OUTPUT = ROOT / "data" / "large_places.csv"
CITIES_CSV = ROOT / "data" / "us_cities.csv"

# Census names that stripping the suffix cannot turn into the table's name.
HAND_MAPPING = {
    ("TN", "Nashville-Davidson metropolitan government (balance)"): "Nashville",
    ("KY", "Louisville/Jefferson County metro government (balance)"): "Louisville",
    ("IN", "Indianapolis city (balance)"): "Indianapolis",
    ("KY", "Lexington-Fayette urban county"): "Lexington",
    ("GA", "Athens-Clarke County unified government (balance)"): "Athens",
    ("GA", "Augusta-Richmond County consolidated government (balance)"): "Augusta",
    ("GA", "Macon-Bibb County"): "Macon",
    ("ID", "Boise City city"): "Boise",
    ("CA", "San Buenaventura (Ventura) city"): "Ventura",
    ("CT", "Milford city (balance)"): "Milford",
    ("MA", "Methuen Town city"): "Methuen",
    ("MA", "Weymouth Town city"): "Weymouth",
}

_SUFFIX = re.compile(r" (?:city|town|village|borough|municipality)$")
_STATE_FOR_NAME = {name: code for code, name in COVERED_STATES.items()}


def main(census_path: str) -> None:
    table = _read_table(CITIES_CSV)
    kept: dict[tuple[str, str], tuple[str, str, int]] = {}
    missing = []
    with open(census_path, encoding="latin-1", newline="") as f:
        for row in csv.DictReader(f):
            population = int(row["POPESTIMATE2023"])
            state = _STATE_FOR_NAME.get(row["STNAME"])
            if row["SUMLEV"] != "162" or state is None or population < MIN_POPULATION:
                continue
            name = row["NAME"]
            by_hand = (state, name) in HAND_MAPPING
            city = HAND_MAPPING[(state, name)] if by_hand else _SUFFIX.sub("", name)
            key = (state, _city_key(city))
            if key not in table.places:
                if by_hand:
                    sys.exit(f"Hand mapping {state} {name!r} -> {city!r} is not in the table.")
                missing.append(f"{city}, {state} ({population:,})")
                continue
            if key in kept:
                sys.exit(f"Two census rows map to {city}, {state}: {kept[key][0]!r} and {name!r}.")
            kept[key] = (name, table.places[key].label.rsplit(",", 1)[0], population)

    with open(OUTPUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["state", "city", "population"])
        rows = sorted(
            (state, city, population) for (state, _), (_, city, population) in kept.items()
        )
        writer.writerows(rows)

    print(f"Wrote {len(kept)} rows to {OUTPUT}")
    print(f"Left out, not in the places table ({len(missing)}): " + "; ".join(missing))
    print(f"Hand mappings ({len(HAND_MAPPING)}):")
    for (state, name), city in HAND_MAPPING.items():
        print(f"  {state}: {name} -> {city}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
