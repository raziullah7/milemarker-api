"""Research script 2: how far is a station's city centre from where the station really is?

Looks up a sample of well-known chain truck stops in OpenStreetMap (Nominatim, 1 request/second)
and compares that position with the city-centre position we would assign offline.

Usage: python -I s2_truth.py <stations.csv> <cache_dir> <sample_size>
"""
import csv, sys, re, os, json, math, time, random, collections, urllib.request, urllib.parse

STATIONS, CACHE, N = sys.argv[1], sys.argv[2], int(sys.argv[3])
BRANDS = [("PILOT", "Pilot Travel Center"), ("FLYING J", "Flying J"), ("LOVES", "Love's Travel Stop"), ("LOVE'S", "Love's Travel Stop"),
          ("PETRO", "Petro Stopping Center"), ("TA ", "TA Travel Center"), ("KWIK TRIP", "Kwik Trip"), ("SAPP BROS", "Sapp Bros"),
          ("ROAD RANGER", "Road Ranger"), ("BUC-EE", "Buc-ee's"), ("MAVERIK", "Maverik"), ("SHEETZ", "Sheetz"), ("QUIKTRIP", "QuikTrip"),
          ("CASEY", "Casey's"), ("LOVE S", "Love's Travel Stop")]


def norm(s):
    s = str(s).upper().strip()
    s = re.sub(r"\bST\.?\s", "SAINT ", s); s = re.sub(r"\bFT\.?\s", "FORT ", s); s = re.sub(r"\bMT\.?\s", "MOUNT ", s)
    return re.sub(r"[^A-Z]", "", s)


def miles(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


table = collections.defaultdict(list)
for c in csv.DictReader(open(os.path.join(CACHE, "us_cities.csv"), encoding="utf-8-sig", newline="")):
    table[(c["STATE_CODE"], norm(c["CITY"]))].append((float(c["LATITUDE"]), float(c["LONGITUDE"])))
centre = {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in table.items()}

seen, cands = set(), []
for r in csv.DictReader(open(STATIONS, newline="", encoding="utf-8-sig")):
    sid = r["OPIS Truckstop ID"]
    if sid in seen:
        continue
    seen.add(sid)
    key = (r["State"].strip(), norm(r["City"]))
    brand = next((b for k, b in BRANDS if k in r["Truckstop Name"].upper()), None)
    if brand and key in centre:
        cands.append((sid, brand, r["City"].strip(), r["State"].strip(), r["Address"], centre[key]))
random.seed(7)
sample = random.sample(cands, N)
print("candidates with a known brand:", len(cands), "| sampled:", len(sample))

cache_path = os.path.join(CACHE, "nominatim.json")
cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
errs, rows = [], []
for sid, brand, city, st, addr, c in sample:
    q = "%s, %s, %s" % (brand, city, st)
    if q not in cache:
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
            {"q": q, "format": "jsonv2", "countrycodes": "us", "limit": 5})
        req = urllib.request.Request(url, headers={"User-Agent": "route-research/0.1"})
        try:
            cache[q] = json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as e:
            cache[q] = {"error": str(e)}
        json.dump(cache, open(cache_path, "w"))
        time.sleep(1.1)
    res = cache[q]
    if not isinstance(res, list) or not res:
        rows.append((q, addr, None)); continue
    # several same-brand results in a city: report nearest and farthest so the range is honest
    ds = sorted(miles(c, (float(x["lat"]), float(x["lon"]))) for x in res)
    ds = [d for d in ds if d < 60] or ds[:1]
    errs.append((ds[0], ds[-1]))
    rows.append((q, addr, (round(ds[0], 1), round(ds[-1], 1), len(ds))))

hit = [r for r in rows if r[2]]
print("found in OpenStreetMap:", len(hit), "of", len(rows))
for r in rows:
    print("  %-48s %-34s %s" % (r[0][:48], r[1][:34], r[2]))
for label, idx in (("nearest match", 0), ("farthest match", 1)):
    v = sorted(e[idx] for e in errs)
    q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
    print("%s: city centre to real station, miles: median %.1f | p75 %.1f | p90 %.1f | p95 %.1f | max %.1f" % (label, q(.5), q(.75), q(.9), q(.95), v[-1]))
    print("   share within 2 mi: %.0f%% | 5 mi: %.0f%% | 10 mi: %.0f%%" % tuple(100 * sum(x <= t for x in v) / len(v) for t in (2, 5, 10)))
