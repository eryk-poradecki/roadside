# Safety checklist copy (EN / PL)

The final strings for the safety checklist ([ADR 0010](../adr/0010-static-safety-checklist-in-frontend.md)) and the damage report's addressee help line ([ADR 0009](../adr/0009-damage-report-drafted-from-incident.md)). The build ticket copies them into `i18n/en.ts` and `i18n/pl.ts`. Each fact cites an official source from the [table at the end](#sources). No line is left *to verify*: every fact cites an official source or makes no claim. Approved by the project owner on 2026-11-10. Background and quotes: [research: Polish roadside safety and road managers](../research/roadside-safety-pl.md) (not a source on its own).

Voice: short sentences, second person, reassuring (`PRODUCT.md`). Shape: one first step, at most 4 more items, and the last item is always the shared 112 line.

## Labels

| Key | EN | PL |
| --- | --- | --- |
| `firstLabel` | Do this first | Zrób to najpierw |
| `checklistTitle` | Then | Potem |
| `checklistBadge` | Safety basics · not AI | Podstawy bezpieczeństwa · nie AI |
| `checklistSummary(n)` | N more safety steps | Jeszcze N kroki/kroków bezpieczeństwa |
| `resolvedSummary` | Safety steps | Kroki bezpieczeństwa |

## Shared items

| Key | EN | PL | Sources |
| --- | --- | --- | --- |
| `getOut` | Put on a reflective vest if you have one. Get everyone out on the side away from traffic, behind the barrier or well away from the road. | Jeśli masz kamizelkę odblaskową, załóż ją. Wysiądźcie od strony pobocza i stańcie za barierą albo z dala od jezdni. | Vest not mandatory: [EQ] § 11; vest, passenger side, behind the barrier: [POL-A], [GD-PAS] |
| `triangle` | Place the warning triangle behind the car: right behind it in town, 30–50 m outside built-up areas, 100 m on a motorway or expressway. | Ustaw trójkąt ostrzegawczy za autem: w terenie zabudowanym tuż za nim, poza nim 30–50 m, na autostradzie lub drodze ekspresowej 100 m. | [PoRD] art. 50 ust. 2; mandatory: [EQ] § 11 ust. 1 pkt 13 |
| `call112` | Anyone hurt, smoke, fire, leaking fuel, or the car standing in a live lane: call 112. | Ktoś jest ranny, widać dym lub ogień, cieknie paliwo albo auto stoi na pasie ruchu: dzwoń pod 112. | 112 as the emergency number: [GD-19111] (contrasts 19 111, "nie jest numerem alarmowym") |

In a built-up area art. 50 ust. 2 puts the triangle behind or on the car (the copy leaves out the 1 m height limit). Whether it is legally required there when hazard lights work is ambiguous, so the copy gives it as guidance and never says it is required.

## Per problem type

Order: `first`, then the items in order. `getOut`, `triangle` and `call112` are the shared items above.

### Flat tyre (`tyre`)

| | EN | PL | Sources |
| --- | --- | --- | --- |
| first | Hazard lights on. Then stop as far from traffic as you safely can. | Włącz światła awaryjne. Zatrzymaj się jak najdalej od ruchu, na ile to bezpieczne. | [PoRD] art. 50 ust. 1–2 |
| 1 | `getOut` | | |
| 2 | `triangle` | | |
| 3 | Don't change the tyre next to moving traffic or on the hard shoulder. | Nie zmieniaj koła przy jadących autach ani na pasie awaryjnym. | [POL-A] |
| 4 | `call112` | | |

### Flat battery (`battery`)

| | EN | PL | Sources |
| --- | --- | --- | --- |
| first | Hazard lights on. Turn off the radio, air con and anything else drawing power. | Włącz światła awaryjne. Wyłącz radio, klimatyzację i wszystko, co pobiera prąd. | [PoRD] art. 50 ust. 1–2 |
| 1 | `getOut` | | |
| 2 | `triangle` | | |
| 3 | Don't jump-start next to moving traffic or on the hard shoulder. | Nie odpalaj „na kable” przy jadących autach ani na pasie awaryjnym. | [POL-A] (no repairs on the emergency lane; no rule names jump-starting) |
| 4 | `call112` | | |

The prototype said "switch off lights". That was dropped: at night the car's lights help other drivers see it.

### Out of fuel (`fuel`)

| | EN | PL | Sources |
| --- | --- | --- | --- |
| first | Hazard lights on. If the car is still rolling, steer to the safest spot off the road. | Włącz światła awaryjne. Jeśli auto jeszcze się toczy, zjedź w najbezpieczniejsze miejsce poza jezdnią. | [PoRD] art. 50 ust. 1; emergency lane: [GD-PAS] |
| 1 | `getOut` | | |
| 2 | `triangle` | | |
| 3 | On a motorway or expressway, don't walk along the road to fetch fuel. Wait behind the barrier and call for help. | Na autostradzie lub drodze ekspresowej nie idź po paliwo wzdłuż jezdni. Zaczekaj za barierą i wezwij pomoc. | Motorways for motor vehicles only: [PoRD] art. 2 pkt 3–4; stay behind the barrier: [POL-A], [POL-POM], [GD-PAS] |
| 4 | `call112` | | |

### Out of charge (`charge`, the EV variant of `fuel`)

| | EN | PL | Sources |
| --- | --- | --- | --- |
| first | Hazard lights on. While the car still moves, steer to the safest spot off the road. | Włącz światła awaryjne. Póki auto jeszcze jedzie, zjedź w najbezpieczniejsze miejsce poza jezdnią. | [PoRD] art. 50 ust. 1–2 |
| 1 | `getOut` | | |
| 2 | `triangle` | | |
| 3 | Ask for a flatbed truck. Many electric cars can't be towed on their wheels. | Poproś o lawetę. Wiele aut elektrycznych nie może być holowanych na kołach. | Manufacturer, not government (accepted for this item only): [NISSAN], [VW] |
| 4 | `call112` | | |

### Pothole damage (`pothole`)

| | EN | PL | Sources |
| --- | --- | --- | --- |
| first | Slow down and stop only where it's safe. Hazard lights on. | Zwolnij i zatrzymaj się tylko w bezpiecznym miejscu. Włącz światła awaryjne. | [PoRD] art. 50 ust. 1–2 |
| 1 | `getOut` | | |
| 2 | Don't drive on if a tyre, a wheel or the steering feels wrong. | Nie jedź dalej, jeśli opona, koło lub kierownica zachowują się dziwnie. | General safety advice, no legal claim |
| 3 | Take photos of the hole and the damage, and note the exact place. They help with a claim later. | Zrób zdjęcia dziury i uszkodzeń i zapisz dokładne miejsce. Przydadzą się przy zgłoszeniu szkody. | [RF] |
| 4 | `call112` | | |

The pothole list has no `triangle`, because the driver often drives on. If the car can't move, the AI answer adds it (invariant 4).

### Something else (`other`)

| | EN | PL | Sources |
| --- | --- | --- | --- |
| first | Hazard lights on. Then move away from traffic if you safely can. | Włącz światła awaryjne. Odsuń się od ruchu, jeśli to bezpieczne. | [PoRD] art. 50 ust. 1–2 |
| 1 | `getOut` | | |
| 2 | `triangle` | | |
| 3 | `call112` | | |

## Damage report: addressee help line

Replaces the line in ADR 0009, which missed toll motorways and cities with county rights.

**EN**

> Who manages this road?
> - Motorway or expressway: GDDKiA. On a toll section, ask the motorway operator or GDDKiA.
> - Any other road in a city with county rights (e.g. Kraków, Poznań, Gdańsk): the city.
> - Elsewhere: a red road-number sign means GDDKiA, a yellow one the voivodeship's road authority, no number the county or the municipality.
> Not sure? Use GDDKiA's "Who manages this road?" page.

**PL**

> Kto zarządza tą drogą?
> - Autostrada lub droga ekspresowa: GDDKiA. Na płatnym odcinku zapytaj operatora autostrady albo GDDKiA.
> - Każda inna droga w mieście na prawach powiatu (np. Kraków, Poznań, Gdańsk): miasto.
> - Poza takim miastem: czerwony numer drogi na znaku oznacza GDDKiA, żółty zarząd dróg województwa, brak numeru powiat albo gminę.
> Nie wiesz? Sprawdź stronę GDDKiA „Kto jest zarządcą tej drogi?".

Who handles claims on concession sections is unconfirmed, so the toll-section line names both and makes no claim. Sources: [UDP] art. 19 ust. 2, 3 and 5; red/yellow numbers and no numbers on other roads: [SIGNS] section 6.3.7; lookup page: [GD-WHO]. The link is [GD-WHO]. No phone numbers or claim addresses are hard-coded, because GDDKiA's claim contacts change yearly ([GD-CLAIM]).

## Sources

| Id | Source |
| --- | --- |
| [PoRD] | Prawo o ruchu drogowym, consolidated text Dz.U. 2024 poz. 1251: https://api.sejm.gov.pl/eli/acts/DU/2024/1251/text.pdf |
| [UDP] | Ustawa o drogach publicznych, consolidated text Dz.U. 2025 poz. 889: https://api.sejm.gov.pl/eli/acts/DU/2025/889/text.pdf |
| [EQ] | Rozporządzenie w sprawie warunków technicznych pojazdów (equipment), Dz.U. 2024 poz. 502: https://api.sejm.gov.pl/eli/acts/DU/2024/502/text.html |
| [SIGNS] | Rozporządzenie w sprawie szczegółowych warunków technicznych dla znaków (Dz.U. 2019 poz. 2311), section 6.3.7: https://api.sejm.gov.pl/eli/acts/DU/2019/2311/text.pdf |
| [GD-PAS] | GDDKiA, "Droga to nie tor wyścigowy, pas awaryjny to nie parking": https://www.gov.pl/web/gddkia/droga-to-nie-tor-wyscigowy-pas-awaryjny-to-nie-parking |
| [GD-19111] | GDDKiA, "Informacja drogowa – 19 111": https://www.gov.pl/web/gddkia/informacja-drogowa---19-111 |
| [GD-WHO] | GDDKiA, "Kto jest zarządcą tej drogi?": https://www.gov.pl/web/gddkia/kto-jest-zarzadca-tej-drogi2 |
| [GD-CLAIM] | GDDKiA, "Zgłaszanie szkód z ubezpieczenia OC zarządcy drogi": https://www.gov.pl/web/gddkia/zglaszanie-szkod-z-ubezpieczenia-oc-zarzadcy-drogi |
| [POL-A] | Policja Pabianice, "Niebezpieczna sytuacja na S-14" (7 Aug 2026): passenger side, behind the barrier, no repairs or wheel change on the emergency lane: https://pabianice.policja.gov.pl/epa/informacje/122092,Niebezpieczna-sytuacja-na-S-14.html |
| [POL-POM] | Policja Pomorska, "Bezpieczna autostrada…" (19 Aug 2024): stay behind the barrier the whole time: https://pomorska.policja.gov.pl/pom/informacje/wiadomosci/135942,Bezpieczna-autostrada-Twoje-zycie-Twoja-odpowiedzialnosc.html |
| [RF] | Rzecznik Finansowy, "Szkody w pojazdach związane z ubytkami (dziurami) w drodze…" (9 May 2024): https://archiwum.rf.gov.pl/2024/05/09/szkody-w-pojazdach-zwiazane-z-ubytkami-dziurami-w-drodze-oraz-dziko-zyjacymi-zwierzetami-praktyczne-odpowiedzi-na-pojawiajace-sie-problemy/ |
| [NISSAN] | Nissan LEAF owner's manual (2023, UK), towing: https://www.nissan.co.uk/owners/car-repair/car-owner-manual/manuals/iom/leaf/0ze1/e0/2023/towing-recommended-by-nissan-1.shtml |
| [VW] | Volkswagen ID.3 rescue card (PL): https://www.volkswagen.pl/idhub/content/dam/onehub_pkw/importers/pl/serwis-i-akcesoria/wypadek-lub-awaria/karta-ratownicza/karty/id_3_5dr_2019_ds_pl.pdf |
