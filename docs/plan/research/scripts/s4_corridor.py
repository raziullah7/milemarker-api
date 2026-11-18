"""Research script 4: stations along real routes, search radius, plan cost and timings.

Uses the route responses saved by s3_osrm.py. Throwaway research code.
Usage: python -I s4_corridor.py <stations.csv> <cache_dir>
"""
import csv, sys, re, os, json, math, time, collections
import numpy as np
from scipy.spatial import cKDTree

STATIONS, CACHE = sys.argv[1], sys.argv[2]
EARTH = 3958.8
RANGE, MPG, TANK = 500.0, 10.0, 50.0
OVERRIDES = {("GA", "PORTWENTWORTH"): (32.149, -81.163), ("VA", "HENRICO"): (37.50, -77.31), ("AL", "EVERGREEN"): (31.433, -86.957),
             ("NJ", "ELIZABETHPORT"): (40.647, -74.196), ("IL", "UNIVERSITYPARK"): (41.44, -87.68)}


def norm(s):
    s = str(s).upper().strip()
    s = re.sub(r"\bST\.?\s", "SAINT ", s); s = re.sub(r"\bFT\.?\s", "FORT ", s); s = re.sub(r"\bMT\.?\s", "MOUNT ", s)
    return re.sub(r"[^A-Z]", "", s)


def xyz(lat, lon):
    lat, lon = np.radians(lat), np.radians(lon)
    return np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])


def chord(miles):
    return 2 * np.sin(miles / (2 * EARTH))


def arc(ch):
    return 2 * EARTH * np.arcsin(np.clip(ch / 2, 0, 1))


def hav(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    h = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH * np.arcsin(np.sqrt(h))


# ---------- stations: one row per id, lowest price, city-centre position ----------
table = collections.defaultdict(list)
for c in csv.DictReader(open(os.path.join(CACHE, "us_cities.csv"), encoding="utf-8-sig", newline="")):
    table[(c["STATE_CODE"], norm(c["CITY"]))].append((float(c["LATITUDE"]), float(c["LONGITUDE"])))
centre = {k: tuple(np.mean(v, axis=0)) for k, v in table.items()}
centre.update(OVERRIDES)
best = {}
for r in csv.DictReader(open(STATIONS, newline="", encoding="utf-8-sig")):
    p = float(r["Retail Price"])
    if r["OPIS Truckstop ID"] not in best or p < best[r["OPIS Truckstop ID"]][0]:
        best[r["OPIS Truckstop ID"]] = (p, r)
S = []
missing = collections.Counter()
for sid, (p, r) in best.items():
    key = (r["State"].strip(), norm(r["City"]))
    if key in centre:
        S.append((sid, r["Truckstop Name"].strip(), r["City"].strip(), r["State"].strip(), p, centre[key][0], centre[key][1]))
    else:
        missing[r["State"].strip()] += 1
print("stations placed:", len(S), "| not placed:", sum(missing.values()), dict(missing))
s_lat = np.array([s[5] for s in S]); s_lon = np.array([s[6] for s in S]); s_price = np.array([s[4] for s in S])
s_xyz = xyz(s_lat, s_lon)
states = sorted({s[3] for s in S})
print("US state codes with stations:", len(states), "| missing from lower 48 + DC:",
      sorted(set("AL AZ AR CA CO CT DE FL GA ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split()) - set(states)))
t = time.perf_counter(); station_tree = cKDTree(s_xyz); print("build tree over all stations: %.1f ms" % (1000 * (time.perf_counter() - t)))


def load_route(name, variant="full"):
    d = json.load(open(os.path.join(CACHE, "osrm_%s_%s.json" % (name, variant))))
    c = np.array(d["routes"][0]["geometry"]["coordinates"])
    return c[:, 1], c[:, 0], d["routes"][0]["distance"] / 1609.344


def resample(lat, lon, step):
    seg = hav(lat[:-1], lon[:-1], lat[1:], lon[1:])
    cum = np.concatenate([[0], np.cumsum(seg)])
    marks = np.arange(0, cum[-1], step)
    marks = np.append(marks, cum[-1])
    return np.interp(marks, cum, lat), np.interp(marks, cum, lon), marks, cum[-1]


def corridor(lat, lon, radius, step=0.5):
    """Stations within `radius` miles of the route, as (mile_marker, off_route, index) sorted by marker."""
    rlat, rlon, marks, total = resample(lat, lon, step)
    tree = cKDTree(xyz(rlat, rlon))
    d, idx = tree.query(s_xyz, distance_upper_bound=chord(radius))
    keep = np.isfinite(d)
    order = np.argsort(marks[idx[keep]])
    return marks[idx[keep]][order], arc(d[keep])[order], np.flatnonzero(keep)[order], total


def plan(marks, prices, total, start_price):
    """Greedy rule. Returns (cost, stops[(mile, price, gallons)]) or raises ValueError on a gap."""
    # cheapest station per mile marker, origin at 0 with start_price, destination at `total` with price 0
    m = [0.0]; p = [start_price]
    for mm, pp in zip(marks, prices):
        if mm <= 0 or mm >= total:
            continue
        if mm == m[-1]:
            p[-1] = min(p[-1], pp) if len(m) > 1 else p[-1]
            continue
        m.append(float(mm)); p.append(float(pp))
    m.append(float(total)); p.append(0.0)
    fuel, i, stops, cost = 0.0, 0, [], 0.0
    while i < len(m) - 1:
        reach = [j for j in range(i + 1, len(m)) if m[j] - m[i] <= RANGE + 1e-9]
        if not reach:
            raise ValueError("gap of more than %d miles after mile %.0f" % (RANGE, m[i]))
        cheaper = next((j for j in reach if p[j] < p[i]), None)
        if cheaper is not None:
            buy = max(0.0, (m[cheaper] - m[i]) / MPG - fuel); nxt = cheaper
        else:
            buy = TANK - fuel; nxt = min(reach, key=lambda j: p[j])
        if buy > 1e-9:
            stops.append((m[i], p[i], buy)); cost += buy * p[i]
        fuel = fuel + buy - (m[nxt] - m[i]) / MPG
        i = nxt
    return cost, stops


def fewest_stops(marks, prices, total, start_price):
    """Naive driver: fill up, drive as far as possible, fill up again."""
    m = [0.0] + [float(x) for x in marks if 0 < x < total] + [float(total)]
    p = [start_price] + [float(pp) for x, pp in zip(marks, prices) if 0 < x < total] + [0.0]
    i, cost, n = 0, 0.0, 0
    while i < len(m) - 1:
        if total - m[i] <= RANGE:
            cost += (total - m[i]) / MPG * p[i]; n += 1; break
        j = max(k for k in range(i + 1, len(m) - 1) if m[k] - m[i] <= RANGE)
        cost += (m[j] - m[i]) / MPG * p[i]; n += 1; i = j   # buys exactly what the leg burns, arriving empty
    return cost, n


TRIPS = ["nyc_la", "chi_hou", "sea_mia", "det_buf", "dal_hou", "bos_dc"]
print("\n== stations along each route, by search radius")
print("%-8s %7s | %s" % ("trip", "miles", "  ".join("R=%-2d: n / max gap / cost / stops" % r for r in (3, 5, 10))))
for name in TRIPS:
    lat, lon, miles_osrm = load_route(name)
    start_d, start_i = station_tree.query(xyz(lat[:1], lon[:1]))
    start_price = s_price[start_i[0]]
    out = []
    for R in (3, 5, 10):
        marks, off, idx, total = corridor(lat, lon, R)
        gaps = np.diff(np.concatenate([[0], marks, [total]]))
        try:
            cost, stops = plan(marks, s_price[idx], total, start_price)
            out.append("%4d / %5.0f / $%7.2f / %2d" % (len(marks), gaps.max(), cost, len(stops)))
        except ValueError as e:
            out.append("%4d / %5.0f / NO PLAN" % (len(marks), gaps.max()))
    print("%-8s %7.1f | %s   (nearest station to start: %.1f mi, $%.3f)" % (name, miles_osrm, "    ".join(out), arc(start_d[0]), start_price))

print("\n== optimiser against simpler strategies (R=5)")
for name in TRIPS:
    lat, lon, miles_osrm = load_route(name)
    _, start_i = station_tree.query(xyz(lat[:1], lon[:1])); sp = s_price[start_i[0]]
    marks, off, idx, total = corridor(lat, lon, 5)
    cost, stops = plan(marks, s_price[idx], total, sp)
    naive, n = fewest_stops(marks, s_price[idx], total, sp)
    avg = total / MPG * float(np.mean(s_price[idx])) if len(idx) else float("nan")
    print("%-8s optimised $%8.2f (%2d stops, avg $%.3f/gal) | fewest-stops $%8.2f (%d stops) | at average corridor price $%8.2f | saving vs fewest-stops %4.1f%%"
          % (name, cost, len(stops), cost / (total / MPG), naive, n, avg, 100 * (naive - cost) / naive))

print("\n== the NYC to LA plan (R=5)")
lat, lon, miles_osrm = load_route("nyc_la")
_, start_i = station_tree.query(xyz(lat[:1], lon[:1])); sp = s_price[start_i[0]]
marks, off, idx, total = corridor(lat, lon, 5)
lookup = {}
for mm, o, i in zip(marks, off, idx):
    k = round(float(mm), 6)
    if k not in lookup or s_price[i] < s_price[lookup[k][0]]:
        lookup[k] = (i, o)
cost, stops = plan(marks, s_price[idx], total, sp)
for mile, price, gal in stops:
    if mile == 0:
        s = S[start_i[0]]; o = float("nan")
    else:
        i, o = lookup[round(mile, 6)]; s = S[i]
    print("  mile %7.1f  $%.3f  %5.1f gal  $%7.2f  off-route %4.1f mi  %s, %s %s" % (mile, price, gal, gal * price, o, s[1][:32], s[2], s[3]))
print("  total $%.2f for %.1f gallons over %.1f route miles (provider says %.1f)" % (cost, sum(g for _, _, g in stops), total, miles_osrm))

print("\n== our distance sum against the provider's figure")
for name in TRIPS:
    lat, lon, miles_osrm = load_route(name)
    ours = hav(lat[:-1], lon[:-1], lat[1:], lon[1:]).sum()
    print("  %-8s ours %8.2f  provider %8.2f  difference %.3f%%" % (name, ours, miles_osrm, 100 * (ours - miles_osrm) / miles_osrm))

print("\n== timings on the NYC to LA route (best of 7)")
def best_of(f, n=7):
    b = 1e9
    for _ in range(n):
        t = time.perf_counter(); f(); b = min(b, time.perf_counter() - t)
    return 1000 * b
raw = open(os.path.join(CACHE, "osrm_nyc_la_full.json"), "rb").read()
print("  parse provider JSON (793 KB): %.1f ms" % best_of(lambda: json.loads(raw)))
print("  resample to 0.5 mi: %.1f ms" % best_of(lambda: resample(lat, lon, 0.5)))
print("  corridor search, tree over route samples: %.1f ms" % best_of(lambda: corridor(lat, lon, 5)))
marks, off, idx, total = corridor(lat, lon, 5)
print("  fuel plan: %.2f ms" % best_of(lambda: plan(marks, s_price[idx], total, sp)))
def brute():
    rlat, rlon, m, _ = resample(lat, lon, 0.5)
    box = (s_lat > rlat.min() - .2) & (s_lat < rlat.max() + .2) & (s_lon > rlon.min() - .2) & (s_lon < rlon.max() + .2)
    best_d = np.full(box.sum(), 1e9)
    for a in range(0, len(rlat), 512):
        d = hav(s_lat[box][:, None], s_lon[box][:, None], rlat[None, a:a + 512], rlon[None, a:a + 512])
        best_d = np.minimum(best_d, d.min(axis=1))
    return best_d
print("  same search without a tree (numpy only): %.0f ms" % best_of(brute, 2))
coords = np.column_stack([lon, lat])
print("  serialise full geometry to JSON (%d points): %.1f ms, %.0f KB" % (len(lat), best_of(lambda: json.dumps(coords.round(6).tolist())), len(json.dumps(coords.round(6).tolist())) / 1024))

print("\n== simplifying the route line for the response (NYC to LA)")
def rdp(lat, lon, tol_miles):
    x = np.radians(lon) * EARTH * np.cos(np.radians(lat.mean())); y = np.radians(lat) * EARTH
    keep = np.zeros(len(x), bool); keep[0] = keep[-1] = True
    stack = [(0, len(x) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        dx, dy = x[b] - x[a], y[b] - y[a]
        L = math.hypot(dx, dy) or 1e-12
        d = np.abs(dx * (y[a + 1:b] - y[a]) - dy * (x[a + 1:b] - x[a])) / L
        k = int(d.argmax())
        if d[k] > tol_miles:
            k += a + 1; keep[k] = True; stack.append((a, k)); stack.append((k, b))
    return keep
for tol in (0.01, 0.03, 0.06, 0.12, 0.3):
    t = time.perf_counter(); k = rdp(lat, lon, tol); dt = 1000 * (time.perf_counter() - t)
    size = len(json.dumps(np.column_stack([lon[k], lat[k]]).round(5).tolist())) / 1024
    kept_len = hav(lat[k][:-1], lon[k][:-1], lat[k][1:], lon[k][1:]).sum()
    print("  tolerance %4.0f m: %5d points, %4.0f KB JSON, %.0f ms, length kept %.2f%%" % (tol * 1609, k.sum(), size, dt, 100 * kept_len / total))

print("\n== does the simplified provider geometry work for the search?")
slat, slon, _ = load_route("nyc_la", "simplified")
m2, o2, i2, t2 = corridor(slat, slon, 5)
print("  full geometry: %d stations within 5 mi | provider 'simplified' (55 points): %d stations, of which %d are also in the full set"
      % (len(idx), len(i2), len(set(i2) & set(idx))))

print("\n== does Detroit to Buffalo leave the USA?")
lat, lon, m = load_route("det_buf")
d_london = hav(lat, lon, 42.9849, -81.2453).min()
print("  closest approach to London, Ontario: %.1f mi | northernmost point %.3f N" % (d_london, lat.max()))
