import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { en } from '../src/i18n/en'
import { pl } from '../src/i18n/pl'

/** The approved copy (ADR 0010). The i18n files must match it word for word. */
const doc = readFileSync(resolve(__dirname, '../../docs/copy/safety-checklist.md'), 'utf8')

const cells = (row: string) =>
  row
    .split('|')
    .slice(1, -1)
    .map((c) => c.trim())

/** The table rows of the markdown between `start` and the next heading of the same level. */
function rows(start: string): string[][] {
  const from = doc.indexOf(start)
  if (from < 0) throw new Error(`Missing section: ${start}`)
  const level = /^#+/.exec(start)?.[0] ?? '#'
  const rest = doc.slice(from + start.length)
  const end = rest.search(new RegExp(`\\n#{1,${String(level.length)}} `))
  const body = end < 0 ? rest : rest.slice(0, end)
  return body
    .split('\n')
    .filter((l) => l.startsWith('|') && !/^\|\s*-/.test(l))
    .slice(1) // header row
    .map(cells)
}

const unquote = (s: string) => s.replace(/^`|`$/g, '')

const shared = new Map(
  rows('## Shared items').map(([key = '', e = '', p = '']) => [unquote(key), { en: e, pl: p }]),
)

const KEYS = ['tyre', 'battery', 'fuel', 'charge', 'pothole', 'other'] as const

/** `tyre` for the on-road list, `parked.tyre` for its parked variant (#93). */
function listFromDoc(key: string) {
  const heading = doc.split('\n').find((l) => l.startsWith('### ') && l.includes(`(\`${key}\``))
  if (!heading) throw new Error(`No section for ${key}`)
  const result = {
    en: { first: '', items: [] as string[] },
    pl: { first: '', items: [] as string[] },
  }
  for (const [n = '', e = '', p = ''] of rows(heading)) {
    const sharedItem = shared.get(unquote(e))
    const item = sharedItem ?? { en: e, pl: p }
    if (n === 'first') {
      result.en.first = item.en
      result.pl.first = item.pl
    } else {
      result.en.items.push(item.en)
      result.pl.items.push(item.pl)
    }
  }
  return result
}

describe('safety checklist copy', () => {
  it.each(KEYS)('matches docs/copy/safety-checklist.md for %s in both languages', (key) => {
    const fromDoc = listFromDoc(key)
    expect(en.checklist.lists[key]).toEqual(fromDoc.en)
    expect(pl.checklist.lists[key]).toEqual(fromDoc.pl)
  })

  it('always ends with the shared 112 line and has at most 4 more items', () => {
    for (const key of KEYS) {
      expect(en.checklist.lists[key].items.at(-1)).toBe(shared.get('call112')?.en)
      expect(pl.checklist.lists[key].items.at(-1)).toBe(shared.get('call112')?.pl)
      expect(en.checklist.lists[key].items.length).toBeLessThanOrEqual(4)
    }
  })

  it.each(KEYS)('matches the parked variant in the copy doc for %s in both languages', (key) => {
    const fromDoc = listFromDoc(`parked.${key}`)
    expect(en.checklist.parkedLists[key]).toEqual(fromDoc.en)
    expect(pl.checklist.parkedLists[key]).toEqual(fromDoc.pl)
  })

  it('keeps the 112 line last in every parked list and leaves out the roadside steps', () => {
    const roadside = /hazard|triangle|vest|barrier/i
    for (const key of KEYS) {
      const list = en.checklist.parkedLists[key]
      expect(list.items.at(-1)).toBe(shared.get('call112')?.en)
      expect(pl.checklist.parkedLists[key].items.at(-1)).toBe(shared.get('call112')?.pl)
      expect(list.items.length).toBeLessThanOrEqual(4)
      for (const line of [list.first, ...list.items]) expect(line).not.toMatch(roadside)
    }
  })

  it('uses the labels from the copy doc', () => {
    const labels = new Map(
      rows('## Labels').map(([k = '', e = '', p = '']) => [unquote(k), { en: e, pl: p }]),
    )
    for (const key of [
      'firstLabel',
      'checklistTitle',
      'checklistBadge',
      'resolvedSummary',
    ] as const) {
      expect(en.checklist[key]).toBe(labels.get(key)?.en)
      expect(pl.checklist[key]).toBe(labels.get(key)?.pl)
    }
  })
})
