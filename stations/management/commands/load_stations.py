"""Replace the FuelStation table with the stations in the supplied CSV.

Safe to run again: the table is replaced inside one transaction. After reloading, restart
the server so it picks up the new stations (the index is read once per process).
"""

import csv
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from stations import places
from stations.models import FuelStation


class Command(BaseCommand):
    help = "Load fuel stations from the CSV into the database, placing each at its city centre."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--csv", default=settings.STATIONS_CSV, help="the fuel prices CSV")
        parser.add_argument("--cities", default=settings.CITIES_CSV, help="the places table CSV")

    def handle(self, *args, **options) -> None:
        rows = read_rows(Path(options["csv"]))
        self.stdout.write(f"Rows read: {len(rows)}")

        stations = cheapest_listing_per_station(rows)
        self.stdout.write(f"Stations: {len(stations)}")

        in_coverage = [s for s in stations if s["State"] in places.COVERED_STATES]
        self.stdout.write(f"In the lower 48 and DC: {len(in_coverage)}")

        # Point the lookup at --cities for this run only, then put the default back.
        places.use_cities_file(options["cities"])
        try:
            saved, unplaced, hand_added = [], [], 0
            for row in in_coverage:
                position = places.locate_city(row["City"], row["State"])
                if position is None:
                    unplaced.append(row)
                    continue
                hand_added += places.is_hand_added(row["City"], row["State"])
                saved.append(FuelStation(**station_fields(row), lat=position[0], lng=position[1]))
        finally:
            places.use_cities_file(None)

        if unplaced:
            lines = [
                f"station {s['OPIS Truckstop ID']} {s['Truckstop Name']}: {s['City']}, {s['State']}"
                for s in unplaced
            ]
            raise CommandError("Could not place these stations:\n" + "\n".join(lines))

        self.stdout.write(f"Placed from the places table: {len(saved) - hand_added}")
        self.stdout.write(f"Placed from hand-added places: {hand_added}")

        # One transaction: a failure part-way leaves the old table exactly as it was.
        with transaction.atomic():
            FuelStation.objects.all().delete()
            FuelStation.objects.bulk_create(saved)
        self.stdout.write(f"Saved: {len(saved)}")


def read_rows(path: Path) -> list[dict[str, str]]:
    """Every CSV row, with whitespace stripped from every field."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [{key: value.strip() for key, value in row.items()} for row in csv.DictReader(f)]


def cheapest_listing_per_station(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """One row per station ID: its cheapest listing, the first in the file on a price tie."""
    best: dict[str, dict[str, str]] = {}
    for row in rows:
        current = best.get(row["OPIS Truckstop ID"])
        if current is None or Decimal(row["Retail Price"]) < Decimal(current["Retail Price"]):
            best[row["OPIS Truckstop ID"]] = row
    return list(best.values())


def station_fields(row: dict[str, str]) -> dict:
    """The FuelStation fields a CSV row gives, apart from the position."""
    return {
        "opis_id": int(row["OPIS Truckstop ID"]),
        "name": row["Truckstop Name"],
        "address": row["Address"],
        "city": row["City"],
        "state": row["State"],
        "rack_id": int(row["Rack ID"]),
        "price": Decimal(row["Retail Price"]),
    }
