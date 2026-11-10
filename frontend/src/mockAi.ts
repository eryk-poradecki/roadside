// Prototype-only content for the Result screen. This is NOT the AI JSON contract;
// it is what the screen turned out to need, written as plain mock data.
import type { Lang, TileId } from './i18n'

export type Confidence = 'likely' | 'possible' | 'unsure'

export type AiAnswer = {
  cause: string
  confidence: Confidence
  alternatives: string[]
  steps: Step[]
  escalate: string[]
  /** photos the model saw, photos it could not see (cap / text-only), what it observed */
  photos: { seen: number; notSeen: number; observed?: string }
}

/** What a step relies on in the vehicle profile. Without it, `otherwise` is shown (or the step is dropped). */
export type Needs = 'assistance' | 'spare' | 'lockKey'
export type Step = string | { needs: Needs; text: string; otherwise?: string }

export type ClarifyRound = {
  /** immediate safety step, always first in an asking turn */
  now: string
  question: string
  options: string[]
}

type TileContent = { answer: AiAnswer; rounds: ClarifyRound[] }

const en: Record<TileId, TileContent> = {
  tyre: {
    rounds: [
      {
        now: 'Stop on firm, level ground, away from traffic.',
        question: 'Is the tyre completely flat?',
        options: ['Completely flat', 'Low but holding air', 'Not sure'],
      },
    ],
    answer: {
      cause: 'A puncture or a cut in the side wall of the front-left tyre.',
      confidence: 'likely',
      alternatives: ['A slow leak at the valve', 'A bent rim after hitting a kerb or pothole'],
      photos: { seen: 1, notSeen: 0, observed: 'The front-left tyre is flat, with a bulge on the side wall.' },
      steps: [
        'Leave the repair kit. A side-wall cut cannot be sealed.',
        { needs: 'spare', text: 'You have a space-saver spare. Fit it only once you are well away from traffic.', otherwise: 'If you have a spare wheel, fit it only once you are well away from traffic.' },
        { needs: 'lockKey', text: 'The wheel lock key is in the glovebox. Undo the locking bolt first.' },
        { needs: 'spare', text: 'Drive no faster than 80 km/h on the space-saver and get to a tyre shop today.', otherwise: 'On a space-saver spare, drive no faster than 80 km/h. Get to a tyre shop today.' },
      ],
      escalate: ['you are on a motorway or a narrow shoulder', 'the jack will not sit on firm, level ground', 'you cannot undo the wheel bolts'],
    },
  },
  battery: {
    rounds: [
      {
        now: 'Switch off the lights, radio and heater fan.',
        question: 'What happens when you turn the key?',
        options: ['Rapid clicking', 'One loud click', 'Nothing at all', 'Cranks slowly'],
      },
    ],
    answer: {
      cause: 'The battery is too flat to start the engine.',
      confidence: 'likely',
      alternatives: ['A loose or corroded battery clamp', 'A faulty starter motor'],
      photos: { seen: 0, notSeen: 0 },
      steps: [
        'Wait two minutes, then try once more. Do not keep cranking.',
        'A jump-start is fine away from traffic: red to red, then black to bare metal on your car.',
        'Once it starts, keep the engine running for at least 20 minutes.',
        'Book a battery check. A battery that went flat once often does it again.',
      ],
      escalate: ['you smell rotten eggs or the battery looks swollen', 'it still will not start after a jump-start'],
    },
  },
  fuel: {
    rounds: [
      {
        now: 'Hazard lights on. Stay off the carriageway.',
        question: 'Where is the car now?',
        options: ['On the hard shoulder', 'In a car park or lay-by', 'Still in a lane', 'Not sure'],
      },
    ],
    answer: {
      cause: 'The tank is empty.',
      confidence: 'likely',
      alternatives: ['A faulty fuel gauge, if it still showed fuel', 'A blocked fuel filter'],
      photos: { seen: 0, notSeen: 0 },
      steps: [
        'Stay with the car. Do not walk along the road to a fuel station.',
        { needs: 'assistance', text: '{insurer} can bring fuel to you. Call them with the button below.', otherwise: 'If you have roadside assistance, they can usually bring fuel to you.' },
        'With a spare can, add at least 5 litres before you try to start.',
        'If it is a diesel, turn the ignition on for 30 seconds before you start.',
      ],
      escalate: ['the car is stopped in a live lane', 'it will not start after refuelling'],
    },
  },
  pothole: {
    rounds: [
      {
        now: 'Stop only where it is safe. Hazard lights on.',
        question: 'How does the car feel?',
        options: ['Pulls to one side', 'Shakes or vibrates', 'Feels normal', 'Not sure'],
      },
    ],
    answer: {
      cause: 'Possible damage to the front-right wheel or tyre.',
      confidence: 'possible',
      alternatives: ['Knocked wheel alignment only', 'No damage: a hard hit can sound worse than it is'],
      photos: { seen: 2, notSeen: 1, observed: 'The front-right rim has a dent. The tyre still looks inflated.' },
      steps: [
        'Check the tyre for bulges or cuts, and the rim for dents.',
        'Photograph the pothole, the damage and something that shows where you are.',
        { needs: 'assistance', text: 'If the steering pulls or the car shakes, do not drive on. Call {insurer}.', otherwise: 'If the steering pulls or the car shakes, do not drive on. Fit a spare if you have one, or call for roadside help.' },
        'Your location is saved with this incident for the damage report.',
      ],
      escalate: ['a tyre is losing air', 'the steering feels loose or noisy'],
    },
  },
  other: {
    rounds: [
      {
        now: 'Switch the engine off and stand behind the barrier.',
        question: 'Where is the smoke or smell coming from?',
        options: ['From the engine bay', 'From under the car', 'From the exhaust', 'Not sure'],
      },
      {
        now: 'Keep the bonnet closed for now.',
        question: 'Is a warning light on?',
        options: ['Temperature light', 'Oil light', 'No lights', 'Not sure'],
      },
    ],
    answer: {
      cause: 'The engine is overheating, probably from low coolant or a leak.',
      confidence: 'possible',
      alternatives: ['A failed cooling fan', 'A broken water-pump belt'],
      photos: { seen: 0, notSeen: 0 },
      steps: [
        'Keep the engine off. Do not open the coolant cap while hot: it can scald.',
        'Wait at least 30 minutes behind the barrier.',
        'Once cool, look for a puddle under the car or a low coolant level.',
        { needs: 'assistance', text: 'Do not drive on with the temperature light on. Ask {insurer} for a tow.', otherwise: 'Do not drive on with the temperature light on. Arrange a tow: your roadside assistance if you have it, or a local towing service.' },
      ],
      escalate: ['you see flames, or the smoke gets thicker (call 112)', 'you smell fuel'],
    },
  },
}

const pl: Record<TileId, TileContent> = {
  tyre: {
    rounds: [
      {
        now: 'Zatrzymaj się na twardym, równym podłożu, z dala od ruchu.',
        question: 'Czy opona jest całkiem płaska?',
        options: ['Całkiem płaska', 'Niska, ale trzyma', 'Nie wiem'],
      },
    ],
    answer: {
      cause: 'Przebicie lub rozcięcie boku lewej przedniej opony.',
      confidence: 'likely',
      alternatives: ['Powolny wyciek przy wentylu', 'Wygięta felga po uderzeniu w krawężnik lub dziurę'],
      photos: { seen: 1, notSeen: 0, observed: 'Lewa przednia opona jest płaska, z wybrzuszeniem na boku.' },
      steps: [
        'Odłóż zestaw naprawczy. Rozcięcia boku nie da się uszczelnić.',
        { needs: 'spare', text: 'Masz koło dojazdowe. Załóż je dopiero z dala od ruchu.', otherwise: 'Jeśli masz koło zapasowe, załóż je dopiero z dala od ruchu.' },
        { needs: 'lockKey', text: 'Klucz do śruby zabezpieczającej jest w schowku. Odkręć ją jako pierwszą.' },
        { needs: 'spare', text: 'Na kole dojazdowym jedź najwyżej 80 km/h i jeszcze dziś dojedź do wulkanizacji.', otherwise: 'Na kole dojazdowym jedź najwyżej 80 km/h. Jeszcze dziś dojedź do wulkanizacji.' },
      ],
      escalate: ['stoisz na autostradzie lub wąskim poboczu', 'podnośnika nie da się oprzeć na twardym, równym podłożu', 'nie możesz odkręcić śrub koła'],
    },
  },
  battery: {
    rounds: [
      {
        now: 'Wyłącz światła, radio i nawiew.',
        question: 'Co się dzieje, gdy przekręcasz kluczyk?',
        options: ['Szybkie klikanie', 'Jedno głośne kliknięcie', 'Nic', 'Rozrusznik kręci wolno'],
      },
    ],
    answer: {
      cause: 'Akumulator jest zbyt rozładowany, by uruchomić silnik.',
      confidence: 'likely',
      alternatives: ['Luźna lub skorodowana klema', 'Uszkodzony rozrusznik'],
      photos: { seen: 0, notSeen: 0 },
      steps: [
        'Odczekaj dwie minuty i spróbuj jeszcze raz. Nie kręć rozrusznikiem w kółko.',
        'Odpalanie „na kable” z dala od ruchu: czerwony do czerwonego, czarny do metalu w Twoim aucie.',
        'Gdy silnik zapali, nie gaś go przez co najmniej 20 minut.',
        'Umów sprawdzenie akumulatora. Ten, który raz padł, często pada znowu.',
      ],
      escalate: ['czujesz zapach zgniłych jaj lub akumulator jest spuchnięty', 'auto nie zapala mimo odpalania „na kable”'],
    },
  },
  fuel: {
    rounds: [
      {
        now: 'Włącz światła awaryjne. Nie stój na jezdni.',
        question: 'Gdzie teraz stoi auto?',
        options: ['Na pasie awaryjnym', 'Na parkingu lub zatoczce', 'Wciąż na pasie ruchu', 'Nie wiem'],
      },
    ],
    answer: {
      cause: 'Skończyło się paliwo.',
      confidence: 'likely',
      alternatives: ['Wadliwy wskaźnik paliwa, jeśli pokazywał zapas', 'Zatkany filtr paliwa'],
      photos: { seen: 0, notSeen: 0 },
      steps: [
        'Zostań przy aucie. Nie idź po paliwo wzdłuż drogi.',
        { needs: 'assistance', text: '{insurer} może przywieźć paliwo. Zadzwoń przyciskiem poniżej.', otherwise: 'Jeśli masz assistance, zwykle może przywieźć paliwo.' },
        'Z kanistrem wlej co najmniej 5 litrów, zanim spróbujesz zapalić.',
        'Jeśli to diesel, włącz zapłon na 30 sekund przed uruchomieniem.',
      ],
      escalate: ['auto stoi na pasie ruchu', 'silnik nie zapala po zatankowaniu'],
    },
  },
  pothole: {
    rounds: [
      {
        now: 'Zatrzymaj się tylko w bezpiecznym miejscu. Włącz światła awaryjne.',
        question: 'Jak zachowuje się auto?',
        options: ['Ściąga na bok', 'Trzęsie się lub drga', 'Normalnie', 'Nie wiem'],
      },
    ],
    answer: {
      cause: 'Możliwe uszkodzenie prawego przedniego koła lub opony.',
      confidence: 'possible',
      alternatives: ['Tylko rozregulowana zbieżność', 'Brak uszkodzeń: mocne uderzenie brzmi gorzej, niż jest'],
      photos: { seen: 2, notSeen: 1, observed: 'Prawa przednia felga jest wgnieciona. Opona wygląda na napompowaną.' },
      steps: [
        'Sprawdź oponę pod kątem wybrzuszeń i rozcięć, a felgę pod kątem wgnieceń.',
        'Zrób zdjęcia dziury, uszkodzenia i czegoś, co pokazuje, gdzie jesteś.',
        { needs: 'assistance', text: 'Jeśli kierownica ściąga lub auto drga, nie jedź dalej. Zadzwoń do {insurer}.', otherwise: 'Jeśli kierownica ściąga lub auto drga, nie jedź dalej. Załóż zapas, jeśli masz, albo wezwij pomoc drogową.' },
        'Twoja lokalizacja jest zapisana w tym zdarzeniu na potrzeby zgłoszenia szkody.',
      ],
      escalate: ['z opony uchodzi powietrze', 'kierownica ma luz lub stuka'],
    },
  },
  other: {
    rounds: [
      {
        now: 'Wyłącz silnik i stań za barierką.',
        question: 'Skąd jest dym lub zapach?',
        options: ['Spod maski', 'Spod auta', 'Z wydechu', 'Nie wiem'],
      },
      {
        now: 'Na razie nie otwieraj maski.',
        question: 'Czy świeci się kontrolka?',
        options: ['Temperatura', 'Olej', 'Żadna', 'Nie wiem'],
      },
    ],
    answer: {
      cause: 'Silnik się przegrzewa, prawdopodobnie przez brak płynu lub wyciek.',
      confidence: 'possible',
      alternatives: ['Uszkodzony wentylator chłodnicy', 'Zerwany pasek pompy wody'],
      photos: { seen: 0, notSeen: 0 },
      steps: [
        'Nie uruchamiaj silnika. Nie odkręcaj gorącego korka płynu: może poparzyć.',
        'Odczekaj co najmniej 30 minut za barierką.',
        'Gdy ostygnie, sprawdź, czy pod autem jest plama lub czy brakuje płynu.',
        { needs: 'assistance', text: 'Nie jedź dalej ze świecącą kontrolką temperatury. Poproś {insurer} o holowanie.', otherwise: 'Nie jedź dalej ze świecącą kontrolką temperatury. Zamów holowanie: assistance, jeśli masz, albo lokalną pomoc drogową.' },
      ],
      escalate: ['widzisz ogień lub dym gęstnieje (dzwoń 112)', 'czujesz zapach paliwa'],
    },
  },
}

const unsure: Record<Lang, AiAnswer> = {
  en: {
    cause: 'We cannot tell what is wrong from this alone.',
    confidence: 'unsure',
    alternatives: ['An electrical fault', 'A fuel supply problem'],
    photos: { seen: 0, notSeen: 0 },
    steps: [
      'Stay somewhere safe, away from traffic.',
      { needs: 'assistance', text: 'Call {insurer} and tell them what you see and hear.', otherwise: 'Call for roadside help, such as your assistance if you have it, and describe what you see and hear.' },
    ],
    escalate: ['anything gets worse while you wait'],
  },
  pl: {
    cause: 'Na tej podstawie nie da się ustalić, co jest nie tak.',
    confidence: 'unsure',
    alternatives: ['Usterka elektryczna', 'Problem z dopływem paliwa'],
    photos: { seen: 0, notSeen: 0 },
    steps: [
      'Zostań w bezpiecznym miejscu, z dala od ruchu.',
      { needs: 'assistance', text: 'Zadzwoń do {insurer} i opisz, co widzisz i słyszysz.', otherwise: 'Wezwij pomoc drogową, np. assistance, jeśli masz, i opisz, co widzisz i słyszysz.' },
    ],
    escalate: ['cokolwiek się pogorszy, gdy czekasz'],
  },
}

export function aiContent(lang: Lang, tile: TileId, lowConfidence: boolean) {
  const c = (lang === 'pl' ? pl : en)[tile]
  return { rounds: c.rounds, answer: lowConfidence ? unsure[lang] : c.answer }
}

// ---- Vehicle (from the vehicle profile) ----
export type MockVehicle = {
  name: string
  tyreSize: string
  spare: Record<Lang, string> | null
  lockKey: Record<Lang, string> | null
  /** assistance insurance: insurer name and phone, both optional in the profile */
  insurer: string | null
  assistancePhone: string | null
}

const OCTAVIA = {
  name: 'Škoda Octavia III',
  tyreSize: '205/55 R16',
  spare: { en: 'space-saver spare', pl: 'koło dojazdowe' },
  lockKey: { en: 'lock key in glovebox', pl: 'klucz w schowku' },
}

export const VEHICLES: Record<'full' | 'noins', MockVehicle> = {
  full: { ...OCTAVIA, insurer: 'Asysta 24', assistancePhone: '+48000000000' },
  noins: { ...OCTAVIA, lockKey: null, insurer: null, assistancePhone: null },
}

/** Resolve vehicle-dependent steps: a step that needs something the vehicle lacks falls back or drops. */
export function resolveSteps(steps: Step[], v: MockVehicle | null): string[] {
  const has = (n: Needs) => !!v && (n === 'assistance' ? !!v.assistancePhone : n === 'spare' ? !!v.spare : !!v.lockKey)
  return steps.flatMap((s) => {
    if (typeof s === 'string') return [s]
    if (has(s.needs)) return [s.text.replace('{insurer}', v?.insurer ?? 'your assistance')]
    return s.otherwise ? [s.otherwise] : []
  })
}

// ---- Nearby places ----
// SAMPLE places, not OSM data: public Overpass instances were at capacity in all
// 5 attempts across 3 servers. Shapes mirror Overpass (name and tags may be missing).
export type PlaceCat = 'tyres' | 'fuel' | 'repair'
export type Place = {
  id: string
  cat: PlaceCat
  name: string | null
  lat: number
  lon: number
  distanceKm: number
  phone?: string
  /** raw OSM opening_hours */
  openingHours?: string
}

export const USER_POS = { lat: 52.2297, lon: 21.0122 }

export const PLACES: Place[] = [
  { id: 'n1', cat: 'tyres', name: 'Wulkanizacja Hoża', lat: 52.2271, lon: 21.0177, distanceKm: 0.5, phone: '+48000000001', openingHours: 'Mo-Fr 08:00-18:00; Sa 09:00-14:00' },
  { id: 'n2', cat: 'fuel', name: null, lat: 52.2335, lon: 21.0068, distanceKm: 0.6, openingHours: '24/7' },
  { id: 'n3', cat: 'fuel', name: 'Stacja Emilii Plater', lat: 52.2318, lon: 20.9996, distanceKm: 0.9 },
  { id: 'n4', cat: 'repair', name: 'Auto Serwis Wilcza', lat: 52.2263, lon: 21.0003, distanceKm: 0.9, phone: '+48000000002', openingHours: 'Mo-Su 07:00-22:00' },
  { id: 'n5', cat: 'repair', name: 'Mechanika Pojazdowa Koszykowa', lat: 52.2219, lon: 21.0055, distanceKm: 1.0, openingHours: 'Mo-Fr 08:00-17:00; PH off' },
  { id: 'n6', cat: 'tyres', name: 'Opony Powiśle', lat: 52.2399, lon: 21.0301, distanceKm: 1.7, phone: '+48000000003' },
]

/**
 * OSM opening_hours is a rich grammar (weekday ranges, holidays, exceptions), so the
 * screen shows only values that are unambiguous at a glance and omits the rest.
 * Supported: "24/7" and the same hours every day ("Mo-Su HH:MM-HH:MM").
 */
export function simpleHours(raw: string | undefined, lang: Lang): string | null {
  if (!raw) return null
  const v = raw.trim()
  if (v === '24/7') return lang === 'pl' ? 'Czynne całą dobę' : 'Open 24 hours'
  const m = /^Mo-Su (\d{2}:\d{2})-(\d{2}:\d{2})$/.exec(v)
  if (m) return lang === 'pl' ? `Codziennie ${m[1]}–${m[2]}` : `Daily ${m[1]}–${m[2]}`
  return null
}

/** Category pre-selected for a problem type; the driver can still switch to All. */
export const DEFAULT_FILTER: Record<TileId, PlaceCat | 'all'> = {
  tyre: 'tyres',
  fuel: 'fuel',
  battery: 'repair',
  pothole: 'tyres',
  other: 'all',
}
