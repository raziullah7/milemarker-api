"""Research script 3: what does a free routing call actually cost in time and size?

Calls the OSRM public demo server for a few US trips (1 request/second), with full and
simplified geometry, and saves the responses for the later experiments.

Usage: python -I s3_osrm.py <cache_dir>
"""
import sys, os, json, time, gzip, urllib.request

CACHE = sys.argv[1]
TRIPS = {
    "nyc_la": ((40.748, -73.997), (33.973, -118.248)),
    "chi_hou": ((41.886, -87.618), (29.765, -95.366)),
    "sea_mia": ((47.611, -122.330), (25.779, -80.198)),
    "det_buf": ((42.331, -83.046), (42.886, -78.878)),
    "dal_hou": ((32.777, -96.797), (29.765, -95.366)),
    "bos_dc": ((42.358, -71.068), (38.912, -77.018)),
}
VARIANTS = {"full": "overview=full&geometries=geojson", "simplified": "overview=simplified&geometries=geojson",
            "full_polyline6": "overview=full&geometries=polyline6"}

print("%-9s %-15s %8s %9s %9s %8s %9s" % ("trip", "geometry", "secs", "gzip KB", "raw KB", "points", "miles"))
for name, (a, b) in TRIPS.items():
    for vname, params in VARIANTS.items():
        path = os.path.join(CACHE, "osrm_%s_%s.json" % (name, vname))
        url = "https://router.project-osrm.org/route/v1/driving/%f,%f;%f,%f?%s" % (a[1], a[0], b[1], b[0], params)
        req = urllib.request.Request(url, headers={"User-Agent": "route-research/0.1", "Accept-Encoding": "gzip"})
        t = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read(); enc = r.headers.get("Content-Encoding")
        except Exception as e:
            print("%-9s %-15s ERROR %s" % (name, vname, e)); time.sleep(1.2); continue
        dt = time.perf_counter() - t
        raw = gzip.decompress(body) if enc == "gzip" else body
        open(path, "wb").write(raw)
        d = json.loads(raw)
        route = d["routes"][0]
        geom = route["geometry"]
        pts = len(geom["coordinates"]) if isinstance(geom, dict) else -1
        print("%-9s %-15s %8.2f %9.0f %9.0f %8d %9.1f" % (name, vname, dt, len(body) / 1024, len(raw) / 1024, pts, route["distance"] / 1609.344))
        time.sleep(1.2)
