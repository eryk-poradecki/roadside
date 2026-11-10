# Polish roadside safety rules and road managers (`zarządca drogi`)

Research for the safety copy and the damage-report addressee help line. Date of research: 2026-11-10.
Facts are tagged **[law]** (read in the official Dziennik Ustaw text), **[gddkia]** / **[police]** / **[rf]** (official page of that body), **[mfr]** (manufacturer document), **[inferred]** (my reading) or **UNCONFIRMED**.
Notes on method:

- Statute text comes from the official Dz.U. PDFs of the consolidated texts, fetched through the Sejm ELI API (`https://api.sejm.gov.pl/eli/acts/DU/<year>/<pos>/text.pdf`). The same API's `text.html` for the *base* acts (`DU/1997/602`, `DU/1985/60`) is the **original unamended text** and is out of date (it lacks art. 11 ust. 4a of the traffic code, for example). Do not use it.
- Consolidated texts used: Prawo o ruchu drogowym (PoRD) = Dz.U. 2024 poz. 1251; Ustawa o drogach publicznych (UDP) = Dz.U. 2025 poz. 889; equipment regulation = Dz.U. 2024 poz. 502; sign regulations = Dz.U. 2019 poz. 2310 and 2311.
- I grepped the 2025-2026 acts that amend PoRD (Dz.U. 2025 poz. 820, 1006, 1676, 1734, 1843, 1872; 2026 poz. 180, 982, 1466) and found none touching art. 2 pkt 3-4, 11, 31, 49 or 50 of PoRD. For UDP, the only later amendments (Dz.U. 2026 poz. 815 and 982) do not touch art. 4, 18 or 19. This is a keyword check, not a legal opinion. The sign regulations have later amendments (2021, 2022, 2026) that I did not re-read.
- WebFetch returns model-written summaries of web pages, so quotes from web pages (not PDFs) were not re-checked against raw HTML, except where marked "read raw".

## Summary (facts a copywriter needs)

- **Hazard lights.** On a motorway or expressway a stopped vehicle must be signalled "w każdym przypadku": hazard lights plus triangle 100 m behind. On other hard-surface roads signalling is required only if the car stops on the carriageway where stopping is prohibited (built-up area), or on the carriageway where prohibited / on the shoulder where the car is not visible from a sufficient distance (outside built-up area). PoRD art. 50 ust. 1-2. [law]
- **Triangle distances.** Motorway/expressway: 100 m behind the vehicle, on the carriageway or shoulder "odpowiednio do miejsca unieruchomienia pojazdu". Other roads outside built-up area: 30-50 m behind, plus hazard lights. Built-up area: hazard lights; the triangle goes "za pojazdem lub na nim, na wysokości nie większej niż 1 m", and the text reads as a fallback for cars without hazard lights (see section A.2 for the ambiguity). PoRD art. 50 ust. 2. [law]
- **Triangle is mandatory equipment** of every motor vehicle except single-track motorcycles. **Fire extinguisher is mandatory** of every motor vehicle except motorcycles, placed "w miejscu łatwo dostępnym". Equipment regulation § 11 ust. 1 pkt 13-14. [law]
- **First aid kit is not mandatory in a private car.** It is required in buses, taxis, lorries carrying people outside the cab and driving-school vehicles (§ 18, 24, 40, 43). A Ministry of Infrastructure draft would require it for M1 cars first registered after 31 March 2027; only press reports of the draft found, so treat as **UNCONFIRMED / not law**.
- **Reflective vest is not mandatory equipment** (no vest in § 11; no PoRD article requires one for drivers). There is **no "art. 63a"** about vests (PoRD art. 63 is about carrying passengers). What the law does require: pedestrians moving on a road after dusk outside a built-up area must use reflective elements (PoRD art. 11 ust. 4a), and people working on a road must (art. 41). Police say a person outside a car is legally a pedestrian. GDDKiA and police nevertheless tell drivers to put on a vest before leaving a car on a motorway. [law] [police] [gddkia]
- **Motorway/expressway breakdown, official advice.** Move onto the emergency lane if possible, hazard lights, vest, triangle at 100 m, leave the car on the passenger side, go behind the barriers (or use the emergency exit in noise screens) and wait there, "poza jezdnią i pasem awaryjnym". Do not repair or change a wheel on the emergency lane. [gddkia] [police]
- **Whom to call.** 112 for emergencies. 19 111 is GDDKiA's round-the-clock *road information* line for national roads and is explicitly **not** an emergency number, although GDDKiA and police also list it for calling road assistance. Roadside alarm columns (`kolumna alarmowa`) reach the GDDKiA traffic management centre (CZR). [gddkia] [police]
- **Towing on a motorway is banned** except by vehicles designed for towing, to the nearest exit or service area (PoRD art. 31 ust. 2 pkt 5). Towing speed limit 30 km/h built-up, 60 km/h outside (art. 31 ust. 1 pkt 1). [law]
- **Walking on a motorway.** Motorways and expressways are "przeznaczone tylko do ruchu pojazdów samochodowych" (PoRD art. 2 pkt 3-4; UDP art. 4 pkt 10-11). Official advice is to stay behind the barrier and call for help, not to walk to a fuel station. [law] [police]
- **EVs.** Manufacturers say do not tow with drive wheels on the ground; use a flatbed or lift the drive axle (Nissan LEAF 2023 UK manual, VW ID.3 rescue card). A flat 12 V battery is a separate problem: jump-start gives power to the 12 V system only and does not charge the traction battery (Nissan). [mfr]
- **Pothole damage.** No statute obliges you to call the police. Police advise calling 112; officers record the damage and send a `notatka` to the road manager. The Financial Ombudsman lists photos, witness statements and a police or `straż miejska` note as useful evidence and says liability rests on art. 415 k.c. (fault). [police] [rf]
- **Who manages roads (UDP art. 19 ust. 2).** National: GDDKiA (Generalny Dyrektor Dróg Krajowych i Autostrad). Voivodeship: `zarząd województwa`. County: `zarząd powiatu`. Municipal: `wójt (burmistrz, prezydent miasta)`. [law]
- **Exceptions.** Paid motorways run by a concessionaire are managed by that company, except some tasks that stay with GDDKiA (art. 19 ust. 3). In cities with county rights the city president manages all public roads except motorways and expressways (art. 19 ust. 5). [law]
- **Reading road signs.** Only national and voivodeship roads get numbers on road signs: "Numerów dróg pozostałych kategorii nie umieszcza się na znakach drogowych." National road numbers: red background, white digits (E-15a). Voivodeship: yellow background, black digits (E-15b/e/h). `A` motorway and `S` expressway: red. E-numbers (E-16, green) are international routes. Colours of E-15b and E-15c/d are visible only in the regulation's figures, not in its text. [law]
- **Damage claims at GDDKiA.** One page: "Zgłaszanie szkód z ubezpieczenia OC zarządcy drogi" (link in section B.4). It says nothing specific about potholes. [gddkia]

## A. Roadside safety

### A.1 Hazard lights (`światła awaryjne`)

- PoRD art. 50 ust. 1: "Kierujący pojazdem jest obowiązany sygnalizować postój pojazdu silnikowego lub przyczepy z powodu uszkodzenia lub wypadku:" [law, Dz.U. 2024 poz. 1251]
  1. "na autostradzie lub drodze ekspresowej - w każdym przypadku";
  2. on other hard-surface roads: (a) outside built-up area "w razie postoju na jezdni w miejscu, w którym jest to zabronione, a na poboczu, jeżeli pojazd nie jest widoczny z dostatecznej odległości"; (b) in built-up area "w razie postoju na jezdni w miejscu, w którym zatrzymanie jest zabronione".
- Art. 50 ust. 3: signalling "obowiązuje przez cały czas postoju pojazdu".
- If the car has no hazard lights, art. 50 ust. 2 requires position lights instead ("a jeżeli pojazd nie jest w nie wyposażony, należy włączyć światła pozycyjne").
- So the law does not say "always switch on hazards when stopped with a breakdown" on ordinary roads: it ties the duty to where the car stands. [inferred from the text] A car stopped legally at the kerb in a town is outside the duty, though using hazards is sensible.
- Related duties: art. 46 ust. 1 (stop only where the car is visible and not a danger), art. 46 ust. 3 (outside built-up areas the car should stand off the carriageway "jeżeli to tylko możliwe"), art. 49 ust. 3 (below). [law]
- Art. 49 ust. 3: "Zabrania się zatrzymania lub postoju pojazdu na autostradzie lub drodze ekspresowej w innym miejscu niż wyznaczone w tym celu. Jeżeli unieruchomienie pojazdu nastąpiło z przyczyn technicznych, kierujący pojazdem jest obowiązany usunąć pojazd z jezdni oraz ostrzec innych uczestników ruchu." [law] (the "ostrzec" part is what art. 50 specifies)
- PoRD says nothing about V16 beacons or other devices in place of the triangle; art. 50 names only "ostrzegawczy trójkąt odblaskowy". [law] I did not research EU/foreign V16 rules; treat as out of scope.

### A.2 Warning triangle (`trójkąt ostrzegawczy`)

Art. 50 ust. 2 [law]:

| Place | Required signalling | Wording |
|---|---|---|
| Motorway / expressway | hazard lights + triangle 100 m behind | "włączenie świateł awaryjnych ... umieszczenie ostrzegawczego trójkąta odblaskowego w odległości 100 m za pojazdem; trójkąt ten umieszcza się na jezdni lub poboczu, odpowiednio do miejsca unieruchomienia pojazdu" |
| Other roads, outside built-up area | triangle 30-50 m behind + hazard lights | "umieszczenie w odległości 30-50 m za pojazdem ostrzegawczego trójkąta odblaskowego i włączenie świateł awaryjnych" |
| Built-up area | hazard lights; triangle behind or on the car, at most 1 m high | "przez włączenie świateł awaryjnych, a jeżeli pojazd nie jest w nie wyposażony, należy włączyć światła pozycyjne i umieścić ostrzegawczy trójkąt odblaskowy za pojazdem lub na nim, na wysokości nie większej niż 1 m" |

- **Hazard lights and the triangle in a built-up area.** The sentence puts the triangle inside the "if the car has no hazard lights" branch, so the text reads as: hazard lights suffice if the car has them. The statute does not say this in so many words, so the reading is [inferred]. Police pages quote the same wording and do not state a different rule (KSP Wydział Ruchu Drogowego, 14.03.2023, https://ksp.policja.gov.pl/wrd/aktualnosci/118448,JAK-SYGNALIZOWAC-POSTOJ-na-drodze.html; Policja Zachodniopomorska, undated, https://zachodniopomorska.policja.gov.pl/sz/aktualnosci/ruch-drogowy/warto-wiedziec/73735,Jak-prawidlowo-sygnalizowac-postoj-pojazdu-wynikajacy-z-awarii.html). Other police pages (Łódź, Środa Śląska, Elbląg) say hazards plus triangle on the roadway; I did not open them. For the app, "hazard lights first, triangle too if you can do it safely" is the safe wording; do not state that the triangle is *forbidden* or *optional* with legal certainty.
- Outside built-up areas, signalling is required only in the cases listed in A.1, but when it is required both triangle and hazards are required. [law]
- **Carrying a triangle is mandatory**: equipment regulation (Rozporządzenie Ministra Infrastruktury z 31.12.2002 r. w sprawie warunków technicznych pojazdów oraz zakresu ich niezbędnego wyposażenia, consolidated Dz.U. 2024 poz. 502) § 11 ust. 1: "Pojazd samochodowy wyposaża się: ... 13) w trójkąt do ustawiania na drodze, przeznaczony do ostrzegania o obecności unieruchomionego pojazdu; przepisu nie stosuje się do motocykla jednośladowego" [law]. Authority: PoRD art. 66 ust. 5.
- Fine: Policja Pomorska says failing to place the triangle on a motorway can cost 300 zł and 1 penalty point (https://pomorska.policja.gov.pl/pom/informacje/wiadomosci/135942,Bezpieczna-autostrada-Twoje-zycie-Twoja-odpowiedzialnosc.html, 19.08.2024) [police, WebFetch summary]. The legal basis (fine schedule) was not checked: **UNCONFIRMED**.
- Roadside hectometre posts every 100 m help to measure the 100 m (same police page; Policja Pabianice 2026, below).

### A.3 Reflective vest (`kamizelka odblaskowa`, `elementy odblaskowe`)

- **Not mandatory equipment.** § 11 ust. 1 of the equipment regulation (Dz.U. 2024 poz. 502) has no vest item, and the full text of PoRD (Dz.U. 2024 poz. 1251) contains no occurrence of "kamizelk" (checked with grep on the PDF text). The two 2024 amending regulations (Dz.U. 2024 poz. 983 and 1417, each a page or so) do not mention trójkąt, gaśnica or apteczka. [law, keyword check] Police state it as advice: "Załóż kamizelkę odblaskową - warto ją mieć" (Policja Pomorska, 19.08.2024). [police]
- **There is no "art. 63a" on vests.** PoRD art. 63 is "Przewóz osób ...". [law]
- **When reflective elements are legally required** [law, Dz.U. 2024 poz. 1251]:
  - Art. 11 ust. 4a: "Pieszy poruszający się po drodze po zmierzchu poza obszarem zabudowanym jest obowiązany używać elementów odblaskowych w sposób widoczny dla innych uczestników ruchu, chyba że porusza się po drodze dla pieszych, drodze dla pieszych i rowerów lub drodze dla rowerów." Not applicable in a `strefa zamieszkania` (art. 11 ust. 5).
  - Art. 41: "Osoba wykonująca roboty lub inne czynności na drodze jest obowiązana używać w sposób widoczny dla innych uczestników ruchu elementów odblaskowych odpowiadających właściwym warunkom technicznym."
  - Art. 12 ust. 6 pkt 2: columns of pedestrians longer than 20 m in poor visibility (not relevant for a driver).
  - Art. 43 ust. 2 (reflective elements for children up to 15 after dusk) was **repealed** in the 2024 consolidated text ("(uchylony)"). Older web pages still quote it.
- A driver who leaves a car is a "pieszy" for the police: "kodeks drogowy traktuje osobę, która znajduje się na drodze poza pojazdem, jako pieszego" (Informacyjny Serwis Policyjny, 20.08.2020, archived, https://isp.policja.pl/isp/aktualnosci/15477,Autostrada-jak-zachowac-sie-w-przypadku-awarii-kolizji-lub-wypadku.html). [police] So art. 11 ust. 4a plausibly covers a stranded driver walking along a road outside a built-up area after dusk; whether a person *standing* counts as "poruszający się" is **UNCONFIRMED**. There is no rule requiring a vest "when leaving a vehicle on a motorway" in the texts I read.
- No rule found that makes a vest obligatory on motorways. GDDKiA's own advice does list it: "Włącz światła awaryjne, załóż kamizelkę odblaskową i wystaw trójkąt ostrzegawczy 100 m od pojazdu." (GDDKiA, "Droga to nie tor wyścigowy. Pas awaryjny to nie parking", 18.06.2025, https://www.gov.pl/web/gddkia/droga-to-nie-tor-wyscigowy-pas-awaryjny-to-nie-parking). [gddkia]
- I found no primary source for a pending requirement to carry a vest. Press articles from 2026 only discuss a first aid kit (A.6).

### A.4 Motorway / expressway breakdown, official guidance

GDDKiA, 18.06.2025 (https://www.gov.pl/web/gddkia/droga-to-nie-tor-wyscigowy-pas-awaryjny-to-nie-parking) [gddkia]:

- Stop only at designated parking areas, exceptions: "awaria pojazdu", police or other authorised stop, "sytuacja awaryjna na drodze (np. wypadek)". "Poza powyższymi przypadkami pasem awaryjnym nie wolno się poruszać ani na nim zatrzymywać."
- Breakdown: "Włącz światła awaryjne, załóż kamizelkę odblaskową i wystaw trójkąt ostrzegawczy 100 m od pojazdu. Przestaw, o ile to możliwe, samochód na pas awaryjny, a jeżeli nie jest to możliwe, ustaw trójkąt ostrzegawczy i oddal się od pojazdu."
- "Szybko wezwij pomoc, dzwoniąc pod numer alarmowy 112, numer Infolinii drogowej GDDKiA 19 111 lub udając się do najbliższej kolumny alarmowej i powiadamiając o zajściu dyżurnego w Centrum Zarządzania Ruchem."
- "Na pomoc czekaj po prawej stronie drogi poza jezdnią i pasem awaryjnym. Jeśli wzdłuż jezdni są ekrany przeciwhałasowe, skorzystaj z wyjścia ewakuacyjnego."
- Rejoining: build speed on the emergency lane first and wait for a safe gap.
- The page says nothing about passenger-side exit, repairs or tyre changes.

Police (Policja Pabianice, 7 Aug 2026, https://pabianice.policja.gov.pl/epa/informacje/122092,Niebezpieczna-sytuacja-na-S-14.html, read raw) [police]:

- "zjedź najszybciej jak to możliwe na pas awaryjny i włącz światła awaryjne"; "załóż kamizelkę odblaskową"; "opuść pojazd od strony pasażera i przejdź za barierki wraz z pasażerami. Nie zostawiaj nikogo w pojeździe".
- Triangle 100 m, use "słupki hektometryczne zlokalizowane co 100 m". (The page says "przed pojazdem", which contradicts art. 50 "za pojazdem"; treat as a typo and quote the statute.)
- "nie próbuj na własną rękę naprawiać samochodu ani wymieniać koła na pasie awaryjnym".
- "wezwij pomoc drogową, korzystając z numeru alarmowego 112 lub z ogólnokrajowego numeru informacyjnego 19 111 zarządzanego przez Generalną Dyrekcję Dróg Krajowych i Autostrad"; read the location from the white-red hectometre posts (road, kilometre, metre).

Policja Pomorska (19.08.2024) [police]: "przebywaj cały czas za barierkami ochronnymi"; give location (GPS or marker posts); "Służby same ustalą Twoją lokalizację, jeśli zadzwonisz z budki z telefonem alarmowym"; return to the car only when the services have secured the place; only tow trucks may tow on motorways and expressways.

ISP (20.08.2020, archived): check the mirrors before getting out; vest, then triangle 100 m "odpowiednio do miejsca jego unieruchomienia"; "Zejdź z jezdni i na poboczu, najlepiej za barierkami oczekuj na pomoc; ogranicz do niezbędnego minimum czynności przy unieruchomionym pojeździe". [police]

Related law: art. 45 ust. 1 pkt 3 forbids "wysiadania bez upewnienia się, że nie spowoduje to zagrożenia bezpieczeństwa ruchu lub jego utrudnienia". [law]

**What 19 111 is.** GDDKiA: "numer 19 111 jest dla kierowców źródłem niezawodnej informacji o sytuacji na drogach krajowych", "19 111 nie jest numerem alarmowym", "W sytuacjach nagłych, wymagających interwencji służb ratowniczych, należy wybrać numer 112." When reporting, give the road number, location from the km posts ("pikietaż ze słupków drogowych") and direction. Not covered: other managers' roads, toll amounts. ("Numer 19 111 - niezawodny partner każdego kierowcy", 03.08.2023, https://www.gov.pl/web/gddkia/numer-19-111---niezawodny-partner-kazdego-kierowcy.) A second GDDKiA page says it runs 24/7 and that detailed road conditions on national roads are given there (https://www.gov.pl/web/gddkia/informacja-drogowa---19-111). The GDDKiA page said nothing about the "0" prefix, though an older summary did; **UNCONFIRMED**. [gddkia]

**Roadside emergency phones.** GDDKiA (2025) mentions "kolumna alarmowa" reaching the traffic management centre. Whether every motorway/expressway section still has working columns: **UNCONFIRMED**.

**Hard shoulder name.** PoRD does not define "pas awaryjny" (word absent from its text); GDDKiA and police use it. On expressways without one, the `pobocze` is the standing place. [inferred]

### A.5 Tyre change, jump-start, towing/pushing, walking

- **Tyre change / repair on the emergency lane**: police advise against it: "nie próbuj na własną rękę naprawiać samochodu ani wymieniać koła na pasie awaryjnym" (Pabianice, 2026). GDDKiA's page (2025) does not mention it. No statute found that bans it as such. [police]
- **Jump-start** on a hard shoulder: no official guidance found; the general "do not repair, call for help, wait behind the barrier" applies. **UNCONFIRMED** as a specific rule.
- **Towing on a motorway** (PoRD art. 31 ust. 2 pkt 5) [law]: "Zabrania się holowania: ... na autostradzie, z wyjątkiem holowania przez pojazdy przeznaczone do holowania do najbliższego wyjazdu lub miejsca obsługi podróżnych." The rule names `autostrada` only; expressways are not mentioned in this item. The police say only tow trucks may tow on motorways *and* expressways (Pomorska 2024) [police], which goes beyond the text I read.
- Other towing conditions (art. 31 ust. 1): max 30 km/h in built-up area, 60 km/h outside; low beams on; towed car carries a triangle at the rear left or yellow flashing signals; distance max 3 m rigid, 4-6 m flexible, marked. [law]
- **Pushing a car** on a motorway: no specific rule found. It would conflict with art. 49 ust. 3 (stopping place) and with pedestrian rules. **UNCONFIRMED.**
- **Pedestrians on motorways.** PoRD art. 2 pkt 3: "autostrada ... przeznaczoną tylko do ruchu pojazdów samochodowych"; pkt 4 the same for `droga ekspresowa`. UDP art. 4 pkt 11 lit. a: motorway carriageways "przeznaczone wyłącznie do ruchu pojazdów samochodowych"; art. 3 pkt 2 classes them as "drogi o ograniczonej dostępności". [law] I did not find a PoRD article that says in words "pedestrians may not enter"; the ban follows from the designation and the signs D-9/D-7 (Dz.U. 2019 poz. 2310 § 48 describes them as marking the start of a motorway/expressway). The penalty provision (Kodeks wykroczeń) was not checked: **UNCONFIRMED**.
- **Stranded driver walking to a fuel station**: official advice is the opposite, stay behind the barrier and call 112/19 111 or use the alarm column. Real case: Pabianice police, 7 Aug 2026: an 80-year-old driver without a phone walked on the S14 carriageway; officers brought him back to his car. [police] Whether walking *behind* the barrier along an expressway is an offence: **UNCONFIRMED**.

### A.6 Fire extinguisher and first aid kit

- **Fire extinguisher: mandatory** for every motor vehicle except a motorcycle. § 11 ust. 1 pkt 14: "w gaśnicę umieszczoną w miejscu łatwo dostępnym w razie potrzeby jej użycia; przepisu nie stosuje się do motocykla". [law, Dz.U. 2024 poz. 502] Police pages agree (e.g. https://rawa-mazowiecka.policja.gov.pl/erw/informacje/70311,Obowiazkowe-wyposazenie-samochodu.html, found by search, not opened).
- **First aid kit (`apteczka doraźnej pomocy`): not mandatory in a private car.** § 11 ust. 1 has no kit; the regulation lists it for buses (§ 18), taxis (§ 24), lorries carrying people outside the cab (§ 40) and driving-school vehicles (§ 43). [law] Police pages: "Apteczka nie jest wymagana, ... ale ... dobrze jest" to have one (KMP Koszalin, per search summary, not opened). [police]
- **Draft change (not law)**: RMF24, 4 Aug 2026, quotes the Ministry of Infrastructure: the draft covers M1 cars "po raz pierwszy zarejestrowane w Polsce po 31 marca 2027 roku"; contents not specified (https://www.rmf24.pl/fakty/polska/news-apteczka-w-autach-osobowych-coraz-blizej-mamy-komentarz-mini,nIdn,1012511). I did not find the draft on legislacja.gov.pl / the ministry's work list: **UNCONFIRMED**, and it must not be presented as in force. Press also reported a 1 June 2026 date, which the ministry corrected (auto-swiat, found by search, not opened).

### A.7 Electric vehicles out of charge

- **Do not tow with drive wheels on the road.** Nissan LEAF 2023 UK owner's manual, section 10.3.4.3: "NISSAN recommends that your vehicle be towed with the driving (front) wheels off the ground or that the vehicle be placed on a flatbed truck" and "Never tow with the front wheels on the ground or four wheels on the ground (forward or backward) as this may cause serious and expensive damage to the motor." (https://www.nissan.co.uk/owners/car-repair/car-owner-manual/manuals/iom/leaf/0ze1/e0/2023/towing-recommended-by-nissan-1.shtml) [mfr, WebFetch summary]
- VW ID.3 rescue card (karta ratownicza, 5-door 2019, Polish), section 8 "Holowanie/transport/magazynowanie": "Nie holować samochodu za oś napędową (oś tylna), lecz na lawecie z powierzchnią do transportu samochodów albo z podniesioną osią napędową." and "ID.3 nie posiada ucha do holowania z tyłu samochodu." (https://www.volkswagen.pl/idhub/content/dam/onehub_pkw/importers/pl/serwis-i-akcesoria/wypadek-lub-awaria/karta-ratownicza/karty/id_3_5dr_2019_ds_pl.pdf) [mfr, read raw from the PDF text]
- **Tesla**: the owner's manual pages returned HTTP 403 to me; Tesla's stance (flatbed, no wheel on the ground) is **UNCONFIRMED** from a primary source.
- **12 V battery is a separate issue.** Nissan LEAF 2023 manual, section 10.3.3: a flat 12 V battery stops the power switch moving from OFF; jump starting "provides power to the 12-volt system"; "Jump starting does not charge the Li-ion battery"; "The vehicle can not be driven until the Li-ion battery is charged"; "The LEAF cannot be used as a booster vehicle." (https://www.nissan.co.uk/owners/car-repair/car-owner-manual/manuals/iom/leaf/0ze1/e0/2023/jump-starting-1.shtml) [mfr, WebFetch summary]. Other makes may differ; the app copy should say "check your manual".
- Polish law on EV towing: nothing specific found; the general towing rules in art. 31 apply.

### A.8 Pothole damage

- **No duty to call the police** in the statute for a pothole with no injury: art. 44 ust. 2 requires police and medical services only "jeżeli w wypadku jest zabity lub ranny". [law] Calling is advice, not a legal requirement. [inferred]
- **Police advice** (KMP Legnica, 08.02.2023, archived, https://legnica.policja.gov.pl/dle/aktualnosci/bieza/87716,Wjechales-dziure-i-uszkodziles-auto-i-co-teraz.html) [police]: call "numer alarmowy 112"; the patrol goes to the spot; "Funkcjonariusze ustalają okoliczności zdarzenia. Sprawdzają i odnotowują uszkodzenia pojazdu."; "Policjanci sporządzają z takiej czynności notatkę i przesyłają do zarządcy drogi."; the injured party may claim from "zarządcy drogi lub ubezpieczyciela". If the hole is a danger the police inform the road manager so it can be secured.
- **Financial Ombudsman (Rzecznik Finansowy), 9 May 2024** (https://archiwum.rf.gov.pl/2024/05/09/szkody-w-pojazdach-zwiazane-z-ubytkami-dziurami-w-drodze-oraz-dziko-zyjacymi-zwierzetami-praktyczne-odpowiedzi-na-pojawiajace-sie-problemy/, read raw) [rf]:
  - First identify the road manager. The injured party must document the damage: witness statements with contact data; "protokołu/notatki policji lub straży miejskiej z miejsca zdarzenia"; "dokumentacji zdjęciowej lub nagranie telefonem miejsca zdarzenia oraz powstałych uszkodzeń"; an invoice or repair estimate (the claim exists even before repair).
  - Claim to the manager's liability insurer, or directly to the manager if there is no policy (these policies are voluntary).
  - Liability is based on art. 415 k.c. (fault), so the claimant has to show wrongful act, damage and causation. Insurers who refuse must give reasons; complain to the insurer, then to the Rzecznik Finansowy.
  - The page lists a manager's duties under UDP art. 20 (inspections, interventions, signs).
- UDP art. 20 pkt 10 and 11 (periodic checks, interventions and securing works) are the statutory duties behind this. [law]
- Limitation period for such claims: not checked, **UNCONFIRMED** (do not state a number in copy).

## B. Road administration (`zarządca drogi`)

### B.1 Who manages which category

UDP (Dz.U. 2025 poz. 889) [law]:

- Art. 2 ust. 1: categories are `drogi krajowe`, `drogi wojewódzkie`, `drogi powiatowe`, `drogi gminne`.
- Art. 5 ust. 1 pkt 1: national roads include "autostrady i drogi ekspresowe oraz drogi leżące w ich ciągach do czasu wybudowania".
- **Art. 19 ust. 2**: "Zarządcami dróg, z zastrzeżeniem ust. 3, 5, 5a i 8, są dla dróg: 1) krajowych - Generalny Dyrektor Dróg Krajowych i Autostrad; 2) wojewódzkich - zarząd województwa; 3) powiatowych - zarząd powiatu; 4) gminnych - wójt (burmistrz, prezydent miasta)."
- Art. 19 ust. 1: the manager is the "organ administracji rządowej lub jednostki samorządu terytorialnego, do którego właściwości należą sprawy z zakresu planowania, budowy, przebudowy, remontu, utrzymania i ochrony dróg".
- Art. 18: GDDKiA has regional branches (`oddziały`) per voivodeship (ust. 2-3); regional branches for particular motorways/expressways spanning more than one voivodeship are possible (ust. 3a). GDDKiA's own page lists the branches (https://www.gov.pl/web/gddkia/kto-jest-zarzadca-tej-drogi2, 14.08.2023). [law] [gddkia]
- **Paid motorways, art. 19 ust. 3**: GDDKiA manages a motorway built under the motorway act "do czasu przekazania jej, w drodze porozumienia, spółce, z którą zawarto umowę o budowę i eksploatację albo wyłącznie eksploatację autostrady. Spółka pełni funkcję zarządcy autostrady płatnej na warunkach określonych w umowie ..., z wyjątkiem zadań, o których mowa w art. 20 pkt 1, 8, 17 i 20, które wykonuje Generalny Dyrektor Dróg Krajowych i Autostrad." [law]
  - GDDKiA's list (16.08.2023, https://www.gov.pl/web/gddkia/ponad-1800-km-autostrad-wiekszosc-bez-oplat): concessionaires on A1 Gdańsk (Rusocin) - Toruń (Gdańsk Transport Company S.A., to 2039), A2 Nowy Tomyśl - Konin (Autostrada Wielkopolska S.A., to 2037), A2 Świecko - Nowy Tomyśl (Autostrada Wielkopolska II S.A., to 2037), A4 Kraków (Balice) - Katowice (Stalexport Autostrada Małopolska S.A., to 2027). GDDKiA runs A2 Konin - Stryków and A4 Wrocław - Sośnica. [gddkia] **The list is from 2023; check before use.** A later search result says GDDKiA takes over A4 Katowice-Kraków on 16 March 2027, not verified on the page: **UNCONFIRMED**.
  - Practical consequence for the app: on a concession section the damage-report addressee may be the concessionaire, not GDDKiA. [inferred]
- Art. 19 ust. 8: a `drogowa spółka specjalnego przeznaczenia` can act as manager of a national road under its own act. [law]
- Art. 19 ust. 5a: a `związek metropolitalny` board can manage national roads (not motorways/expressways) and voivodeship roads. [law]
- **Names of the units.** The statute names the *organ* (`zarząd województwa`, `zarząd powiatu`, `wójt/burmistrz/prezydent`). Everyday names (ZDW, ZDiK, PZD, MZD) are organisational units that do the work for that organ; their names vary and I found no primary list: **UNCONFIRMED**.

### B.2 Cities with county rights (`miasta na prawach powiatu`)

- **Art. 19 ust. 5** [law]: "W granicach miast na prawach powiatu zarządcą wszystkich dróg publicznych, z wyjątkiem autostrad i dróg ekspresowych oraz dróg, o których mowa w przepisach wydanych na podstawie art. 5 ust. 2a, jest prezydent miasta."
  - So inside such a city the president manages national, voivodeship, county and municipal roads. GDDKiA keeps motorways and expressways. The art. 5 ust. 2a exception covers national roads designated by regulation to give TEN-T access to the ports listed in Regulation (EU) 1315/2013.
- GDDKiA's page states it as "w 66 miastach na prawach powiatu prezydent miasta zarządza wszystkimi drogami publicznymi z wyjątkiem autostrad i dróg ekspresowych" (14.08.2023). The count "66" is from that page, not re-checked. [gddkia]
- The same split exists for traffic management: PoRD art. 10 ust. 6: "Prezydent miasta zarządza ruchem na drogach publicznych położonych w miastach na prawach powiatu, z wyjątkiem autostrad i dróg ekspresowych." [law]
- Mind the difference between a city with county rights and an ordinary town: in an ordinary town, a national road is still GDDKiA's, a voivodeship road still the voivodeship's, and only municipal (gminne) roads belong to the mayor. [inferred from ust. 2]

### B.3 Telling the road category

- Regulation on technical conditions for signs (Dz.U. 2019 poz. 2311, consolidated; section 6.3.7): "Znaki z numerem drogi stosuje się samodzielnie lub umieszcza się na znakach kierunku w celu wskazania dróg krajowych lub wojewódzkich. Numerów dróg pozostałych kategorii nie umieszcza się na znakach drogowych." [law]
- Signs (from the text and figures of the regulation, Dz.U. pp. 288-289) [law]:

| Sign | Meaning | Look |
|---|---|---|
| E-15a / E-15f / E-15g | national road number | "o tle barwy czerwonej ... napisie barwy białej" (text); axle-load variants differ in frame |
| E-15b / E-15e / E-15h | voivodeship road number | yellow background, black digits (figure only; text does not state the colour); E-15e has a black-yellow dotted frame |
| E-15c | motorway number (`A4`) | red, white digits (figure only) |
| E-15d | expressway number (`S7`) | red, white digits (figure only) |
| E-16 | international route (`E 77`) | green, white digits (figure) |

- § 65 of the sign regulation (Dz.U. 2019 poz. 2310) says the E-15 signs "wskazują numer i rodzaj (kategorię) drogi". [law]
- So: red `DK`-style numbers = national; yellow = voivodeship; county and municipal roads have no number on signs. A driver cannot tell a county from a municipal road by signs, and a numberless road may also be a service or private road. [inferred]
- Road numbers for national and voivodeship roads are assigned by the Director General of GDDKiA ("nadaje numery drogom krajowym i wojewódzkim"; https://www.gov.pl/web/gddkia/drogi-wojewodzkie, list dated 31.01.2023 by file name). [gddkia]
- Where to look the manager up: GDDKiA publishes "Kto jest zarządcą tej drogi" (https://www.gov.pl/web/gddkia/kto-jest-zarzadca-tej-drogi2) and a map service https://drogi.gddkia.gov.pl. For county and municipal roads the practical route is the commune or county office; I found no official national register for them: **UNCONFIRMED**.

### B.4 GDDKiA claims page

- "Zgłaszanie szkód z ubezpieczenia OC zarządcy drogi": https://www.gov.pl/web/gddkia/zglaszanie-szkod-z-ubezpieczenia-oc-zarzadcy-drogi [gddkia, WebFetch summary]. Claims go to one of: the broker `Biuro Brokerów Ubezpieczeniowych Maxima Fides Sp. z o.o.` (GDDKiA's `pełnomocnik ... w zakresie administrowania szkodami`, szkody3@maxima-fides.pl, 42 636 64 98 wew. 38); the GDDKiA branch for the place of the damage; or the insurer "od 2026 roku", Towarzystwo Ubezpieczeń Wzajemnych Polski TUW (801 159 159 wew. 2). A claim form (`Formularz zgłoszenia szkody z ubezpieczenia OC`, .doc and .pdf, files dated 2026-03-09) is attached.
- The page does not list required documents, deadlines or the covered roads, and does not mention potholes or concession motorways. Contact data change with each policy year: do not hard-code them in the app.
- Older regional pages ask for a description by km marker, sketch, witnesses, licence and registration copy and dated photos (GDDKiA archive; per search summary, not opened).
- Also: https://www.gov.pl/web/gddkia/odszkodowania is about compensation for land taken for road building, not vehicle damage.

## Unconfirmed / open

- Whether the triangle is **required in addition to hazard lights** in a built-up area (art. 50 ust. 2 pkt 2 lit. b reads as a fallback; no official interpretation found).
- Legal basis and amount of the fine for not placing a triangle (police page says 300 zł + 1 point).
- Whether *standing* near a vehicle after dusk counts as "poruszający się" under art. 11 ust. 4a; no source says vests are required on motorways.
- First aid kit draft (M1, cars registered after 31 March 2027): only press reports; no draft text or number found.
- Specific penalty and legal text for pedestrians on a motorway; pushing a car on a motorway; jump-starting on a hard shoulder (no official guidance found).
- Whether the towing ban in art. 31 ust. 2 pkt 5 reaches expressways (text says only "autostradzie").
- Tesla (403) and other makes' towing rules; the VW and Nissan documents are model- and year-specific.
- 19 111 and the "0" prefix on some mobile networks (one older source only).
- Whether all motorway/expressway sections still have working alarm columns (`kolumny alarmowe`).
- Concession status after 2023 (A4 Katowice-Kraków handover in 2027) and the current concessionaire list.
- Limitation period for road-condition damage claims; no national register of county/municipal road managers.
- Everyday names of local road authorities (ZDW, ZDiK, PZD, MZD).
- Not read in full: later (2021-2026) amendments of the sign regulations; police pages from Łódź, Środa Śląska and Elbląg on the built-up-area triangle.

## Sources

- PoRD consolidated text: https://api.sejm.gov.pl/eli/acts/DU/2024/1251/text.pdf (Dz.U. 2024 poz. 1251: art. 2 pkt 3-4, 10 ust. 6, 11 ust. 4a, 31, 41, 44, 45, 46, 49, 50, 63, 66 ust. 5)
- UDP consolidated text: https://api.sejm.gov.pl/eli/acts/DU/2025/889/text.pdf (Dz.U. 2025 poz. 889: art. 2, 3, 4 pkt 10-11, 5, 18, 19, 20)
- Equipment regulation, consolidated: https://api.sejm.gov.pl/eli/acts/DU/2024/502/text.html (Dz.U. 2024 poz. 502: § 11, 18, 24, 40, 43)
- Sign regulations, consolidated: https://api.sejm.gov.pl/eli/acts/DU/2019/2310/text.pdf (znaki i sygnały drogowe, § 48, 65) and https://api.sejm.gov.pl/eli/acts/DU/2019/2311/text.pdf (warunki techniczne, section 6.3.7)
- GDDKiA: https://www.gov.pl/web/gddkia/droga-to-nie-tor-wyscigowy-pas-awaryjny-to-nie-parking; https://www.gov.pl/web/gddkia/numer-19-111---niezawodny-partner-kazdego-kierowcy; https://www.gov.pl/web/gddkia/informacja-drogowa---19-111; https://www.gov.pl/web/gddkia/zglaszanie-szkod-z-ubezpieczenia-oc-zarzadcy-drogi; https://www.gov.pl/web/gddkia/kto-jest-zarzadca-tej-drogi2; https://www.gov.pl/web/gddkia/ponad-1800-km-autostrad-wiekszosc-bez-oplat; https://www.gov.pl/web/gddkia/drogi-wojewodzkie (the old `gddkia.gov.pl` and `archiwum.gddkia.gov.pl` pages redirect to gov.pl or refuse connections)
- Police: https://pabianice.policja.gov.pl/epa/informacje/122092,Niebezpieczna-sytuacja-na-S-14.html; https://pomorska.policja.gov.pl/pom/informacje/wiadomosci/135942,Bezpieczna-autostrada-Twoje-zycie-Twoja-odpowiedzialnosc.html; https://isp.policja.pl/isp/aktualnosci/15477,Autostrada-jak-zachowac-sie-w-przypadku-awarii-kolizji-lub-wypadku.html; https://ksp.policja.gov.pl/wrd/aktualnosci/118448,JAK-SYGNALIZOWAC-POSTOJ-na-drodze.html; https://zachodniopomorska.policja.gov.pl/sz/aktualnosci/ruch-drogowy/warto-wiedziec/73735,Jak-prawidlowo-sygnalizowac-postoj-pojazdu-wynikajacy-z-awarii.html; https://legnica.policja.gov.pl/dle/aktualnosci/bieza/87716,Wjechales-dziure-i-uszkodziles-auto-i-co-teraz.html
- Rzecznik Finansowy: https://archiwum.rf.gov.pl/2024/05/09/szkody-w-pojazdach-zwiazane-z-ubytkami-dziurami-w-drodze-oraz-dziko-zyjacymi-zwierzetami-praktyczne-odpowiedzi-na-pojawiajace-sie-problemy/
- Manufacturers: Nissan LEAF 2023 UK manual (towing and jump starting pages above); VW ID.3 karta ratownicza (PDF above)
- Press on the first aid kit draft: https://www.rmf24.pl/fakty/polska/news-apteczka-w-autach-osobowych-coraz-blizej-mamy-komentarz-mini,nIdn,1012511
