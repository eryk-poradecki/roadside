// Prototype scenarios. Override with query params, e.g. ?loc=denied&ai=error&demo=0
// Result screen: ?result=tyre
//   &ai=ok|error|asking|answered-after-question|unsure|loading
//   &places=found|searching|none|unavailable|noloc   (default: searching, then found)
//   &vehicle=full|noins|none &resolved=1 &map=open (full map, with places=found)
export type LocState = 'detecting' | 'found' | 'weak' | 'denied'
export type AiOutcome = 'ok' | 'error' | 'asking' | 'answered-after-question' | 'unsure' | 'loading'
export type PlacesOutcome = 'found' | 'searching' | 'none' | 'unavailable' | 'noloc'

const q = new URLSearchParams(window.location.search)

const loc = q.get('loc')
export const MOCK_LOC: LocState | null =
  loc === 'detecting' || loc === 'found' || loc === 'weak' || loc === 'denied' ? loc : null

const oneOf = <T extends string>(k: string, all: readonly T[], fallback: T): T =>
  (all as readonly string[]).includes(q.get(k) ?? '') ? (q.get(k) as T) : fallback

export const MOCK_AI = oneOf<AiOutcome>('ai', ['ok', 'error', 'asking', 'answered-after-question', 'unsure', 'loading'], 'ok')
/** null = the default flow: searching first, places arrive later */
export const MOCK_PLACES: PlacesOutcome | null = q.has('places')
  ? oneOf<PlacesOutcome>('places', ['found', 'searching', 'none', 'unavailable', 'noloc'], 'found')
  : null
export const PLACES_DELAY_MS = 7000
export const TURN_DELAY_MS = 1400
export const MOCK_VEHICLE = oneOf<'full' | 'noins' | 'none'>('vehicle', ['full', 'noins', 'none'], 'full')
export const MOCK_MAP_OPEN = q.get('map') === 'open'
export const MOCK_RESOLVED = q.get('resolved') === '1'
export const SHOW_DEMO = q.get('demo') !== '0'
export const AI_DELAY_MS = 3200

const TILE_IDS = ['tyre', 'battery', 'fuel', 'pothole', 'other'] as const
const pick = (k: string) => {
  const v = q.get(k)
  return TILE_IDS.find((id) => id === v) ?? null
}
// ?sheet=tyre opens the bottom sheet; ?result=tyre jumps to the hand-off screen.
export const MOCK_SHEET = pick('sheet')
export const MOCK_RESULT = pick('result')

export const MOCK_LAT = { value: '52.2297', dir: 'N' }
export const MOCK_LON = { value: '21.0122', dir: 'E' }
export const MOCK_COORDS = '52.2297° N, 21.0122° E'
export const MOCK_ACCURACY = '240 m'
export const MOCK_ACCURACY_FOUND = '15 m'
