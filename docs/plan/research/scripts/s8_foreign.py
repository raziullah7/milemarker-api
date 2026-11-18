"""Research script 8: detect a route that leaves the USA by testing it against the outlines of
Canada and Mexico (not the US outline, which fails on US islands and coasts).

Also checks the keyless OSRM mirror returns the same format as the main server.
Usage: python -I s8_foreign.py <cache_dir>
"""
import sys, os, json, time, urllib.request
import numpy as np

CACHE = sys.argv[1]
EARTH = 3958.8
NEW = {  # US trips that hug a border, a coast or islands, and must NOT be flagged
    "laredo_brownsville": ((27.5036, -99.5076), (25.9017, -97.4975)),
    "elpaso_delrio": ((31.7587, -106.4869), (29.3627, -100.8968)),
    "keywest_miami": ((24.5551, -81.7800), (25.7617, -80.1918)),
    "montauk_nyc": ((41.0359, -71.9545), (40.748, -73.997)),
    "seattle_blaine": ((47.6062, -122.3321), (48.9937, -122.7471)),
    "detroit_porthuron": ((42.3314, -83.0458), (42.9709, -82.4249)),
    "sandiego_calexico": ((32.7157, -117.1611), (32.6789, -115.4989)),
    "houlton_madawaska": ((46.1262, -67.8403), (47.3553, -68.3217)),
    "intlfalls_baudette": ((48.6023, -93.4041), (48.7125, -94.5999)),
    "boston_seattle": ((42.358, -71.068), (47.6062, -122.3321)),      # may cut through Canada?
    "detroit_boston": ((42.3314, -83.0458), (42.358, -71.068)),      # likely through Ontario
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "route-research/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def route(name, a, b):
    path = os.path.join(CACHE, "osrm_%s_full.json" % name)
    if not os.path.exists(path):
        open(path, "wb").write(get("https://router.project-osrm.org/route/v1/driving/%f,%f;%f,%f?overview=full&geometries=geojson" % (a[1], a[0], b[1], b[0])))
        time.sleep(1.2)
    d = json.load(open(path))
    return np.array(d["routes"][0]["geometry"]["coordinates"]), d["routes"][0]["distance"] / 1609.344


def rings(scale, code):
    d = json.load(open(os.path.join(CACHE, "ne_%s_countries.geojson" % scale), encoding="utf-8"))
    f = next(f for f in d["features"] if f["properties"].get("ADM0_A3") == code)
    polys = f["geometry"]["coordinates"] if f["geometry"]["type"] == "MultiPolygon" else [f["geometry"]["coordinates"]]
    return max((np.array(p[0]) for p in polys), key=len)


def inside(lon, lat, ring):
    x, y = lon[:, None], lat[:, None]
    x1, y1, x2, y2 = ring[:-1, 0][None], ring[:-1, 1][None], ring[1:, 0][None], ring[1:, 1][None]
    crosses = (y1 > y) != (y2 > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
    return (crosses & (x < xi)).sum(axis=1) % 2 == 1


def hav(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    h = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH * np.arcsin(np.sqrt(h))


def abroad(c, can, mex, step=2.0):
    seg = hav(c[:-1, 1], c[:-1, 0], c[1:, 1], c[1:, 0]); cum = np.concatenate([[0], np.cumsum(seg)])
    marks = np.arange(0, cum[-1], step)
    lon, lat = np.interp(marks, cum, c[:, 0]), np.interp(marks, cum, c[:, 1])
    out = np.zeros(len(marks), bool)
    north = lat > 41.6          # southernmost point of Canada is about 41.7 N
    south = lat < 32.8          # northernmost point of Mexico is about 32.7 N
    if north.any():
        out[north] = inside(lon[north], lat[north], can)
    if south.any():
        out[south] = inside(lon[south], lat[south], mex)
    run = best = 0
    for o in out:
        run = run + 1 if o else 0; best = max(best, run)
    return step * out.sum(), step * best, int(north.sum() + south.sum())


names = ["det_buf", "nyc_la", "sea_mia", "chi_hou", "bos_dc", "dal_hou"]
routes = {n: route(n, None, None) for n in names}
for n, (a, b) in NEW.items():
    try:
        routes[n] = route(n, a, b)
    except Exception as e:
        print("could not fetch", n, e)

for scale in ("50m", "10m"):
    can, mex = rings(scale, "CAN"), rings(scale, "MEX")
    print("== Natural Earth %s: Canada outline %d vertices, Mexico %d vertices, %.0f KB together as JSON"
          % (scale, len(can), len(mex), (len(json.dumps(can.round(4).tolist())) + len(json.dumps(mex.round(4).tolist()))) / 1024))
    print("   %-20s %7s %14s %12s %8s" % ("trip", "miles", "miles abroad", "longest run", "ms"))
    for n, (c, miles) in routes.items():
        t = time.perf_counter(); tot, run, tested = abroad(c, can, mex); ms = 1000 * (time.perf_counter() - t)
        print("   %-20s %7.0f %14.0f %12.0f %8.1f   (%d points near a border tested)" % (n, miles, tot, run, ms, tested))

print("\n== keyless mirror (routing.openstreetmap.de) against the main server, Dallas to Houston, full geometry")
a, b = (32.777, -96.797), (29.765, -95.366)
for host, prefix in (("https://router.project-osrm.org", "/route/v1/driving/"), ("https://routing.openstreetmap.de", "/routed-car/route/v1/driving/")):
    t = time.perf_counter()
    try:
        d = json.loads(get("%s%s%f,%f;%f,%f?overview=full&geometries=geojson" % (host, prefix, a[1], a[0], b[1], b[0])))
        r = d["routes"][0]
        print("   %-34s code %s | %.2f s | %.1f mi | %d points | geometry type %s | top-level keys %s"
              % (host, d["code"], time.perf_counter() - t, r["distance"] / 1609.344, len(r["geometry"]["coordinates"]), r["geometry"]["type"], sorted(d)))
    except Exception as e:
        print("   %-34s ERROR %s" % (host, e))
    time.sleep(1.2)
