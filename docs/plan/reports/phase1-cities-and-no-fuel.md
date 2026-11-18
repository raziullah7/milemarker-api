# Phase 1, tasks 1.4 and 1.5: measured by the controller

Script: `plan/research/scripts/p1_checks.py`, run 18 Nov 2026 on the supplied CSV and the cached places table.

## 1.4 Places whose table rows are more than 10 miles apart

22 places, used by 106 stations. For these the rows are not averaged; the row for the county below is used.

| Place | Spread (mi) | Stations | Row to use |
|---|---|---|---|
| Orlando, FL | 48.1 | 4 | Orange |
| Austin, TX | 23.5 | 2 | Travis |
| Philadelphia, PA | 22.2 | 3 | Philadelphia |
| Jacksonville, FL | 19.2 | 12 | Duval |
| Greenville, SC | 18.1 | 4 | Greenville |
| San Antonio, TX | 17.7 | 19 | Bexar |
| Saint Paul, MN | 16.4 | 3 | Ramsey |
| Omaha, NE | 15.5 | 3 | Douglas |
| North Charleston, SC | 15.3 | 3 | Charleston |
| Fort Washington, PA | 14.9 | 0 | Montgomery |
| Trenton, NJ | 14.5 | 2 | Mercer |
| Dallas, TX | 14.3 | 13 | Dallas |
| Cincinnati, OH | 13.9 | 6 | Hamilton |
| Charleston, SC | 13.3 | 6 | Charleston |
| Houston, TX | 12.9 | 0 | Harris |
| Kissimmee, FL | 12.6 | 1 | Osceola |
| Denver, CO | 12.2 | 4 | Denver |
| Wewahitchka, FL | 11.7 | 0 | Gulf |
| Indianapolis, IN | 11.4 | 15 | Marion |
| San Francisco, CA | 10.8 | 0 | San Francisco |
| Littleton, CO | 10.1 | 0 | Arapahoe |
| Tampa, FL | 10.0 | 6 | Hillsborough |

The county chosen is the one the city is the seat of or mainly lies in (controller's own knowledge, not looked up).

## 1.5 Trips with no fuel listed along the road

Real routes from the OSRM public server, stations within 5 miles of the road.

| Trip | Miles | Stations on the road | Longest stretch without one | Plan possible |
|---|---|---|---|---|
| Los Angeles to Seattle | 1,143 | 17 | 886 miles, from mile 0 (first station: Halsey, OR) | **no** |
| San Francisco to Portland | 634 | 6 | 554 miles, from mile 0 (first station: Halsey, OR) | **no** |
| Los Angeles to San Francisco | 388 | 0 | 388 miles | yes, one fill-up at the start |
| Los Angeles to Phoenix | 377 | 11 | 134 miles | yes |
| Los Angeles to Las Vegas | 276 | 0 | 276 miles | yes |
| San Francisco to Salt Lake City | 739 | 37 | 222 miles | yes |

Confirmed: the CSV lists no station on I-5 through California, so Los Angeles to Seattle has no plan and must return `no_fuel_plan` with the gap starting at mile 0.
