# Nominatim reverse geocoding for location label and location context

Research for GitHub issue #32 (part of #4). Date of research and live tests: 2026-11-10.
Facts are tagged **[doc]** (stated on a cited primary page), **[observed]** (I ran it against the public instance), **[inferred]** (my reasoning) or **UNCONFIRMED**.
Docs read as raw HTML/wikitext (not summaries): Nominatim 5.3.3 manual (Reverse, Place Output Formats), the OSMF Nominatim usage policy, and OSM wiki pages via `action=raw`.
Live tests: 5 reverse requests and 2 search requests (7 total) to `nominatim.openstreetmap.org`, at least 1.2 s apart, `User-Agent: research-agent/1.0`, synthetic coordinates only.

## Summary and recommendations

**One reverse call is enough for both the label and the context, with two corrections to the planned mapping.**

1. **Request:** `GET https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=..&lon=..&zoom=17&addressdetails=1&extratags=1&accept-language=<ui locale>`. Add `extratags=1` (gives `ref`-like and Polish class tags) and `accept-language` (so the label follows the UI locale). Keep the ADR's 3 s timeout (observed 0.17-0.57 s). Consider `layer=address` so POIs never match (UNCONFIRMED, not tested; at `zoom=17` buildings are already excluded by the docs). [doc] [observed]
2. **A point on a road returns the road.** At `zoom=17` all 5 results were `category=highway`, `osm_type=way`; the A2 motorway point returned `type=motorway` (a point exactly on the way). Docs: reverse "finds the closest suitable OSM object" and `zoom=17` = "major and minor streets"; `18` adds buildings. [doc] [observed] **But there is no distance limit:** a deliberately rural point returned a residential street about 370 m away, and the response carries no distance field. So the backend must compute the distance between the request and the result's `lat`/`lon` and force `road_class=unknown` above a threshold (suggest 50 m, tunable; [inferred]). This adds to the ADR's >150 m GPS accuracy rule.
3. **Correction: `motorway` is the Polish expressway (S) tag, not `trunk`.** About 95% of S roads are mapped `highway=motorway`; `trunk` is used only for the few S sections that are single carriageway or have at-grade junctions. [doc: wiki Tag:highway=trunk, Pl:Znakowanie dróg w Polsce] The planned mapping still works for S roads, with no change to the table. **But `trunk` in Poland also covers main international-transit national roads that are not expressways** (TEN-T routes), so `trunk` is not proof of a limited-access road. Keep `trunk -> motorway_expressway` as the conservative (safety-first) choice and say so in the prompt text ("fast road, may be limited access"), (whether to split it into its own value is an open product question). [doc] [inferred]
4. **Mapping table (confirmed with the correction above):**

   | `category` | `type` (jsonv2) | `road_class` |
   |---|---|---|
   | `highway` | `motorway`, `motorway_link`, `trunk`, `trunk_link` | `motorway_expressway` |
   | `highway` | `primary`, `primary_link`, `secondary`, `secondary_link`, `tertiary`, `tertiary_link` | `main_road` |
   | `highway` | `unclassified`, `residential`, `living_street`, `service` | `local_street` |
   | `highway` | anything else (`track`, `path`, `footway`, `cycleway`, `pedestrian`, `road`, ...) | `unknown` |
   | other category, error, timeout, distance over threshold, accuracy over 150 m | | `unknown` |

   Add the `*_link` values for primary/secondary/tertiary too (the ticket's list omitted them). In Poland `tertiary` and `unclassified` are both used for rural roads; the Polish wiki separates them by whether two vehicles can pass without slowing, so `tertiary -> main_road` will label some ordinary village connectors as main roads (the observed `Gnieznienska` in Wrzesnia, a town street, was `tertiary`). That error is on the safe side for "handle it yourself" and acceptable. [doc] [observed]
5. **Settlement mapping (corrections):** use `address.city` -> `city`, `town` -> `town`, `village` -> `village`; **`hamlet` and `isolated_dwelling` -> `countryside`**, not `village` (my recommendation; the rural test returned `hamlet: Kaliska` and `village: Rytel` together, so `village` wins when present); none -> `countryside` only if the response is a valid in-country road, else `unknown`. Do not use `municipality` (it is the gmina, e.g. `gmina Wrzesnia`), `suburb`, `city_district`, `neighbourhood`. [doc] [observed]
   - **Caveat:** the key names the nearest named locality, not "built-up area". The A2 motorway point returned `village: Bierzglinek`, i.e. a motorway reads as `settlement=village`. Combine with `road_class` in the prompt; for `motorway_expressway`, treat settlement as weak. [observed]
   - `city` vs `town` in Poland: Nominatim derives them from `place=city|town` of the matched settlement/admin object, not from the gmina type; `city` is rare in the data (the one town tested, Wrzesnia, is `town`). Whether big cities (Warsaw, Poznan) return `city` was not tested: UNCONFIRMED. For the prompt it only matters coarsely; fall back to `town` handling if `city` is missing. [inferred]
6. **Label recipe:** `"{name or ref}, {settlement name}"`, e.g. `Autostrada Wolnosci, Bierzglinek`; fallback `display_name` split on commas, first two parts; final fallback a generic "Your location" string chosen by the UI. Details in section 3. Do not store `display_name` as the label: it carries up to 9 parts and a postcode. The label is shown to the user and stored; never sent to the model (ADR 0004).
7. **Policy fit:** a low-traffic public demo is acceptable if the app sends an identifying User-Agent, caches, stays under 1 req/s for the whole app, shows OSM attribution, and can be switched to another server without a software update (config, not code). Demo mode makes no Nominatim call (ADR 0004), which is the right default for the public deploy. Real-user GPS coordinates go to a third party, and the policy says "do not submit personal data"; this needs a line in the privacy note. [doc] See section 4.
8. **Latency:** 0.17-0.57 s per reverse call, first call slowest (cold). 3 s timeout is generous. [observed]

## 1. Which fields identify the matched object, and what gets matched

- JSONv2 fields: `osm_type` (`node|way|relation`), `osm_id`, `category` and `type` ("key and value of the main OSM tag"), `place_rank`, `importance`, `display_name`, `address`, `boundingbox`; `extratags` and `namedetails` only on request. `class` is renamed `category` in jsonv2. [doc: Place Output Formats]
- `addresstype` is present in the live output (it was in all 5 responses) but is not described in the 5.3.3 Output page I read. For roads it equals `type` (`motorway`, `tertiary`, `living_street`, `residential`). Use `category`+`type`, not `addresstype`. [observed] [doc gap]
- Reverse "works by finding the closest suitable OSM object and returning its address information"; small unnamed paths are not in the index and so cannot match; "in dense city areas it may belong to a completely different street"; it "returns exactly one result or an error when the coordinate is in an area with no OSM data coverage". [doc: Reverse]
- `zoom` (0-18, default 18): `16` major streets, `17` major and minor streets, `18` building; `15` any settlement, `14` neighbourhood, `13` village/suburb, `12` town/borough, `10` city. [doc]
  - So `zoom=17` stops at streets (buildings are not returned). At `zoom=18` a point in a built-up area would return the nearest building or house number and `category` would be `building`/`place`; the road would then be only `address.road`. [doc] [inferred; zoom 18 not run]
  - Observed at `zoom=17`: 5 of 5 results `category=highway`, `osm_type=way`.
- `layer` (default `address,poi`): `address` = house numbers, streets, settlements, admin areas; `poi` = shops, restaurants, etc. `layer=address` would exclude POIs; not tested. [doc] UNCONFIRMED effect on streets.
- Error shape: docs say only "an error"; the JSON body shape (I expect `{"error":"Unable to geocode"}`) was not observed: UNCONFIRMED. Treat any non-200, missing `category`, or an `error` key as `unknown`.

### Polish road tags

- OSM `highway=*` ranks by function/importance, not by official class, and "the Polish classification is not a copy of the official one". [doc: Key:highway; Pl:Znakowanie dróg w Polsce]
- Poland (wiki `Pl:Znakowanie dróg w Polsce`): `motorway` = motorways (A) and dual-carriageway expressways (S) with at least two lanes each way; `trunk` = most important routes not meeting `motorway` for international transit or between the largest cities, **plus single-carriageway expressways**; `primary` = main national and main voivodeship roads, in big cities main arteries; `secondary` = regional roads (voivodeship/county of distinguished importance); `tertiary` = links between smaller towns and gminas; `unclassified` = lowest through category, links villages; `residential`, `living_street` (D-40 residential zone), `service` (access roads, car parks). Mapping voivodeship roads to `secondary` or county roads to `tertiary` automatically is "strongly discouraged". [doc]
- Wiki `Tag:highway=trunk`, Poland row: ~95% of S roads are `motorway`; `trunk` is the small share that do not meet motorway requirements. [doc] The motorway page adds: `motorway` used to be only A roads and was extended to dual-carriageway S roads, and the two are told apart by `highway:class:pl` (A vs S). [doc: Tag:highway=motorway] Observed on A2: `highway:class:pl=A`, `highway:category:pl=1` in `extratags`. [observed]
- S7 itself was **not observed**: both `search` queries I tried returned empty and the one reverse guess at Bialobrzegi missed (it hit a `living_street` 80 m away, which is still a useful data point). So "S7 returns `motorway`" is from the wiki (S7 is mostly dual carriageway), not from a live response: UNCONFIRMED live. Recommended follow-up: pick a verified S-road coordinate in implementation tests.

## 2. Settlement keys in Poland

- `address` labels, rough order of significance: `municipality, city, town, village`; `city_district, district, borough, suburb, subdivision`; `hamlet, croft, isolated_dwelling`; `neighbourhood, ...`; `road`. They "roughly correspond to the classification of the OSM data according to either the place tag or the main key". [doc: Place Output Formats]
- `place=*` values: `city`, `town`, `village`, `hamlet`, `isolated_dwelling`; the wiki says a place tag should exist for every significant settlement and gives no population thresholds. [doc: Key:place] The wiki's table of place ranks lists `city` 6-9 and `town, village, hamlet` 7-10 for default search radii. [doc]
- Observed keys (Poland):
  - Wrzesnia street: `town: Wrzesnia`, `municipality: gmina Wrzesnia`, plus `neighbourhood`, `city_district`.
  - A2: `village: Bierzglinek`, `municipality: gmina Wrzesnia`.
  - Bialobrzegi: `town: Bialobrzegi`, `municipality: gmina Bialobrzegi`.
  - Rural point: `hamlet: Kaliska`, `village: Rytel`, `municipality: gmina Czersk`.
  - `municipality` is the gmina in all 4 cases and appears even for a village: never use it for settlement. `suburb` was not seen in these samples. `state` is `wojewodztwo ...`, `county` is `powiat ...`. [observed]
- Key reliability: in 4 of 4 samples exactly one of `town`/`village` was present, so the planned order works; `hamlet` appeared alongside `village`. Missing-key cases (a road between settlements) were not sampled (my one rural attempt still got a hamlet), so "none present -> countryside" is untested: UNCONFIRMED.

## 3. Building a short label

From the same response (all fields in `address`, `name` top-level, `extratags.ref`/`namedetails.ref` for numbered roads):

1. Road part: `name` if present; for numbered roads without a useful name prefer `ref` (A2/S7/DK92). Request `namedetails=1` to get `ref` ("full list of available names including ref etc." [doc]). In my A2 response with only `extratags=1`, no `ref` was returned (only `highway:class:pl`), so **do not rely on `extratags.ref`**; whether `namedetails=1` yields `ref` for this way was not run: UNCONFIRMED. Fallback to `name`.
2. Settlement part: first of `address.city`, `town`, `village`, `hamlet`.
3. Join: `"{road}, {settlement}"`; if there is no road name, settlement alone; if neither, a generic fallback.
4. Language: `accept-language` is supported; the Polish names above came back with `Accept-Language` unset, i.e. default local names. [doc: Reverse] [observed]

Example labels from the samples: `Autostrada Wolnosci, Bierzglinek`; `Kalinowa, Bialobrzegi`; `Ogrodowa, Rytel`.

## 4. Usage policy and fit

From https://operations.osmfoundation.org/policies/nominatim/ [doc]:
- "No heavy uses (an absolute maximum of 1 request per second)". The limit applies "per website/application: the sum of traffic by all your users".
- A valid HTTP Referer or User-Agent identifying the application is required; "stock User-Agents as set by http libraries will not do". The reverse docs also have an `email` parameter for larger volumes. The ADR's `Roadside/<version> (+https://github.com/eryk-poradecki/roadside)` meets this.
- Clearly display attribution; data is ODbL (`licence` is in every response).
- Use "directly triggered by the end-user" is OK "provided that your number of users is moderate". Periodic requests are bulk geocoding, "strongly discouraged".
- Apps "must make sure that they can switch the service at our request at any time (in particular, switching should be possible without requiring a software update). If at all possible, set up a proxy and also enable caching." Keep the base URL in config.
- Results should be cached; "clients sending repeatedly the same query may be classified as faulty and blocked".
- Forbidden: auto-complete, systematic queries (reverse queries in a grid), scraping `details`, reselling geocoding results, and "applications whose primary function is related to geocoding ... includes package/vehicle tracking applications".
- LLM clause: code generated by LLMs must adhere to the policy; the public API must not be built in through vibe-coding platforms, and "use of the public API is only permitted where the application developer has made a deliberate, informed decision". This ADR is that deliberate decision; cite the policy in it.
- Privacy: "Please do not submit personal data or other confidential material". A reverse call sends the user's location to OSMF. That is inherent to the feature; it should be stated in the README/privacy note and happen only after the user starts an incident. No identifiers in headers beyond the app User-Agent.
- Policy "may change without notice".

**Fit for a public demo deploy:** yes for one reverse call per created incident, with the 1 req/s ceiling enforced app-wide (a small async lock/limiter), caching by rounded coordinates (4 decimals is about 11 m; the ADR's choice of rounding is fine), a config switch for `NOMINATIM_BASE_URL`, and demo mode skipping the call. Roadside is not primarily a geocoding app, so the "vehicle tracking" exclusion does not apply: it geocodes once per incident, not continuously. Do not re-geocode on location updates in a loop. For production traffic beyond a demo, self-host or use a third-party provider (the policy lists these). Throttle on 429/403 by degrading to `unknown` with no retry storm.

## 5. Latency

5 reverse calls (all HTTP 200): total time 0.57 s (first, cold), then 0.19, 0.17, 0.23 and 0.29 s. Search calls were not timed. [observed] Small sample from one network location; the policy gives no SLA. A 3 s timeout with graceful `unknown` is right.

## 6. Example responses (trimmed; synthetic coordinates, `format=jsonv2&zoom=17&addressdetails=1&extratags=1`)

**A2 motorway, point exactly on the way** (52.3082667, 17.5911456; 0.29 s):

```json
{"osm_type":"way","osm_id":253663049,"lat":"52.3082667","lon":"17.5911456",
 "category":"highway","type":"motorway","place_rank":26,"addresstype":"motorway",
 "name":"Autostrada Wolności",
 "display_name":"Autostrada Wolności, Bierzglinek, gmina Września, powiat wrzesiński, województwo wielkopolskie, 62-303, Polska",
 "address":{"road":"Autostrada Wolności","village":"Bierzglinek","municipality":"gmina Września",
            "county":"powiat wrzesiński","state":"województwo wielkopolskie","postcode":"62-303","country_code":"pl"},
 "extratags":{"oneway":"yes","maxspeed":"140","lanes":"2","toll":"yes","highway:class:pl":"A","highway:category:pl":"1"}}
```
-> `road_class=motorway_expressway`, `settlement=village` (weak, see caveat), label `Autostrada Wolności, Bierzglinek`.

**Tertiary town street, point about 200 m from the road** (52.3376, 17.5605):

```json
{"osm_type":"way","osm_id":172805947,"lat":"52.3369986","lon":"17.5633697",
 "category":"highway","type":"tertiary","name":"Gnieźnieńska",
 "address":{"road":"Gnieźnieńska","neighbourhood":"Osiedle Krzyża Grunwaldu","city_district":"Sokołowo-Osiedle",
            "town":"Września","municipality":"gmina Września","county":"powiat wrzesiński","country_code":"pl"}}
```
-> `main_road`, `town`, `Gnieźnieńska, Września`. Note the result is about 200 m from the query and the response has no distance.

**Residential zone street** (51.6500, 20.9250; result 80 m away):

```json
{"osm_type":"way","osm_id":1271778755,"category":"highway","type":"living_street","name":"Kalinowa",
 "address":{"road":"Kalinowa","neighbourhood":"Borki Jasieńskie","town":"Białobrzegi","municipality":"gmina Białobrzegi"},
 "extratags":{"surface":"unpaved","maxspeed":"20"}}
```
-> `local_street`, `town`.

**Open countryside, snapped about 370 m to a village street** (53.7500, 17.8000):

```json
{"osm_type":"way","osm_id":916960778,"lat":"53.7513778","lon":"17.7948077",
 "category":"highway","type":"residential","name":"Ogrodowa",
 "address":{"road":"Ogrodowa","hamlet":"Kaliska","village":"Rytel","municipality":"gmina Czersk","county":"powiat chojnicki"},
 "extratags":null}
```
-> by distance rule `road_class=unknown` (370 m); settlement `village` (hamlet Kaliska ignored).

A national road (DK, `primary`) and S7 were not captured: UNCONFIRMED live.

## 7. Open questions

- S7 and a DK road were not observed live (my search queries returned nothing; the 8-request budget ran out; I also used 2 searches). Verify in the first implementation test with a checked coordinate. UNCONFIRMED.
- Does `namedetails=1` return `ref` for numbered roads? UNCONFIRMED. Needed only if the label should say `S7`/`A2`.
- Does `layer=address` change street matching at `zoom=17`? UNCONFIRMED.
- Exact error body and status for no coverage. UNCONFIRMED.
- Is `city` returned for Polish large cities? UNCONFIRMED.
- Distance threshold (suggested 50 m) and GPS accuracy rule need tuning with real tracks; the ADR's >150 m accuracy rule alone does not catch the 370 m snap seen here.
- Whether `trunk` should map to its own value (a national road that is not limited-access) rather than `motorway_expressway`: product decision, safety-conservative default kept.
- Update ADR 0004 text: add `extratags`/`accept-language`, the distance rule, and the `hamlet -> countryside` correction.

## Sources

- https://nominatim.org/release-docs/latest/api/Reverse/ (Nominatim 5.3.3 manual)
- https://nominatim.org/release-docs/latest/api/Output/
- https://operations.osmfoundation.org/policies/nominatim/
- https://wiki.openstreetmap.org/wiki/Key:highway, Tag:highway=motorway, Tag:highway=trunk, Key:place
- https://wiki.openstreetmap.org/wiki/Pl:Znakowanie_dróg_w_Polsce (the wiki redirect target of WikiProject Poland/Klasyfikacja dróg), Pl:Oznaczanie_dróg_ekspresowych_jako_highway=motorway
