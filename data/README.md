# Data files

Everything the API knows about the world, apart from the road itself, is in this folder.
Nothing here is fetched at run time.

| File | What it is | Source and licence |
|---|---|---|
| `fuel-prices-for-be-assessment.csv` | 8,151 rows of truck-stop fuel prices: station ID, name, address, city, state, rack ID, retail price. The only source of stations and prices. | Supplied with the assignment. Unchanged. |
| `us_cities.csv` | 29,880 US places with latitude and longitude. Used to place each station (the price file has no coordinates) and to resolve the start and finish of a trip. | [kelvins/US-Cities-Database](https://github.com/kelvins/US-Cities-Database), MIT licence. The licence text is in `us_cities.LICENSE`. Unchanged. |
| `borders.json` | The outlines of Canada and Mexico, as lists of `[lng, lat]` points under the keys `CAN` and `MEX`. Used to notice a road that leaves the USA. | Made from [Natural Earth](https://www.naturalearthdata.com/) 1:50m Admin 0 Countries, which is in the public domain: the largest outline of each country, rounded to 4 decimals. |
| `large_places.csv` | 748 US places of 50,000 people or more (columns `state,city,population`), each spelt as `us_cities.csv` spells it. Used to put the biggest city first when a name is typed with no state, and as the list a no-state misspelling is matched against. | US Census Bureau, Vintage 2023 city and town population estimates (`POPESTIMATE2023`, incorporated places with 50,000 or more), [sub-est2023.csv](https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/cities/totals/sub-est2023.csv). Public domain (US Government work). Regenerate with `uv run python scripts/extract_large_places.py sub-est2023.csv`. 51 census places the table lacks are left out. |

The recorded roads in `tests/fixtures/roads/` are real answers from the OSRM public
routing server, saved so the tests never need the network. Their geometry comes from
OpenStreetMap: © OpenStreetMap contributors, available under the Open Database License.
