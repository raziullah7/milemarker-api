"""Draw the two README images from two answers of the API.

The images are made from what the API itself returned, so they show real figures:

    curl -o plan.json "http://127.0.0.1:8000/api/v1/route/?start=New%20York,%20NY&finish=Los%20Angeles,%20CA"
    curl -o free.json "http://127.0.0.1:8000/api/v1/route/?start=New%20York,%20NY&finish=Los%20Angeles,%20CA&stop_cost=0"
    uv run --with matplotlib python scripts/draw_readme_images.py plan.json free.json states.geojson

states.geojson is Natural Earth's 1:110m states and provinces (public domain):
https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_1_states_provinces.geojson

matplotlib is not a dependency of the project; `uv run --with` fetches it for the one run.
Writes docs/images/route-nyc-la.png and docs/images/stops-compared.png.
"""

import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
ROAD = "#1f6feb"
STOP = "#d1242f"
INK = "#24292f"
LAND = "#eef1f4"
EDGE = "#b8c0c8"


def _read(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rings(geometry: dict) -> list[list[list[float]]]:
    """Every outer and inner ring of a Polygon or MultiPolygon."""
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    return [ring for polygon in geometry["coordinates"] for ring in polygon]


def draw_route(plan: dict, states: dict) -> None:
    """The road, the stops and the lower 48 states."""
    fig, ax = plt.subplots(figsize=(12, 6.6), dpi=150)
    for feature in states["features"]:
        props = feature["properties"]
        if props.get("adm0_a3") != "USA" or props.get("postal") in ("AK", "HI"):
            continue
        for ring in _rings(feature["geometry"]):
            xs, ys = zip(*ring, strict=True)
            ax.fill(xs, ys, color=LAND, edgecolor=EDGE, linewidth=0.6, zorder=1)

    [line] = [f for f in plan["map"]["features"] if f["geometry"]["type"] == "LineString"]
    xs, ys = zip(*line["geometry"]["coordinates"], strict=True)
    ax.plot(xs, ys, color=ROAD, linewidth=2.4, zorder=2, solid_capstyle="round")

    summary = plan["summary"]
    for place, where in ((summary["start"], "Start"), (summary["finish"], "Finish")):
        # Stop 1 is drawn at the start, so the start's own dot sits under it.
        ax.plot(place["lng"], place["lat"], "o", color=INK, markersize=7, zorder=2.5)
        ax.annotate(
            f"{where}: {place['label']}",
            (place["lng"], place["lat"]),
            xytext=(10, -22) if where == "Start" else (6, -18),
            textcoords="offset points",
            fontsize=10,
            color=INK,
            ha="right" if where == "Start" else "left",
            zorder=5,
        )
    for stop in plan["fuel_stops"]:
        ax.plot(stop["lng"], stop["lat"], "o", color=STOP, markersize=13, zorder=3)
        ax.annotate(
            str(stop["order"]),
            (stop["lng"], stop["lat"]),
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            color="white",
            zorder=4,
        )

    ax.set_xlim(-125, -66)
    ax.set_ylim(24.5, 49.5)
    ax.set_aspect(1 / math.cos(math.radians(37)))
    ax.axis("off")
    ax.set_title(
        f"{summary['start']['label']} to {summary['finish']['label']}: "
        f"{summary['distance_miles']:,} miles, {summary['stops']} fuel stops, "
        f"${summary['total_fuel_cost']:,.2f}",
        fontsize=13,
        color=INK,
        pad=12,
    )
    fig.text(
        0.99,
        0.02,
        "Route: OSRM, OpenStreetMap data. Outlines: Natural Earth.",
        ha="right",
        fontsize=7,
        color="#6e7781",
    )
    fig.savefig(OUT / "route-nyc-la.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def draw_comparison(plan: dict, free: dict) -> None:
    """The stops of the default plan against the cheapest bill, along the same miles."""
    fig, ax = plt.subplots(figsize=(12, 3.6), dpi=150)
    rows = [
        (1, free, "Cheapest bill (stop_cost=0)"),
        (0, plan, r"Default (each stop counted as \$10)"),
    ]
    for y, answer, title in rows:
        summary = answer["summary"]
        ax.hlines(y, 0, summary["distance_miles"], color=EDGE, linewidth=1.5, zorder=1)
        for stop in answer["fuel_stops"]:
            size = 20 + stop["gallons"] * 14
            ax.scatter(stop["mile_marker"], y, s=size, color=STOP, alpha=0.75, zorder=2)
        ax.text(
            -60,
            y + 0.22,
            rf"{title}: {summary['stops']} stops, \${summary['total_fuel_cost']:,.2f}",
            fontsize=11,
            color=INK,
        )
    smallest = min(free["fuel_stops"], key=lambda stop: stop["gallons"])
    ax.annotate(
        f"{smallest['gallons']} gallons",
        (smallest["mile_marker"], 1),
        xytext=(smallest["mile_marker"] + 140, 0.62),
        fontsize=9,
        color=INK,
        arrowprops={"arrowstyle": "-", "color": "#6e7781"},
    )
    ax.set_ylim(-0.45, 1.6)
    ax.set_xlim(-80, plan["summary"]["distance_miles"] + 60)
    ax.set_yticks([])
    ax.set_xlabel("Miles from New York (dot size: gallons bought)", color=INK)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    fig.savefig(OUT / "stops-compared.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    plan_path, free_path, states_path = sys.argv[1:4]
    OUT.mkdir(parents=True, exist_ok=True)
    plan, free = _read(plan_path), _read(free_path)
    draw_route(plan, _read(states_path))
    draw_comparison(plan, free)


if __name__ == "__main__":
    main()
