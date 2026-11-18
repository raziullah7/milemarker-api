"""Research script 7: can a small public-domain outline of the lower 48 states tell us
(a) whether a coordinate is inside the USA and (b) whether a route leaves the USA?

Usage: python -I s7_border.py <cache_dir>
"""
import sys, os, json, time, urllib.request
import numpy as np

CACHE = sys.argv[1]
EARTH = 3958.8


def fetch(url, name):
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        req = urllib.request.Request(url, headers={"User-Agent": "route-research/0.1"})
        with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
            f.write(r.read())
    return json.load(open(path, encoding="utf-8"))


def outline(scale):
    d = fetch("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_%s_admin_0_countries.geojson" % scale,
              "ne_%s_countries.geojson" % scale)
    usa = next(f for f in d["features"] if f["properties"].get("ADM0_A3") == "USA")
    polys = usa["geometry"]["coordinates"] if usa["geometry"]["type"] == "MultiPolygon" else [usa["geometry"]["coordinates"]]
    rings = [np.array(p[0]) for p in polys]                      # outer ring of each part
    return max(rings, key=len), len(rings), os.path.getsize(os.path.join(CACHE, "ne_%s_countries.geojson" % scale)) / 1e6


def inside(lon, lat, ring):
    """Ray casting, vectorised over points."""
    x, y = np.atleast_1d(lon)[:, None], np.atleast_1d(lat)[:, None]
    x1, y1 = ring[:-1, 0][None, :], ring[:-1, 1][None, :]
    x2, y2 = ring[1:, 0][None, :], ring[1:, 1][None, :]
    crosses = (y1 > y) != (y2 > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
    return (crosses & (x < xi)).sum(axis=1) % 2 == 1


def hav(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    h = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH * np.arcsin(np.sqrt(h))


POINTS = [  # name, lat, lon, truly in the USA?
    ("Kansas centre", 38.5, -98.0, True), ("El Paso downtown", 31.7587, -106.4869, True), ("Ciudad Juarez centre", 31.7381, -106.4870, False),
    ("Detroit downtown", 42.3314, -83.0458, True), ("Windsor ON downtown", 42.3149, -83.0364, False), ("Laredo downtown", 27.5036, -99.5076, True),
    ("Nuevo Laredo centre", 27.4861, -99.5069, False), ("San Ysidro", 32.5520, -117.0430, True), ("Tijuana centre", 32.5149, -117.0382, False),
    ("Buffalo downtown", 42.8864, -78.8784, True), ("Fort Erie ON", 42.9018, -78.9722, False), ("Niagara Falls NY", 43.0962, -79.0377, True),
    ("Toronto", 43.6532, -79.3832, False), ("Vancouver BC", 49.2827, -123.1207, False), ("Blaine WA", 48.9937, -122.7471, True),
    ("Seattle", 47.6062, -122.3321, True), ("Miami", 25.7617, -80.1918, True), ("Key West", 24.5551, -81.7800, True),
    ("Brownsville TX", 25.9017, -97.4975, True), ("Matamoros", 25.8690, -97.5027, False), ("Montreal", 45.5019, -73.5674, False),
    ("Calais ME", 45.1890, -67.2786, True), ("Sault Ste Marie MI", 46.4953, -84.3453, True), ("Sault Ste Marie ON", 46.5136, -84.3358, False),
    ("New York", 40.748, -73.997, True), ("Cape Cod Provincetown", 42.0584, -70.1786, True), ("Galveston", 29.3013, -94.7977, True),
    ("Long Island Montauk", 41.0359, -71.9545, True), ("San Francisco", 37.7749, -122.4194, True), ("London UK", 51.5, -0.12, False),
]

for scale in ("50m", "10m"):
    ring, parts, mb = outline(scale)
    print("== Natural Earth %s: source file %.1f MB, USA has %d parts, main outline %d vertices (%.0f KB as JSON)"
          % (scale, mb, parts, len(ring), len(json.dumps(ring.round(4).tolist())) / 1024))
    lat = np.array([p[1] for p in POINTS]); lon = np.array([p[2] for p in POINTS])
    got = inside(lon, lat, ring)
    wrong = [(p[0], bool(g)) for p, g in zip(POINTS, got) if bool(g) != p[3]]
    print("   %d of %d test points classified correctly; wrong: %s" % (len(POINTS) - len(wrong), len(POINTS), wrong))
    for name in ("det_buf", "nyc_la", "sea_mia", "chi_hou", "bos_dc", "dal_hou"):
        d = json.load(open(os.path.join(CACHE, "osrm_%s_full.json" % name)))
        c = np.array(d["routes"][0]["geometry"]["coordinates"])
        seg = hav(c[:-1, 1], c[:-1, 0], c[1:, 1], c[1:, 0]); cum = np.concatenate([[0], np.cumsum(seg)])
        marks = np.arange(0, cum[-1], 2.0)
        slon, slat = np.interp(marks, cum, c[:, 0]), np.interp(marks, cum, c[:, 1])
        t = time.perf_counter(); out = ~inside(slon, slat, ring); ms = 1000 * (time.perf_counter() - t)
        print("   %-8s %4d samples, %6.0f miles outside the outline (%.0f ms)" % (name, len(marks), 2.0 * out.sum(), ms))
