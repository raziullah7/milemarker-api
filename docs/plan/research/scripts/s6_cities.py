"""Research script 6: can people's likely start/finish inputs be resolved offline, and how far is fuel from big cities?

Usage: python -I s6_cities.py <stations.csv> <cache_dir>   (standard library only)
"""
import csv, sys, re, os, math, collections

STATIONS, CACHE = sys.argv[1], sys.argv[2]
BIG = """New York, NY|Los Angeles, CA|Chicago, IL|Houston, TX|Phoenix, AZ|Philadelphia, PA|San Antonio, TX|San Diego, CA|Dallas, TX|San Jose, CA|
Austin, TX|Jacksonville, FL|Fort Worth, TX|Columbus, OH|Charlotte, NC|San Francisco, CA|Indianapolis, IN|Seattle, WA|Denver, CO|Washington, DC|
Boston, MA|El Paso, TX|Nashville, TN|Detroit, MI|Oklahoma City, OK|Portland, OR|Las Vegas, NV|Memphis, TN|Louisville, KY|Baltimore, MD|
Milwaukee, WI|Albuquerque, NM|Tucson, AZ|Fresno, CA|Sacramento, CA|Kansas City, MO|Atlanta, GA|Miami, FL|Raleigh, NC|Omaha, NE|
Minneapolis, MN|New Orleans, LA|Cleveland, OH|Tampa, FL|St. Louis, MO|Pittsburgh, PA|Cincinnati, OH|Salt Lake City, UT|Buffalo, NY|Boise, ID|
Winston-Salem, NC|Coeur d'Alene, ID|St. Paul, MN|Ft. Lauderdale, FL|Mt. Pleasant, SC|O'Fallon, MO|Wilkes-Barre, PA|McAllen, TX|Honolulu, HI|Anchorage, AK"""
BIG = [x.strip() for x in BIG.replace("\n", "").split("|")]


def norm(s):
    s = str(s).upper().strip()
    s = re.sub(r"\bST\.?\s", "SAINT ", s); s = re.sub(r"\bFT\.?\s", "FORT ", s); s = re.sub(r"\bMT\.?\s", "MOUNT ", s)
    return re.sub(r"[^A-Z]", "", s)


def miles(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


table = collections.defaultdict(list)
state_names = {}
for c in csv.DictReader(open(os.path.join(CACHE, "us_cities.csv"), encoding="utf-8-sig", newline="")):
    table[(c["STATE_CODE"], norm(c["CITY"]))].append((float(c["LATITUDE"]), float(c["LONGITUDE"])))
    state_names[c["STATE_CODE"]] = c["STATE_NAME"]
centre = {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in table.items()}
print("state codes in the cities table:", len(state_names), sorted(state_names))

seen, st = set(), []
for r in csv.DictReader(open(STATIONS, newline="", encoding="utf-8-sig")):
    k = (r["State"].strip(), norm(r["City"]))
    if r["OPIS Truckstop ID"] not in seen and k in centre:
        seen.add(r["OPIS Truckstop ID"]); st.append((centre[k], r["City"].strip(), r["State"].strip(), float(r["Retail Price"])))

missing, far = [], []
print("\n%-22s %-9s %s" % ("city", "resolved", "nearest station"))
for q in BIG:
    city, s = [x.strip() for x in q.rsplit(",", 1)]
    c = centre.get((s.upper(), norm(city)))
    if not c:
        missing.append(q); print("%-22s NOT FOUND" % q); continue
    d, name, state, price = min((miles(c, x[0]), x[1], x[2], x[3]) for x in st)
    if d > 25:
        far.append((q, round(d)))
    print("%-22s yes       %5.1f mi  %s, %s" % (q, d, name, state))
print("\nnot resolved:", missing)
print("nearest station more than 25 miles away:", far)

# every city in the table: how far to the nearest station? (coarse view of 'fuel deserts')
import random
random.seed(3)
sample = random.sample(sorted(centre), 1500)
ds = sorted(min(miles(centre[k], x[0]) for x in st) for k in sample if k[0] not in ("AK", "HI", "PR", "VI", "GU", "AS", "MP"))
q = lambda p: ds[int(p * (len(ds) - 1))]
print("\ndistance from a random lower-48 city to its nearest station: median %.1f | p90 %.1f | p99 %.1f | max %.1f mi (n=%d)" % (q(.5), q(.9), q(.99), ds[-1], len(ds)))
