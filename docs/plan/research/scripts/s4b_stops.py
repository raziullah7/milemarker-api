"""Research script 4b: too many tiny stops. Test thinning the candidate stations, plus corrected timings.

Usage: python -I s4b_stops.py <stations.csv> <cache_dir>
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


chord = lambda miles: 2 * np.sin(miles / (2 * EARTH))
arc = lambda ch: 2 * EARTH * np.arcsin(np.clip(ch / 2, 0, 1))


def hav(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    h = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH * np.arcsin(np.sqrt(h))


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
S = [(sid, r["Truckstop Name"].strip(), r["City"].strip(), r["State"].strip(), p) + centre[(r["State"].strip(), norm(r["City"]))]
     for sid, (p, r) in best.items() if (r["State"].strip(), norm(r["City"])) in centre]
s_lat = np.array([s[5] for s in S]); s_lon = np.array([s[6] for s in S]); s_price = np.array([s[4] for s in S])
s_xyz = xyz(s_lat, s_lon)
station_tree = cKDTree(s_xyz)


def load_route(name, variant="full", reverse=False):
    d = json.load(open(os.path.join(CACHE, "osrm_%s_%s.json" % (name, variant))))
    c = np.array(d["routes"][0]["geometry"]["coordinates"])
    if reverse:
        c = c[::-1]
    return c[:, 1], c[:, 0], d["routes"][0]["distance"] / 1609.344


def resample(lat, lon, step):
    seg = hav(lat[:-1], lon[:-1], lat[1:], lon[1:])
    cum = np.concatenate([[0], np.cumsum(seg)])
    marks = np.append(np.arange(0, cum[-1], step), cum[-1])
    return np.interp(marks, cum, lat), np.interp(marks, cum, lon), marks, cum[-1]


def corridor(lat, lon, radius, step=0.5):
    rlat, rlon, marks, total = resample(lat, lon, step)
    d, idx = cKDTree(xyz(rlat, rlon)).query(s_xyz, distance_upper_bound=chord(radius))
    keep = np.isfinite(d)
    order = np.argsort(marks[idx[keep]], kind="stable")
    return marks[idx[keep]][order], np.flatnonzero(keep)[order], total


def thin(marks, prices, window):
    """Keep a station only if nothing within `window` miles along the route is cheaper (ties: the earlier one)."""
    if window <= 0:
        return np.ones(len(marks), bool)
    keep = np.zeros(len(marks), bool)
    lo = np.searchsorted(marks, marks - window, "left"); hi = np.searchsorted(marks, marks + window, "right")
    for i in range(len(marks)):
        seg = prices[lo[i]:hi[i]]
        keep[i] = (lo[i] + int(seg.argmin())) == i
    return keep


def plan(marks, prices, total, start_price):
    m = [0.0] + [float(x) for x in marks] + [float(total)]
    p = [float(start_price)] + [float(x) for x in prices] + [0.0]
    fuel, i, stops = 0.0, 0, []
    while i < len(m) - 1:
        reach = [j for j in range(i + 1, len(m)) if m[j] - m[i] <= RANGE + 1e-9]
        if not reach:
            raise ValueError("gap after mile %.0f" % m[i])
        cheaper = next((j for j in reach if p[j] < p[i]), None)
        if cheaper is not None:
            buy = max(0.0, (m[cheaper] - m[i]) / MPG - fuel); nxt = cheaper
        else:
            buy = TANK - fuel; nxt = min(reach, key=lambda j: p[j])
        if buy > 1e-9:
            stops.append((m[i], p[i], buy))
        fuel = fuel + buy - (m[nxt] - m[i]) / MPG
        i = nxt
    return sum(g * pr for _, pr, g in stops), stops


def prepare(name, R=5, reverse=False):
    lat, lon, _ = load_route(name, reverse=reverse)
    d0, i0 = station_tree.query(xyz(lat[:1], lon[:1]))
    marks, idx, total = corridor(lat, lon, R)
    inside = (marks > 0) & (marks < total)
    return marks[inside], idx[inside], total, float(s_price[i0[0]]), float(arc(d0[0])), i0[0]


print("== thinning the candidates: only the cheapest station within W miles along the route stays (R=5)")
print("%-10s %7s | %s" % ("trip", "miles", "   ".join("W=%-3d cand/stops/min gal/cost" % w for w in (0, 10, 25, 50))))
TR = [("nyc_la", False), ("nyc_la", True), ("chi_hou", False), ("sea_mia", False), ("sea_mia", True), ("det_buf", False), ("dal_hou", False), ("bos_dc", False)]
base = {}
for name, rev in TR:
    marks, idx, total, sp, d0, i0 = prepare(name, reverse=rev)
    out = []
    for W in (0, 10, 25, 50):
        k = thin(marks, s_price[idx], W)
        cost, stops = plan(marks[k], s_price[idx][k], total, sp)
        base.setdefault((name, rev), cost)
        out.append("%3d/%2d/%4.1f/$%7.2f(+%.1f%%)" % (k.sum(), len(stops), min(g for _, _, g in stops), cost, 100 * (cost / base[(name, rev)] - 1)))
    print("%-10s %7.1f | %s   start station %.0f mi away" % (name + ("_rev" if rev else ""), total, "   ".join(out), d0))

for name, rev, W in (("nyc_la", False, 25), ("nyc_la", True, 25)):
    marks, idx, total, sp, d0, i0 = prepare(name, reverse=rev)
    k = thin(marks, s_price[idx], W)
    cost, stops = plan(marks[k], s_price[idx][k], total, sp)
    print("\n== %s%s with W=%d: %d stops, $%.2f" % (name, " reversed (LA to NYC)" if rev else "", W, len(stops), cost))
    by_mark = {round(float(m), 6): i for m, i in zip(marks[k], idx[k])}
    for mile, price, gal in stops:
        s = S[i0] if mile == 0 else S[by_mark[round(mile, 6)]]
        note = "  (start fill-up, station %.0f mi from start)" % d0 if mile == 0 else ""
        print("  mile %7.1f  $%.3f  %5.1f gal  $%7.2f  %s, %s %s%s" % (mile, price, gal, gal * price, s[1][:30], s[2], s[3], note))

print("\n== timings on the NYC to LA route, 34,931 points (best of 7)")
def best_of(f, n=7):
    b = 1e9
    for _ in range(n):
        t = time.perf_counter(); f(); b = min(b, time.perf_counter() - t)
    return 1000 * b
lat, lon, _ = load_route("nyc_la")
raw = open(os.path.join(CACHE, "osrm_nyc_la_full.json"), "rb").read()
marks, idx, total, sp, d0, i0 = prepare("nyc_la")
print("  parse provider JSON (%d KB): %.1f ms" % (len(raw) / 1024, best_of(lambda: json.loads(raw))))
print("  to numpy array: %.1f ms" % best_of(lambda: np.array(json.loads(raw)["routes"][0]["geometry"]["coordinates"])))
print("  corridor search (resample + tree + query): %.1f ms" % best_of(lambda: corridor(lat, lon, 5)))
print("  thin + fuel plan: %.2f ms" % best_of(lambda: plan(marks[thin(marks, s_price[idx], 25)], s_price[idx][thin(marks, s_price[idx], 25)], total, sp)))
def brute():
    rlat, rlon, m, _ = resample(lat, lon, 0.5)
    box = (s_lat > rlat.min() - .2) & (s_lat < rlat.max() + .2) & (s_lon > rlon.min() - .2) & (s_lon < rlon.max() + .2)
    b = np.full(int(box.sum()), 1e9)
    for a in range(0, len(rlat), 512):
        b = np.minimum(b, hav(s_lat[box][:, None], s_lon[box][:, None], rlat[None, a:a + 512], rlon[None, a:a + 512]).min(axis=1))
    return b
print("  same search without a tree (numpy only): %.0f ms" % best_of(brute, 2))
full_json = json.dumps(np.column_stack([lon, lat]).round(6).tolist())
print("  serialise full geometry: %.1f ms, %.0f KB" % (best_of(lambda: json.dumps(np.column_stack([lon, lat]).round(6).tolist())), len(full_json) / 1024))

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
        j = int(d.argmax())
        if d[j] > tol_miles:
            j += a + 1; keep[j] = True; stack.append((a, j)); stack.append((j, b))
    return keep
for tol in (0.006, 0.012, 0.03, 0.06, 0.12):
    kk = None
    ms = best_of(lambda: rdp(lat, lon, tol), 3); kk = rdp(lat, lon, tol)
    size = len(json.dumps(np.column_stack([lon[kk], lat[kk]]).round(5).tolist())) / 1024
    kept = hav(lat[kk][:-1], lon[kk][:-1], lat[kk][1:], lon[kk][1:]).sum()
    print("  tolerance %3.0f m: %5d points, %4.0f KB JSON, %3.0f ms, length kept %.2f%%" % (tol * 1609, kk.sum(), size, ms, 100 * kept / total))
for step in (0.25, 0.5, 1.0):
    rlat, rlon, m, _ = resample(lat, lon, step)
    print("  even spacing %.2f mi: %5d points, %4.0f KB JSON" % (step, len(m), len(json.dumps(np.column_stack([rlon, rlat]).round(5).tolist())) / 1024))

print("\n== can the provider's own 'simplified' geometry be used for the search? (NYC to LA, R=5)")
slat, slon, _ = load_route("nyc_la", "simplified")
m2, i2, t2 = corridor(slat, slon, 5)
m1, i1, t1 = corridor(lat, lon, 5)
print("  full: %d stations | simplified (55 points): %d stations, only %d in common; length %.0f vs %.0f mi" % (len(i1), len(i2), len(set(i1) & set(i2)), t1, t2))
