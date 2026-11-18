"""Research script 5: an optimiser that charges a small cost per stop, checked against exact solvers.

1. The greedy rule and the dynamic programme (stop cost 0) are compared with a linear-programming solver.
2. The dynamic programme with a stop cost is compared with brute force over every subset of stations.
3. The dynamic programme is run on the real routes for several stop costs.

Usage: python -I s5_optimiser.py <stations.csv> <cache_dir>
"""
import csv, sys, re, os, json, math, time, random, itertools, collections, functools
import numpy as np
from scipy.optimize import linprog
from scipy.spatial import cKDTree

STATIONS, CACHE = sys.argv[1], sys.argv[2]
RANGE, MPG, TANK = 500.0, 10.0, 50.0
EPS = 1e-9


def greedy(m, p, total):
    """m, p: mile markers and prices of the stations, m[0] == 0 is the start station. Returns (cost, purchases)."""
    m = list(m) + [total]; p = list(p) + [0.0]
    fuel, i, buys = 0.0, 0, []
    while i < len(m) - 1:
        reach = [j for j in range(i + 1, len(m)) if m[j] - m[i] <= RANGE + EPS]
        if not reach:
            return None
        cheaper = next((j for j in reach if p[j] < p[i]), None)
        if cheaper is not None:
            buy = max(0.0, (m[cheaper] - m[i]) / MPG - fuel); nxt = cheaper
        else:
            buy = TANK - fuel; nxt = min(reach, key=lambda j: p[j])
        if buy > EPS:
            buys.append((i, buy))
        fuel = fuel + buy - (m[nxt] - m[i]) / MPG
        i = nxt
    return sum(b * p[i] for i, b in buys), buys


def dp(m, p, total, stop_cost):
    """Cheapest plan when every stop also costs `stop_cost` dollars. Returns (fuel_cost, purchases) or None."""
    n = len(m)
    import sys as _s; _s.setrecursionlimit(10000)

    @functools.lru_cache(maxsize=None)
    def best(u, prev):
        # fuel in the tank on arrival: empty, or what is left of a full tank bought at `prev`
        g = 0.0 if prev < 0 else TANK - (m[u] - m[prev]) / MPG
        out = (math.inf, None, 0.0)
        need = (total - m[u]) / MPG
        if total - m[u] <= RANGE + EPS and g <= need + EPS:           # buy just enough to finish
            out = (stop_cost + (need - g) * p[u], None, need - g)
        for v in range(u + 1, n):
            d = m[v] - m[u]
            if d > RANGE + EPS:
                break
            if p[v] <= p[u]:                                          # buy just enough to reach a station that is no dearer
                need = d / MPG
                if g > need + EPS:
                    continue
                c = stop_cost + (need - g) * p[u] + best(v, -1)[0]
                if c < out[0]:
                    out = (c, (v, -1), need - g)
            else:                                                     # fill up and carry the cheaper fuel past a dearer station
                c = stop_cost + (TANK - g) * p[u] + best(v, u)[0]
                if c < out[0]:
                    out = (c, (v, u), TANK - g)
        return out

    if best(0, -1)[0] == math.inf:
        return None
    buys, state = [], (0, -1)
    while state is not None:
        c, nxt, buy = best(*state)
        buys.append((state[0], buy))
        state = nxt
    return sum(b * p[i] for i, b in buys), buys


def lp(m, p, total):
    n = len(m)
    pos = list(m) + [total]
    A, b = [], []
    for j in range(1, n + 1):                 # never run dry before station j (or the finish)
        A.append([-1.0] * j + [0.0] * (n - j)); b.append(-pos[j] / MPG)
    for j in range(n):                        # never overfill at station j
        A.append([1.0] * (j + 1) + [0.0] * (n - j - 1)); b.append(TANK + pos[j] / MPG)
    r = linprog(p, A_ub=A, b_ub=b, bounds=[(0, None)] * n, method="highs")
    return r.fun if r.success else None


def brute(m, p, total, stop_cost):
    n, best = len(m), math.inf
    for k in range(0, n):
        for extra in itertools.combinations(range(1, n), k):
            idx = (0,) + extra
            r = greedy([m[i] for i in idx], [p[i] for i in idx], total)
            if r:
                best = min(best, r[0] + stop_cost * len(r[1]))
    return best


random.seed(11)
print("== 1. stop cost 0: greedy and dynamic programme against a linear-programming solver")
worst_g = worst_d = 0.0; n_cases = infeasible = 0
for _ in range(400):
    n = random.randint(1, 28); total = random.uniform(50, 3000)
    m = [0.0] + sorted(round(random.uniform(1, total - 1), 1) for _ in range(n - 1))
    p = [round(random.uniform(2.6, 4.5), 3) for _ in range(n)]
    if random.random() < 0.3:
        p = [random.choice([2.9, 3.1, 3.3]) for _ in range(n)]      # many ties
    ref = lp(m, p, total); g = greedy(m, p, total); d = dp(m, p, total, 0.0)
    if ref is None:
        infeasible += 1
        assert g is None and d is None, "solvers disagree about feasibility"
        continue
    n_cases += 1
    worst_g = max(worst_g, abs(g[0] - ref)); worst_d = max(worst_d, abs(d[0] - ref))
print("   feasible cases: %d | infeasible (all three agree): %d" % (n_cases, infeasible))
print("   largest difference from the exact answer: greedy $%.6f | dynamic programme $%.6f" % (worst_g, worst_d))

print("== 2. with a stop cost: dynamic programme against brute force over every subset of stations")
worst = 0.0; n_cases = 0
for _ in range(250):
    n = random.randint(1, 10); total = random.uniform(100, 1800); sc = random.choice([1, 5, 10, 25, 60])
    m = [0.0] + sorted(round(random.uniform(1, total - 1), 1) for _ in range(n - 1))
    p = [round(random.uniform(2.6, 4.5), 3) for _ in range(n)]
    ref = brute(m, p, total, sc); d = dp(m, p, total, sc)
    if ref == math.inf:
        assert d is None; continue
    n_cases += 1
    worst = max(worst, abs(d[0] + sc * len([b for b in d[1] if b[1] > EPS]) - ref))
print("   feasible cases: %d | largest difference in fuel + stop cost: $%.6f" % (n_cases, worst))

# ---------------- real routes ----------------
EARTH = 3958.8
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
centre = {k: tuple(np.mean(v, axis=0)) for k, v in table.items()}; centre.update(OVERRIDES)
bestrow = {}
for r in csv.DictReader(open(STATIONS, newline="", encoding="utf-8-sig")):
    pr = float(r["Retail Price"])
    if r["OPIS Truckstop ID"] not in bestrow or pr < bestrow[r["OPIS Truckstop ID"]][0]:
        bestrow[r["OPIS Truckstop ID"]] = (pr, r)
S = [(sid, r["Truckstop Name"].strip(), r["City"].strip(), r["State"].strip(), pr) + centre[(r["State"].strip(), norm(r["City"]))]
     for sid, (pr, r) in bestrow.items() if (r["State"].strip(), norm(r["City"])) in centre]
s_lat = np.array([s[5] for s in S]); s_lon = np.array([s[6] for s in S]); s_price = np.array([s[4] for s in S])
s_xyz = xyz(s_lat, s_lon); station_tree = cKDTree(s_xyz)

def candidates(name, reverse=False, R=5, W=10):
    d = json.load(open(os.path.join(CACHE, "osrm_%s_full.json" % name)))
    c = np.array(d["routes"][0]["geometry"]["coordinates"]); c = c[::-1] if reverse else c
    lat, lon = c[:, 1], c[:, 0]
    seg = hav(lat[:-1], lon[:-1], lat[1:], lon[1:]); cum = np.concatenate([[0], np.cumsum(seg)])
    marks = np.append(np.arange(0, cum[-1], 0.5), cum[-1]); total = cum[-1]
    rlat, rlon = np.interp(marks, cum, lat), np.interp(marks, cum, lon)
    dist, idx = cKDTree(xyz(rlat, rlon)).query(s_xyz, distance_upper_bound=chord(R))
    keep = np.isfinite(dist); mm = marks[idx[keep]]; ii = np.flatnonzero(keep)
    order = np.argsort(mm, kind="stable"); mm, ii = mm[order], ii[order]
    inside = (mm > 0) & (mm < total); mm, ii = mm[inside], ii[inside]
    pp = s_price[ii]
    lo = np.searchsorted(mm, mm - W, "left"); hi = np.searchsorted(mm, mm + W, "right")
    k = np.array([lo[i] + int(pp[lo[i]:hi[i]].argmin()) == i for i in range(len(mm))], bool) if W > 0 else np.ones(len(mm), bool)
    d0, i0 = station_tree.query(xyz(lat[:1], lon[:1]))
    return [0.0] + [float(x) for x in mm[k]], [float(s_price[i0[0]])] + [float(x) for x in pp[k]], float(total), [int(i0[0])] + [int(x) for x in ii[k]], len(mm)

print("\n== 3. real routes, stations within 5 mi, only the cheapest within 10 mi kept")
print("%-11s %6s %5s | %s" % ("trip", "miles", "cand", "   ".join("$%-2d/stop: stops, fuel $, smallest gal" % s for s in (0, 5, 10, 15, 25))))
for name, rev in [("nyc_la", False), ("nyc_la", True), ("chi_hou", False), ("sea_mia", False), ("sea_mia", True), ("det_buf", False), ("dal_hou", False), ("bos_dc", False)]:
    m, p, total, ids, n_all = candidates(name, rev)
    out = []
    for sc in (0, 5, 10, 15, 25):
        t = time.perf_counter(); cost, buys = dp(m, p, total, float(sc)); ms = 1000 * (time.perf_counter() - t)
        out.append("%2d, %7.2f, %4.1f (%2.0f ms)" % (len(buys), cost, min(b for _, b in buys), ms))
    print("%-11s %6.0f %3d/%3d | %s" % (name + ("_rev" if rev else ""), total, len(m) - 1, n_all, "   ".join(out)))

for name, rev, sc in (("nyc_la", False, 10), ("nyc_la", True, 10), ("sea_mia", False, 10), ("bos_dc", False, 10)):
    m, p, total, ids, n_all = candidates(name, rev)
    cost, buys = dp(m, p, total, float(sc)); base = dp(m, p, total, 0.0)
    print("\n== %s%s at $%d per stop: %d stops, fuel $%.2f (cheapest possible $%.2f with %d stops, +%.1f%%)"
          % (name, " reversed" if rev else "", sc, len(buys), cost, base[0], len(base[1]), 100 * (cost / base[0] - 1)))
    fuel = 0.0; prev = 0.0
    for i, b in buys:
        s = S[ids[i]]
        fuel -= (m[i] - prev) / MPG; arrive = fuel; fuel += b; prev = m[i]
        print("  mile %7.1f  $%.3f  buy %5.1f gal  $%7.2f  (arrive with %4.1f, leave with %4.1f)  %s, %s %s" % (m[i], p[i], b, b * p[i], arrive, fuel, s[1][:28], s[2], s[3]))
