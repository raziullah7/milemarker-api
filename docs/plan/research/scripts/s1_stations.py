"""Research script 1: duplicates, prices and offline geocoding of the station file.

Usage: python -I s1_stations.py <stations.csv> <cache_dir>
Standard library only. Throwaway research code, not project code.
"""
import csv, sys, re, os, io, math, statistics, collections, difflib, urllib.request

STATIONS, CACHE = sys.argv[1], sys.argv[2]
CITIES_URL = "https://raw.githubusercontent.com/kelvins/US-Cities-Database/main/csv/us_cities.csv"


def fetch(url, name):
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        req = urllib.request.Request(url, headers={"User-Agent": "route-research/0.1"})
        with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
            f.write(r.read())
    return open(path, encoding="utf-8-sig", newline="").read()


def norm(s):
    s = str(s).upper().strip()
    s = re.sub(r"\bST\.?\s", "SAINT ", s)
    s = re.sub(r"\bFT\.?\s", "FORT ", s)
    s = re.sub(r"\bMT\.?\s", "MOUNT ", s)
    s = re.sub(r"[^A-Z ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def miles(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


rows = list(csv.DictReader(open(STATIONS, newline="", encoding="utf-8-sig")))

# ---------- 1. duplicates ----------
by_id = collections.defaultdict(list)
for r in rows:
    by_id[r["OPIS Truckstop ID"]].append(r)
multi = {k: v for k, v in by_id.items() if len(v) > 1}
diff_price = {k: v for k, v in multi.items() if len({x["Retail Price"] for x in v}) > 1}
diff_place = {k: v for k, v in multi.items() if len({(x["City"].strip(), x["State"].strip()) for x in v}) > 1}
diff_addr = {k: v for k, v in multi.items() if len({x["Address"].strip() for x in v}) > 1}
diff_name = {k: v for k, v in multi.items() if len({x["Truckstop Name"].strip() for x in v}) > 1}
diff_rack = {k: v for k, v in multi.items() if len({x["Rack ID"] for x in v}) > 1}
print("== duplicates")
print("ids with >1 row:", len(multi), "| differing price:", len(diff_price), "| differing city/state:", len(diff_place),
      "| differing address:", len(diff_addr), "| differing name:", len(diff_name), "| differing rack:", len(diff_rack))
spreads = sorted(max(float(x["Retail Price"]) for x in v) - min(float(x["Retail Price"]) for x in v) for v in diff_price.values())
if spreads:
    q = lambda p: spreads[min(len(spreads) - 1, int(p * len(spreads)))]
    print("price spread within an id ($): median %.3f  p90 %.3f  p99 %.3f  max %.3f" % (q(.5), q(.9), q(.99), spreads[-1]))
    print("ids with spread > $0.25:", sum(s > .25 for s in spreads), "| > $0.50:", sum(s > .5 for s in spreads), "| > $1:", sum(s > 1 for s in spreads))
print("rows per duplicated id:", collections.Counter(len(v) for v in multi.values()).most_common(8))
print("sample differing place:", [(k, sorted({(x['City'].strip(), x['State'].strip()) for x in v})) for k, v in list(diff_place.items())[:5]])
# effect of the price rule on the overall price level
lo = [min(float(x["Retail Price"]) for x in v) for v in by_id.values()]
mean = [statistics.mean(float(x["Retail Price"]) for x in v) for v in by_id.values()]
hi = [max(float(x["Retail Price"]) for x in v) for v in by_id.values()]
print("mean station price by rule: lowest %.4f | mean %.4f | highest %.4f" % (statistics.mean(lo), statistics.mean(mean), statistics.mean(hi)))
# is the file ordered in a way that hints at recency?
ids_in_order = [int(r["OPIS Truckstop ID"]) for r in rows]
print("file sorted by id:", ids_in_order == sorted(ids_in_order))
print("price decimals seen:", collections.Counter(len(r["Retail Price"].split(".")[-1]) for r in rows).most_common(5))
print("rack ids:", len({r["Rack ID"] for r in rows}), "distinct")

# ---------- 2. geocoding against the cities table ----------
cities = list(csv.DictReader(io.StringIO(fetch(CITIES_URL, "us_cities.csv"))))
print("\n== cities table")
print("rows:", len(cities), "| columns:", list(cities[0].keys()))
table = collections.defaultdict(list)
for c in cities:
    table[(c["STATE_CODE"], norm(c["CITY"]))].append((float(c["LATITUDE"]), float(c["LONGITUDE"]), c["COUNTY"]))
amb = {}
for k, pts in table.items():
    if len(pts) > 1:
        d = max(miles(a, b) for a in pts for b in pts)
        amb[k] = d
print("distinct state+city keys:", len(table), "| keys with >1 row:", len(amb),
      "| of those spread >5mi:", sum(d > 5 for d in amb.values()), "| >25mi:", sum(d > 25 for d in amb.values()))

stations = {}
for sid, v in by_id.items():
    r = min(v, key=lambda x: float(x["Retail Price"]))
    stations[sid] = r
exact = fuzzy = 0
unmatched = []
ambiguous_hits = []
by_state_names = collections.defaultdict(list)
for (st, name) in table:
    by_state_names[st].append(name)
for sid, r in stations.items():
    st, name = r["State"].strip(), norm(r["City"])
    key = (st, name)
    if key in table:
        exact += 1
        if amb.get(key, 0) > 5:
            ambiguous_hits.append((sid, r["City"].strip(), st, round(amb[key], 1), r["Address"]))
    else:
        m = difflib.get_close_matches(name, by_state_names.get(st, []), n=1, cutoff=0.85)
        if m:
            fuzzy += 1
            print("  fuzzy:", st, repr(r["City"].strip()), "->", m[0])
        else:
            unmatched.append((st, r["City"].strip(), r["Address"]))
print("\n== geocoding of", len(stations), "distinct stations")
print("exact:", exact, "| fuzzy:", fuzzy, "| unmatched:", len(unmatched))
print("stations whose city name is ambiguous within its state (rows >5 mi apart):", len(ambiguous_hits))
for a in ambiguous_hits[:25]:
    print("  ", a)
us = set("AL AZ AR CA CO CT DE FL GA ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())
un_us = [u for u in unmatched if u[0] in us]
print("unmatched in the lower 48:", len(un_us), "| elsewhere (Canada, AK, HI):", len(unmatched) - len(un_us))
print("unmatched by state:", collections.Counter(u[0] for u in unmatched).most_common(20))
for u in un_us:
    print("  ", u)

# ---------- 3. do common trip endpoints resolve? ----------
print("\n== endpoint lookup")
for q in ["New York, NY", "Los Angeles, CA", "Washington, DC", "St. Louis, MO", "Chicago, IL", "Houston, TX", "Miami, FL",
          "Seattle, WA", "San Francisco, CA", "Fort Worth, TX", "Winston-Salem, NC", "Coeur d'Alene, ID", "Boston, MA",
          "Las Vegas, NV", "Salt Lake City, UT", "New York City, NY", "Saint Paul, MN", "Mt. Vernon, IL", "Honolulu, HI", "Anchorage, AK"]:
    city, st = [x.strip() for x in q.rsplit(",", 1)]
    hit = table.get((st.upper(), norm(city)))
    print("  %-22s %s" % (q, "%d row(s) %s" % (len(hit), [(round(a, 3), round(b, 3), c) for a, b, c in hit][:3]) if hit else "NOT FOUND"))
