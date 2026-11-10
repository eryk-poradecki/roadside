# Overpass API for nearby places (`find_nearby(category)`)

Research for GitHub issue #5. Date of research and live tests: 2026-11-10.
Facts are tagged **[doc]** (stated on a cited primary page), **[observed]** (I ran it with curl, test point Warsaw 52.2297, 21.0122) or **[inferred]**/**[unconfirmed]**.
Note: WebFetch returns model-written summaries of the pages, so exact wording was not re-checked against raw HTML.

## Summary

- Query with `nwr(around:RADIUS,LAT,LON)[tag=value];` and end with `out center tags;`. `nwr` covers nodes, ways and relations; `out center` gives ways/relations a `center` and leaves nodes with `lat`/`lon`. [doc: Overpass QL] [observed: 51 ways, all had `center`]
- Use `[out:json][timeout:25];` as the header. Send it by POST (form field `data=`). The default timeout is 180 s and the default `maxsize` 512 MiB, so declare something small. [doc]
- Send a descriptive `User-Agent` on every call. The main instance asks apps to identify themselves with `User-Agent` or `Referer`. [doc]
- Treat the public instance as unreliable: add a retry (back off 15-30 s on 429/502/504), a client timeout of about 60-90 s, and a fallback endpoint. In my tests `overpass-api.de` answered in 35-47 s and returned 502 "at capacity" for roughly half the calls. [observed]
- Do not trust HTTP 200: a server-side timeout returns **200** with `elements: []` and a `"remark": "runtime error: ..."` field. Always check `remark`. [observed]
- Sort by distance on the backend with haversine. `around` returns elements in id order, not distance order, and I found no server-side distance sort in the Overpass QL reference. [observed]
- Radius: 5 km for roadside, 25 km as the rural fallback. In Warsaw, fuel stations were 47 within 5 km and 364 within 25 km, so cap results client-side (for example nearest 10-20) after sorting. [observed]
- Towing has no settled OSM tag. Query `shop=car_repair` + `service:vehicle:towing=yes` and also `amenity=towing`, which is only a draft proposal. [doc] Expect very few results. [observed: 4 in 25 km]
- Cache by (category, rounded lat/lon, radius) for a few minutes. At 1-2 queries per request this stays far below the documented light-use thresholds, but the policy counts all of an app's users together. [doc]

## 1. Query shape and tags

Skeleton (parametrise `{lat}`, `{lon}`, `{radius}` in metres):

```
[out:json][timeout:25];
nwr(around:{radius},{lat},{lon})["shop"="tyres"];
out center tags;
```

- `around` syntax is `(around:radius,latitude,longitude)`, radius in metres. [doc: https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL]
- `nwr` is shorthand for node, way or relation. [doc: same page]
- `out center` "adds only the centre of the above mentioned bounding box to ways and relations" and the wiki warns the point "is not guaranteed to lie inside the polygon". [doc: same page]
- `out body` is the default and includes tags; `out tags` omits members and geometry; `out N` caps the count. [doc: same page]
- `out center tags;` returned `lat`/`lon` for nodes, `center` for ways, and all tags, so `name`, `opening_hours`, `phone` (or `contact:phone`) come back inside `tags`. [observed]
- `out count;` returns only totals and cannot be combined with other output. [doc] [observed: `{"nodes":"172","ways":"192","relations":"0","total":"364"}`]
- Sorting: `qt` is "roughly geographical", `asc` (default) is by id. [doc] I did not test `qt`.

Tags per category (tag pages are the owning source):

| Category | Tags | Source and caveats |
|---|---|---|
| Tyre shop / vulcanisation | `shop=tyres` | Wiki: "A shop selling tyres"; may also cover vulcanising (repair or refurbishment of tyres) in some countries. `repair=yes` marks tyre repair. [doc: https://wiki.openstreetmap.org/wiki/Tag:shop=tyres] Also consider `shop=car_repair` + `service:vehicle:tyres_repair=yes` (puncture repair, "does not imply tyres are sold") [doc: https://wiki.openstreetmap.org/wiki/Key:service:vehicle]. |
| Fuel station | `amenity=fuel` | Useful tags `brand`, `opening_hours`, `phone`/`contact:phone`, `fuel:*=yes`. The page says nothing about 24/7. [doc: https://wiki.openstreetmap.org/wiki/Tag:amenity=fuel] |
| Car repair | `shop=car_repair` | Repairs and services vehicles; repair shops that sell fuel are mapped as `amenity=fuel`. [doc: https://wiki.openstreetmap.org/wiki/Tag:shop=car_repair] Many results are specialists (electronics, bodywork), see `service:vehicle:*`. |
| Towing / breakdown | `shop=car_repair` + `service:vehicle:towing=yes`; also `amenity=towing` | `service:vehicle:towing=*` is documented as "Offers car towing services to bring vehicle to shop" [doc: https://wiki.openstreetmap.org/wiki/Key:service:vehicle]. The `shop=car_repair` page does not mention towing [doc]. `amenity=towing` with `service:towing:roadside_assistance` etc. is a **draft proposal** started 2025-05-29, not approved [doc: https://wiki.openstreetmap.org/wiki/Proposal:Towing]. I did not find an `emergency=*` tag for towing in the pages I read. |
| 24h pharmacy (optional) | `amenity=pharmacy` + `opening_hours=24/7` | The pharmacy page does not cover 24/7 or `emergency=yes` [doc: https://wiki.openstreetmap.org/wiki/Tag:amenity=pharmacy]. `24/7` is a defined `opening_hours` value, but the wiki notes disagreement whether it includes public holidays and recommends explicit forms like `Mo-Su,PH 00:00-24:00` [doc: https://wiki.openstreetmap.org/wiki/Key:opening_hours]. An exact match `="24/7"` misses those variants. |

`opening_hours` has a formal syntax and needs a parser to evaluate "open now"; the wiki lists parser libraries. [doc: Key:opening_hours] For the MVP, show the raw string.

## 2. Endpoints, limits, fair use

Main instance policy (https://dev.overpass-api.de/overpass-doc/en/preface/commons.html, and https://wiki.openstreetmap.org/wiki/Overpass_API):

- Expected maximum about 10,000 requests/day and about 1 GB/day per user. The wiki page words it as: light use is under 10,000 queries and 1 GB per day and no more than 10 minutes of total processing; for regular use "divide those numbers by 100". [doc]
- Users are identified by IP (IPv6: upper 64 bits) unless a user key is sent. Requests wait up to 15 s in a queue for a slot. Rate-limit denials are **HTTP 429**. [doc: commons]
- Resource-quota denials are **HTTP 504**. Defaults: `[timeout:180]`, `[maxsize:536870912]`. A request is admitted only if it fits within half of the remaining resources. [doc: commons] [inferred: a small declared `timeout`/`maxsize` is therefore more likely to be admitted]
- On 429 the wiki says to "pause for 30 seconds"; the commons page says to resubmit after 15 s. [doc]
- `GET https://overpass-api.de/api/status` shows your slot count and when slots free up. [doc: commons] Without a User-Agent my curl call to it got **406 Not Acceptable**; with a custom User-Agent it worked. [observed] The 406 is mentioned in the wiki only next to 429; I did not find a primary page explaining it.
- Apps should set a `User-Agent` or `Referer` that identifies the app. Also: cache, no parallel scripts, no AI app platforms such as lovable.app/netlify.app. [doc: wiki Overpass_API]
- `[out:json]` and `[timeout:N]` are the standard settings, combined as `[out:json][timeout:25];`. [doc: Overpass QL]

Instances (wiki list is "not exhaustive"; reliability is not guaranteed):

| Endpoint | Policy per source | What I saw [observed] |
|---|---|---|
| `https://overpass-api.de/api/interpreter` (FOSSGIS) | Above. Wiki: "overloaded", "don't expect high reliability". | 200 after 28-47 s for every query size, even `[timeout:1]`; about half of calls got an immediate 502 plain-text "at capacity" body. |
| `https://maps.mail.ru/osm/tools/overpass/api/interpreter` (VK Maps) | "no requests limitations" | 200 after 13-19 s for 4 of 6 queries; 2 returned nginx 504 in 0.5 s. Same Overpass 0.7.62.x. |
| `https://overpass.private.coffee/api/interpreter` | Landing page: "free and unlimited"; terms ask for a meaningful User-Agent with contact, prefer POST, and prior notice for more than 10 req/s or 10 concurrent. https://overpass.private.coffee/ | Timed out (no response in 30-60 s) on my attempts. |
| `https://overpass.kumi.systems/api/interpreter` | `https://overpass.kumi.systems/` now shows the Private.coffee page, so its status is unclear. | No response in 30-60 s; the root page itself returned 200. |
| `https://ovp.dresel.systems/api/interpreter` | 4 parallel queries per IP; free, no key [doc: wiki] | Did not answer in the time I waited. |
| `https://overpass.osm.ch/api/interpreter` | Swiss instance [doc: wiki] | Fast but regional; unsuitable for Poland. |

Contact convention: no primary page prescribes a format. Private.coffee asks for a "meaningful User-Agent with contact" [doc]. Use something like `roadside-app/0.1 (+https://example.org/contact or mailto:ops@example.org)`.

For this app: one or two small queries per request is within the "light use" figures. Keep the endpoint list in config, try the primary first, then fall back. For production traffic beyond a demo the pages suggest running your own instance. [doc: commons]

## 3. Radius, caps, sorting

- No primary source recommends a radius; these are my choices from the counts I measured in central Warsaw. [inferred]
  - 5 km (default, roadside/urban): fuel 47, car repair 87, 24/7 pharmacies 9, tyre shops 5.
  - 25 km (rural fallback, or when the 5 km result is empty): fuel 364, towing 4.
  - Retry logic: query 5 km; if empty, query 25 km (this is the "second small query").
- Smaller radius means faster and smaller responses (24.8 KB for 47 fuel stations with all tags). Use `out center tags N;` only as a safety cap (for example 200), because without a sort `N` cuts by id, not distance. [observed]
- Sorting: results came back in id order within each type (nodes first), not by distance (first six fuel results were 3472, 1916, 1737, 3279, 3339, 4667 m away). [observed] The Overpass QL reference lists `asc`, `qt` and nothing for distance. [doc]
- Do it client-side: for each element take `lat/lon` or `center.lat/center.lon`, compute haversine, sort, return the top N (say 10) with `distance_m`. At these sizes it is negligible.
- Skip elements without a usable coordinate; fall back to `brand` or the category label when `name` is missing (2 of 47 fuel stations had no `name` in the test).

## 4. Failure modes and detection

All rows below were seen against live endpoints unless marked.

| Symptom | Meaning | Detect / handle |
|---|---|---|
| HTTP 429 | Rate limit [doc: commons] (not seen) | Wait 15-30 s, retry once, then fall back. |
| HTTP 504 | Resource quota denial [doc: commons]; nginx proxy timeouts look the same [observed on VK Maps, 0.5 s, HTML body] | Retry with backoff. If persistent, lower radius/timeout. Body is HTML, not JSON. |
| HTTP 502 with plain-text "This Overpass API server is currently at capacity" | Not documented in the primary pages I read [observed: `overpass-api.de`, 0.07 s] | The body advises exponential backoff. Check `Content-Type` before `json()`. |
| HTTP 200, `elements: []`, `"remark": "runtime error: Query timed out in \"query\" at line 1 after 2 seconds."` | Query ran over its `[timeout]` [observed] | Check `"remark"` in the JSON. Treat as an error, not "nothing nearby". The remark can also accompany partial results; the Overpass QL pages I read did not describe `remark`, so this is unconfirmed beyond one observed case. "runtime error: too many requests" was not reproduced and is not defined in the pages I read; handle any `remark` starting with `runtime error`. |
| HTTP 400 with an XHTML body: `Error: line 1: parse error: ';' expected - 'out' found.` | Bad query [observed] | Do not retry. Log the query. Only relevant when building queries from user input. |
| HTTP 200, `elements: []`, no `remark` | Genuinely nothing matches (for example `amenity=towing`, 0 within 25 km) [observed] | Widen the radius or try an alternate tag. |
| Way/relation without `center` | None seen in 51 ways [observed] | `out center` is documented to add it [doc]; still guard: skip elements lacking both `lat/lon` and `center`. |
| Non-JSON or empty body, connection reset or timeout | Overloaded endpoint [observed on private.coffee, kumi, dresel] | Use a client timeout (60-90 s) and fall back to the next endpoint. |

Latency warning: with `overpass-api.de` I measured 28-47 s per query regardless of size, which is too slow for an interactive chat. Cause not documented in the primary pages [unconfirmed]; VK Maps was faster (13-19 s) but flaky. A realistic design is a background request with a "searching..." state, caching, and possibly a self-hosted instance later.

## Ready-to-run example queries

All sent with `curl -s -A 'overpass-research-client/0.1' --data-urlencode "data=$Q" <endpoint>` and Warsaw test point 52.2297, 21.0122. Replace the numbers with `{lat}`, `{lon}`, `{radius}`.

1. Tyre shop / vulcanisation (5 km). VK Maps: 200, 16.0 s, **5** nodes. `overpass-api.de` (earlier run, same query with `out center tags 50`): 200, 47 s, same 5. Adding the union below (with puncture-repair shops) returned 200 in 47.4 s.
```
[out:json][timeout:25];
nwr(around:5000,52.2297,21.0122)["shop"="tyres"];
out center tags;
```
Union variant:
```
[out:json][timeout:25];
(
  nwr(around:5000,52.2297,21.0122)["shop"="tyres"];
  nwr(around:5000,52.2297,21.0122)["shop"="car_repair"]["service:vehicle:tyres_repair"="yes"];
);
out center tags;
```

2. Fuel station (5 km). `overpass-api.de`: 200, 42.2 s, **47** (12 nodes, 35 ways, 0 ways without `center`; 45 with `name`, 29 with `opening_hours`, 4 with `phone`).
```
[out:json][timeout:25];
nwr(around:5000,52.2297,21.0122)["amenity"="fuel"];
out center tags;
```

3. Car repair (5 km). VK Maps: 200, 15.1 s, **87** (71 nodes, 16 ways, 74 with name, 34 with opening_hours, 19 with phone).
```
[out:json][timeout:25];
nwr(around:5000,52.2297,21.0122)["shop"="car_repair"];
out center tags;
```

4. Towing (25 km). `overpass-api.de`: 200, 35.3 s (after one 502), **4** (3 nodes, 1 way; all had `opening_hours` and `phone`, for example `24/7` and `+48 500 163 791`).
```
[out:json][timeout:25];
nwr(around:25000,52.2297,21.0122)["shop"="car_repair"]["service:vehicle:towing"="yes"];
out center tags;
```
   Draft tag `amenity=towing` (25 km): 200, 38.3 s, **0** results, so it is not yet usable on its own.
```
[out:json][timeout:25];
nwr(around:25000,52.2297,21.0122)["amenity"="towing"];
out center tags;
```

5. 24h pharmacy (5 km, exact `24/7`). VK Maps: 200, 19.5 s, **9** nodes, all with `name` and `opening_hours`.
```
[out:json][timeout:25];
nwr(around:5000,52.2297,21.0122)["amenity"="pharmacy"]["opening_hours"="24/7"];
out center tags;
```

Helper used above: count only, 25 km fuel (`overpass-api.de`, 200, 37.7 s, 364 total):
```
[out:json][timeout:25];
nwr(around:25000,52.2297,21.0122)["amenity"="fuel"];
out count;
```

## Not confirmed from primary sources

- Any recommended radius or result cap (these are my choices).
- What causes the 28-47 s latency and the 502 "at capacity" page on `overpass-api.de`, and whether they are intentional throttling.
- Meaning of HTTP 406 on the main instance, and the exact text of "runtime error: too many requests".
- Current status of kumi.systems and dresel.systems endpoints (no response from my network).
- Behaviour of `qt` ordering and `out N` for nearest-first retrieval (not tested).
- A standard OSM tag for roadside breakdown assistance beyond the above.

## Sources

- https://wiki.openstreetmap.org/wiki/Overpass_API (instances, usage policy, User-Agent, 429/406)
- https://dev.overpass-api.de/overpass-doc/en/preface/commons.html (rate limits, quotas, 429/504, status endpoint)
- https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL (settings, `around`, `out` modes, `nwr`)
- https://overpass.kumi.systems/ and https://overpass.private.coffee/ (Private.coffee terms and limits)
- https://wiki.openstreetmap.org/wiki/Tag:shop=tyres
- https://wiki.openstreetmap.org/wiki/Tag:shop=car_repair
- https://wiki.openstreetmap.org/wiki/Tag:amenity=fuel
- https://wiki.openstreetmap.org/wiki/Tag:amenity=pharmacy
- https://wiki.openstreetmap.org/wiki/Key:service:vehicle and https://wiki.openstreetmap.org/wiki/Key:service:vehicle:towing
- https://wiki.openstreetmap.org/wiki/Proposal:Towing (draft `amenity=towing`)
- https://wiki.openstreetmap.org/wiki/Key:opening_hours
