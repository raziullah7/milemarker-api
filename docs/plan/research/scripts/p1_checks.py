"""Phase 1 checks: (a) cities whose table rows are far apart, (b) trips with no fuel on the road.

Usage: python -I p1_checks.py <stations.csv> <cache_dir>
"""
import csv, sys, re, os, json, time, collections, urllib.request
import numpy as np
from scipy.spatial import cKDTree

STATIONS, CACHE = sys.argv[1], sys.argv[2]
EARTH = 3958.8


def norm(s):
    s = str(s).upper().strip()
    s = re.sub(r"\bST\.?\s", "SAINT ", s); s = re.sub(r"\bFT\.?\s", "FORT ", s); s = re.sub(r"\bMT\.?\s", "MOUNT ", s)
    return re.sub(r"[^A-Z]", "", s)


def hav(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    h = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH * np.arcsin(np.sqrt(h))


def xyz(lat, lon):
    lat, lon = np.radians(lat), np.radians(lon)
    return np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])


rows = collections.defaultdict(list)
for c in csv.DictReader(open(os.path.join(CACHE, "us_cities.csv"), encoding="utf-8-sig", newline="")):
    rows[(c["STATE_CODE"], norm(c["CITY"]))].append((c["CITY"], c["COUNTY"], float(c["LATITUDE"]), float(c["LONGITUDE"])))

seen, station_keys = set(), collections.Counter()
S = []
best = {}
for r in csv.DictReader(open(STATIONS, newline="", encoding="utf-8-sig")):
    p = float(r["Retail Price"])
    if r["OPIS Truckstop ID"] not in best or p < best[r["OPIS Truckstop ID"]][0]:
        best[r["OPIS Truckstop ID"]] = (p, r)
for sid, (p, r) in best.items():
    station_keys[(r["State"].strip(), norm(r["City"]))] += 1

print("== (a) places listed more than once with rows over 10 miles apart")
far = []
for k, v in rows.items():
    if len(v) > 1:
        d = max(float(hav(a[2], a[3], b[2], b[3])) for a in v for b in v)
        if d > 10:
            far.append((d, k, v))
far.sort(reverse=True)
print("count:", len(far), "| stations affected:", sum(station_keys[k] for _, k, _ in far))
for d, k, v in far:
    print("  %-22s %s  spread %5.1f mi  stations %2d  rows: %s" % (v[0][0], k[0], d, station_keys[k],
          "; ".join("%s (%.3f,%.3f)" % (x[1], x[2], x[3]) for x in v)))

print("\n== (b) is there fuel along these roads?")
centre = {k: (float(np.mean([x[2] for x in v])), float(np.mean([x[3] for x in v]))) for k, v in rows.items()}
st = [(centre[(r["State"].strip(), norm(r["City"]))], p, r["City"].strip(), r["State"].strip())
      for sid, (p, r) in best.items() if (r["State"].strip(), norm(r["City"])) in centre]
s_lat = np.array([s[0][0] for s in st]); s_lon = np.array([s[0][1] for s in st]); s_xyz = xyz(s_lat, s_lon)
TRIPS = {"la_seattle": (("CA", "LOSANGELES"), ("WA", "SEATTLE")), "sf_portland": (("CA", "SANFRANCISCO"), ("OR", "PORTLAND")),
         "la_sf": (("CA", "LOSANGELES"), ("CA", "SANFRANCISCO")), "la_phoenix": (("CA", "LOSANGELES"), ("AZ", "PHOENIX")),
         "la_lasvegas": (("CA", "LOSANGELES"), ("NV", "LASVEGAS")), "sf_saltlake": (("CA", "SANFRANCISCO"), ("UT", "SALTLAKECITY"))}
for name, (a, b) in TRIPS.items():
    path = os.path.join(CACHE, "osrm_%s_full.json" % name)
    if not os.path.exists(path):
        (la, lo), (lb, lob) = centre[a], centre[b]
        url = "https://router.project-osrm.org/route/v1/driving/%f,%f;%f,%f?overview=full&geometries=geojson" % (lo, la, lob, lb)
        req = urllib.request.Request(url, headers={"User-Agent": "route-research/0.1"})
        open(path, "wb").write(urllib.request.urlopen(req, timeout=60).read()); time.sleep(1.3)
    d = json.load(open(path)); c = np.array(d["routes"][0]["geometry"]["coordinates"]); lat, lon = c[:, 1], c[:, 0]
    seg = hav(lat[:-1], lon[:-1], lat[1:], lon[1:]); cum = np.concatenate([[0], np.cumsum(seg)])
    marks = np.append(np.arange(0, cum[-1], 0.5), cum[-1]); total = cum[-1]
    dist, idx = cKDTree(xyz(np.interp(marks, cum, lat), np.interp(marks, cum, lon))).query(s_xyz, distance_upper_bound=2 * np.sin(5 / (2 * EARTH)))
    keep = np.isfinite(dist); mm = np.sort(marks[idx[keep]]); mm = mm[(mm > 0) & (mm < total)]
    pts = np.concatenate([[0], mm, [total]]); gaps = np.diff(pts); worst = int(gaps.argmax())
    first_bad = next((float(pts[i]) for i in range(len(gaps)) if gaps[i] > 500), None)
    where = [(round(float(m), 0), st[i][2], st[i][3]) for m, i in sorted(zip(marks[idx[keep]], np.flatnonzero(keep)))][:3]
    print("  %-12s %6.0f mi | stations on road %3d | longest gap %5.0f mi starting at mile %5.0f | plan possible: %s%s | first stations: %s"
          % (name, total, len(mm), gaps.max(), pts[worst], "no" if first_bad is not None else "yes",
             "" if first_bad is None else " (gap starts at mile %.0f)" % first_bad, where))
