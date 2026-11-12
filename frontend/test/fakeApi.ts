import { http, HttpResponse, type HttpHandler } from 'msw'
import type {
  AdviceRead,
  AiTurnRead,
  QuestionRead,
  ReplyCreate,
  TurnInputsRead,
} from '../src/api/aiTurns'
import type {
  IncidentCreate,
  IncidentPatch,
  IncidentRead,
  IncidentSummary,
} from '../src/api/incidents'
import type { DamageReportPatch, DamageReportRead } from '../src/api/damageReports'
import type { NearbyRead, PlaceRead } from '../src/api/nearby'
import type { PhotoRead, SamplePhoto } from '../src/api/photos'
import type { VehicleCreate, VehicleRead } from '../src/api/vehicles'

export const API = 'http://api.test'

/** The advice the fake assistant gives unless a test scripts something else. */
export const ADVICE: AdviceRead = {
  cause: 'A puncture in the rear left tyre',
  confidence: 'likely',
  alternatives: ['A damaged valve'],
  steps: ['Get everyone behind the barrier first', 'Call your assistance for a tyre change'],
  escalate_if: ['You smell fuel', 'The car starts rolling'],
  photo_observation: null,
  extra_categories: ['tyres'],
}

/** The clarifying question the fake assistant asks when a test scripts `{ ask: QUESTION }`. */
export const QUESTION: QuestionRead = {
  now: 'Get everyone behind the barrier',
  question: 'Is the car on the hard shoulder?',
  options: ['Yes, on the hard shoulder', 'No, off the road'],
}

/** A real-looking place, nearest first in `PLACES`. */
export const place = (
  osm_id: number,
  category: PlaceRead['category'],
  extra: Partial<PlaceRead> = {},
): PlaceRead => ({
  osm_type: 'node',
  osm_id,
  category,
  name: `Place ${String(osm_id)}`,
  lat: 52.23 + osm_id / 1000,
  lon: 21.01,
  distance_m: osm_id * 300,
  phone: null,
  opening_hours: null,
  ...extra,
})

/** What the fake map lookup finds unless a test scripts something else. */
export const PLACES: PlaceRead[] = [
  place(1, 'repair', { name: 'Auto Serwis Hoża', phone: '+48 22 000 00 01' }),
  place(2, 'tyres', { name: 'Wulkanizacja Nowa', opening_hours: '24/7' }),
  place(3, 'fuel', { name: null, opening_hours: 'Mo-Su 06:00-22:00' }),
  place(4, 'tyres', { name: 'Opony Max', opening_hours: 'Mo-Fr 08:00-18:00' }),
  place(5, 'fuel', { name: 'Orlen' }),
  place(6, 'charging', { name: 'GreenWay' }),
]

/** The sample photos the fake server bundles. */
export const SAMPLES: SamplePhoto[] = [
  {
    id: 'flat_tyre',
    url: '/api/v1/sample-photos/flat_tyre',
    title: 'Flat front tyre',
    credit: 'Someone, CC0',
  },
  {
    id: 'pothole',
    url: '/api/v1/sample-photos/pothole',
    title: 'Deep pothole in the road',
    credit: 'Someone else, CC0',
  },
]

/** One scripted `POST /photos` outcome: stored, or a problem response. */
export type PhotoScript = 'ok' | { status: number; reason: string }

/** One scripted `POST /nearby` outcome: the places found, or a problem response. */
export type NearbyScript = PlaceRead[] | { status: number; reason: string }

/** The letter the fake assistant drafts, with the backend template's placeholders. */
export const reportBody = (locale: 'pl' | 'en') =>
  locale === 'pl'
    ? '[Imię i nazwisko]\n[Adres]\nTel.: [Telefon]\n\n[Adresat: zarządca drogi]\n\nNr rej. WX 1234K. Wjechałem w głęboką wyrwę.\n\nRachunek: [Numer konta bankowego]\n\n[Imię i nazwisko]'
    : '[Your name]\n[Your address]\nPhone: [Your phone]\n\n[Addressee: road manager]\n\nRegistration WX 1234K. I hit a deep pothole.\n\nBank account: [Your bank account]\n\n[Your name]'

/** One scripted `POST /damage-report` outcome: drafted, or a problem response. */
export type ReportScript = 'ok' | { status: number; reason: string }

/** One scripted `POST /ai-turns` outcome: an advice, a question, or a problem response. */
export type TurnScript =
  | { advice: AdviceRead; urgent?: boolean }
  | { ask: QuestionRead }
  | { status: number; reason: string }

const NULLABLE_FIELDS = [
  'make_model',
  'year',
  'fuel_type',
  'transmission',
  'tyre_size',
  'spare_wheel',
  'wheel_locks',
  'lock_key_location',
  'registration',
  'assistance_insurer',
  'assistance_phone',
  'policy_number',
] as const

/** An in-memory stand-in for the backend that follows its vehicle and default-vehicle rules. */
export class FakeApi {
  vehicles: VehicleRead[] = []
  incidents: IncidentRead[] = []
  /** Bodies the app sent, for asserting on the wire format. */
  requests: { method: string; body: unknown }[] = []
  /** Every `POST /incidents` with its `Idempotency-Key`. */
  incidentRequests: { key: string | null; body: IncidentCreate }[] = []
  /** When set, the next create commits but its response is lost (a network error). */
  loseNextCreateResponse = false
  /** Outcomes of the next AI turns, in order; when empty, a turn returns `ADVICE`. */
  turnScript: TurnScript[] = []
  /** What reverse geocoding finds: like the server, the first AI turn stores it as the
   * located incident's `location_label` (ADR 0004). */
  geocodeLabel: string | null = null
  /** Every `POST /incidents/:id/ai-turns` with its body. */
  turnRequests: { incidentId: number; body: unknown }[] = []
  /** Outcomes of the next nearby lookups, in order; when empty, a lookup finds `PLACES`. */
  nearbyScript: NearbyScript[] = []
  /** Every `POST /incidents/:id/nearby` with its body. */
  nearbyRequests: { incidentId: number; body: { radius_km: number } }[] = []
  /** What `GET /config` answers; tests switch demo mode off to upload files. */
  config = { demo_mode: true, vision_enabled: false }
  /** Each incident's damage report, by incident id. */
  reports = new Map<number, DamageReportRead>()
  /** Outcomes of the next report drafts, in order; when empty, a draft is stored. */
  reportScript: ReportScript[] = []
  /** Every request to `/incidents/:id/damage-report`, with its body. */
  reportRequests: { method: string; incidentId: number; body: unknown }[] = []
  /** How many times the app read a damage report. */
  reportGets = 0
  /** While set, every report draft waits for it before answering. */
  reportGate: Promise<void> | null = null
  /** Outcomes of the next photo uploads, in order; when empty, an upload is stored. */
  photoScript: PhotoScript[] = []
  /** While set, every photo upload waits for it before answering. */
  photoGate: Promise<void> | null = null
  /** Every `POST /incidents/:id/photos`: a file (with its name and type) or a sample id. */
  photoRequests: {
    incidentId: number
    file?: { name: string; type: string }
    sampleId?: string
  }[] = []
  private nextPhotoId = 1
  private nextTurnId = 1
  private nextId = 1
  private nextIncidentId = 1
  private keys = new Map<string, number>()

  reset() {
    this.vehicles = []
    this.incidents = []
    this.requests = []
    this.incidentRequests = []
    this.loseNextCreateResponse = false
    this.turnScript = []
    this.turnRequests = []
    this.geocodeLabel = null
    this.nearbyScript = []
    this.nearbyRequests = []
    this.config = { demo_mode: true, vision_enabled: false }
    this.photoScript = []
    this.photoGate = null
    this.reports = new Map()
    this.reportScript = []
    this.reportRequests = []
    this.reportGate = null
    this.reportGets = 0
    this.photoRequests = []
    this.nextPhotoId = 1
    this.nextTurnId = 1
    this.nextId = 1
    this.nextIncidentId = 1
    this.keys.clear()
  }

  /** `extra` overrides server-set fields, e.g. `created_at` or `status`. */
  seedIncident(body: IncidentCreate, extra: Partial<IncidentRead> = {}): IncidentRead {
    const incident = { ...this.createIncident(body), ...extra }
    this.incidents = this.incidents.map((i) => (i.id === incident.id ? incident : i))
    return incident
  }

  private createIncident(body: IncidentCreate): IncidentRead {
    const now = '2026-11-10T10:00:00.000Z'
    const location = body.location
      ? {
          lat: body.location.lat,
          lon: body.location.lon,
          accuracy_m: body.location.accuracy_m ?? null,
        }
      : null
    const incident: IncidentRead = {
      id: this.nextIncidentId++,
      problem_type: body.problem_type,
      status: 'open',
      situation: body.situation ?? 'on_road',
      vehicle_id: body.vehicle_id ?? null,
      note: body.note ?? null,
      location,
      location_label: null,
      created_at: now,
      updated_at: now,
      photos: [],
      ai_turns: [],
      nearby: null,
      damage_report_status: null,
    }
    this.incidents.push(incident)
    return incident
  }

  /** A stored advice turn, for seeding an incident that was already answered. */
  adviceTurn(
    advice: AdviceRead = ADVICE,
    locale: 'pl' | 'en' = 'en',
    extra: Partial<AiTurnRead> = {},
  ): AiTurnRead {
    return {
      id: this.nextTurnId++,
      seq: 1,
      kind: 'advice',
      created_at: '2026-11-10T10:00:30.000Z',
      urgent: false,
      question: null,
      advice,
      reply: null,
      inputs: null,
      locale,
      prompt_version: 'v1',
      provider: 'fake',
      model: 'fake-model',
      ...extra,
    }
  }

  /** A stored clarifying question. */
  questionTurn(question: QuestionRead = QUESTION, extra: Partial<AiTurnRead> = {}): AiTurnRead {
    return { ...this.adviceTurn(), kind: 'question', question, advice: null, ...extra }
  }

  /** A stored reply: the driver's, so it carries no model fields. */
  replyTurn(reply: ReplyCreate, extra: Partial<AiTurnRead> = {}): AiTurnRead {
    return {
      id: this.nextTurnId++,
      seq: 1,
      kind: 'reply',
      created_at: '2026-11-10T10:00:40.000Z',
      urgent: null,
      question: null,
      advice: null,
      reply: { option: reply.option ?? null, text: reply.text ?? null, skip: reply.skip === true },
      inputs: null,
      locale: null,
      prompt_version: null,
      provider: null,
      model: null,
      ...extra,
    }
  }

  /** What the server freezes next to a model turn ("Answered for …"), from the incident now. */
  inputsFor(incident: IncidentRead): TurnInputsRead {
    const v = this.vehicles.find((x) => x.id === incident.vehicle_id)
    return {
      vehicle: v
        ? {
            name: v.name,
            make_model: v.make_model,
            year: v.year,
            fuel_type: v.fuel_type,
            transmission: v.transmission,
            tyre_size: v.tyre_size,
            spare_wheel: v.spare_wheel,
            wheel_locks: v.wheel_locks,
            lock_key_location: v.lock_key_location,
            has_assistance: v.assistance_phone !== null,
            assistance_insurer: v.assistance_phone !== null ? v.assistance_insurer : null,
          }
        : null,
      problem_type: incident.problem_type,
      note: incident.note,
      local_time: '2026-11-10 11:00',
      dark: false,
      road_class: 'unknown',
      settlement: 'unknown',
      situation: incident.situation,
      photo_ids_seen: [],
      photos_not_sent: 0,
    }
  }

  seed(body: VehicleCreate): VehicleRead {
    return this.create(body)
  }

  private build(id: number, body: VehicleCreate, isDefault: boolean): VehicleRead {
    const now = '2026-11-10T10:00:00.000Z'
    const vehicle = {
      id,
      name: body.name,
      is_default: isDefault,
      created_at: now,
      updated_at: now,
    } as VehicleRead
    for (const field of NULLABLE_FIELDS) Object.assign(vehicle, { [field]: body[field] ?? null })
    return vehicle
  }

  private create(body: VehicleCreate): VehicleRead {
    const isDefault = body.is_default ?? !this.vehicles.some((v) => v.is_default)
    if (isDefault) this.vehicles = this.vehicles.map((v) => ({ ...v, is_default: false }))
    const vehicle = this.build(this.nextId++, body, isDefault)
    this.vehicles.push(vehicle)
    return vehicle
  }

  private sorted(): VehicleRead[] {
    return [...this.vehicles].sort(
      (a, b) => Number(b.is_default) - Number(a.is_default) || a.id - b.id,
    )
  }

  handlers(): HttpHandler[] {
    const notFound = () => problem(404, 'not_found', 'Vehicle 99 not found, internal detail')
    return [
      http.get(`${API}/api/v1/config`, () =>
        HttpResponse.json({
          ...this.config,
          max_photos: 5,
          max_photo_bytes: 1000,
          sample_photos: SAMPLES,
        }),
      ),
      http.get(`${API}/api/v1/vehicles`, () => HttpResponse.json(this.sorted())),
      http.post(`${API}/api/v1/vehicles`, async ({ request }) => {
        const body = (await request.json()) as VehicleCreate
        this.requests.push({ method: 'POST', body })
        return HttpResponse.json(this.create(body), { status: 201 })
      }),
      http.get(`${API}/api/v1/vehicles/:id`, ({ params }) => {
        const found = this.vehicles.find((v) => v.id === Number(params.id))
        return found ? HttpResponse.json(found) : notFound()
      }),
      http.put(`${API}/api/v1/vehicles/:id`, async ({ params, request }) => {
        const body = (await request.json()) as VehicleCreate
        this.requests.push({ method: 'PUT', body })
        const current = this.vehicles.find((v) => v.id === Number(params.id))
        if (!current) return notFound()
        const isDefault = body.is_default ?? current.is_default
        if (isDefault && !current.is_default)
          this.vehicles = this.vehicles.map((v) => ({ ...v, is_default: false }))
        const updated = this.build(current.id, body, isDefault)
        this.vehicles = this.vehicles.map((v) => (v.id === current.id ? updated : v))
        return HttpResponse.json(updated)
      }),
      http.post(`${API}/api/v1/incidents`, async ({ request }) => {
        const body = (await request.json()) as IncidentCreate
        const key = request.headers.get('Idempotency-Key')
        this.incidentRequests.push({ key, body })
        const existing = key === null ? undefined : this.keys.get(key)
        if (existing !== undefined)
          return HttpResponse.json(this.incidents.find((i) => i.id === existing))
        if (body.vehicle_id != null && !this.vehicles.some((v) => v.id === body.vehicle_id))
          return problem(422, 'validation_error', 'Unknown vehicle')
        const incident = this.createIncident(body)
        if (key !== null) this.keys.set(key, incident.id)
        if (this.loseNextCreateResponse) {
          this.loseNextCreateResponse = false
          return HttpResponse.error()
        }
        return HttpResponse.json(incident, {
          status: 201,
          headers: { Location: `/api/v1/incidents/${String(incident.id)}` },
        })
      }),
      http.get(`${API}/api/v1/incidents`, ({ request }) => {
        const query = new URL(request.url).searchParams
        const status = query.get('status')
        const limit = Number(query.get('limit') ?? 20)
        const offset = Number(query.get('offset') ?? 0)
        const matching = this.incidents
          .filter((i) => status === null || i.status === status)
          .sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id)
        const items: IncidentSummary[] = matching.slice(offset, offset + limit).map((i) => ({
          id: i.id,
          problem_type: i.problem_type,
          status: i.status,
          created_at: i.created_at,
          location: i.location ? { lat: i.location.lat, lon: i.location.lon } : null,
          location_label: i.location_label,
          vehicle_id: i.vehicle_id,
          damage_report_status: this.reports.get(i.id)?.status ?? null,
        }))
        return HttpResponse.json({ items, total: matching.length, limit, offset })
      }),
      http.patch(`${API}/api/v1/incidents/:id`, async ({ params, request }) => {
        const body = (await request.json()) as IncidentPatch
        this.requests.push({ method: 'PATCH', body })
        const current = this.incidents.find((i) => i.id === Number(params.id))
        if (!current) return problem(404, 'not_found', 'Incident not found')
        if (body.vehicle_id != null && !this.vehicles.some((v) => v.id === body.vehicle_id))
          return problem(422, 'validation_error', 'Unknown vehicle')
        // The types forbid null here, but a buggy client could still send it.
        const raw = body as Record<string, unknown>
        if (raw.status === null || raw.problem_type === null || raw.situation === null)
          return problem(422, 'validation_error', "Can't be null")
        const { location, note, ...rest } = body
        const updated: IncidentRead = {
          ...current,
          ...rest,
          updated_at: '2026-11-10T11:00:00.000Z',
        }
        if (note !== undefined) updated.note = note?.trim() || null
        if (location !== undefined) {
          updated.location = location
            ? { lat: location.lat, lon: location.lon, accuracy_m: location.accuracy_m ?? null }
            : null
          // Like the server: the label goes only with a point that actually moved.
          const old = current.location
          const moved =
            old?.lat !== updated.location?.lat ||
            old?.lon !== updated.location?.lon ||
            old?.accuracy_m !== updated.location?.accuracy_m
          if (moved) {
            updated.location_label = null
            updated.nearby = null
          }
        }
        this.incidents = this.incidents.map((i) => (i.id === current.id ? updated : i))
        return HttpResponse.json(updated)
      }),
      http.delete(`${API}/api/v1/incidents/:id`, ({ params }) => {
        const before = this.incidents.length
        this.incidents = this.incidents.filter((i) => i.id !== Number(params.id))
        this.reports.delete(Number(params.id))
        return this.incidents.length === before
          ? problem(404, 'not_found', 'Incident not found')
          : new HttpResponse(null, { status: 204 })
      }),
      http.post(`${API}/api/v1/incidents/:id/ai-turns`, async ({ params, request }) => {
        const incidentId = Number(params.id)
        const body = (await request.json()) as { locale: 'pl' | 'en'; reply?: ReplyCreate }
        this.turnRequests.push({ incidentId, body })
        let incident = this.incidents.find((i) => i.id === incidentId)
        if (!incident) return problem(404, 'not_found', 'Incident not found')
        if (incident.ai_turns.some((t) => t.kind === 'advice'))
          return problem(409, 'advice_exists', 'The AI answer is complete')
        const open = incident.ai_turns.at(-1)?.kind === 'question'
        if (open && !body.reply) return problem(409, 'reply_required', 'Reply first')
        if (!open && body.reply) return problem(409, 'no_open_question', 'Nothing to reply to')
        const label = this.geocodeLabel
        if (label && incident.location && !incident.location_label) {
          const located: IncidentRead = { ...incident, location_label: label }
          this.incidents = this.incidents.map((i) => (i.id === incidentId ? located : i))
          incident = located
        }
        const append = (turn: AiTurnRead) => {
          const current = incident as IncidentRead
          const updated = {
            ...current,
            ai_turns: [...current.ai_turns, { ...turn, seq: current.ai_turns.length + 1 }],
          }
          this.incidents = this.incidents.map((i) => (i.id === incidentId ? updated : i))
          incident = updated
          return updated.ai_turns.at(-1) as AiTurnRead
        }
        // Like the server: the reply is stored first and stays if the turn then fails.
        if (body.reply) append(this.replyTurn(body.reply))
        const next = this.turnScript.shift() ?? { advice: ADVICE }
        if ('reason' in next) return problem(next.status, next.reason, 'internal detail')
        const extra = { inputs: this.inputsFor(incident) }
        const turn =
          'ask' in next
            ? this.questionTurn(next.ask, { ...extra, locale: body.locale })
            : this.adviceTurn(next.advice, body.locale, { ...extra, urgent: next.urgent ?? false })
        return HttpResponse.json(append(turn), { status: 201 })
      }),
      http.get(`${API}/api/v1/incidents/:id/damage-report`, ({ params }) => {
        this.reportGets++
        const report = this.reports.get(Number(params.id))
        return report ? HttpResponse.json(report) : problem(404, 'not_found', 'No report')
      }),
      http.post(`${API}/api/v1/incidents/:id/damage-report`, async ({ params, request }) => {
        const incidentId = Number(params.id)
        const body = (await request.json()) as { locale?: 'pl' | 'en'; replace?: boolean }
        this.reportRequests.push({ method: 'POST', incidentId, body })
        if (this.reportGate) await this.reportGate
        const incident = this.incidents.find((i) => i.id === incidentId)
        if (!incident) return problem(404, 'not_found', 'Incident not found')
        if (incident.problem_type !== 'pothole_damage')
          return problem(422, 'not_pothole_damage', 'Not a pothole')
        const existing = this.reports.get(incidentId)
        if (existing && !body.replace) return problem(409, 'damage_report_exists', 'Exists')
        const next = this.reportScript.shift() ?? 'ok'
        // Like the server: a failed draft stores nothing.
        if (next !== 'ok') return problem(next.status, next.reason, 'internal detail')
        const locale = body.locale ?? 'pl'
        const report: DamageReportRead = {
          status: 'draft',
          locale,
          body: reportBody(locale),
          created_at: existing?.created_at ?? '2026-11-10T10:05:00.000Z',
          updated_at: `2026-11-10T10:05:0${String(this.reportRequests.length % 10)}.000Z`,
        }
        this.reports.set(incidentId, report)
        return HttpResponse.json(report, { status: existing ? 200 : 201 })
      }),
      http.patch(`${API}/api/v1/incidents/:id/damage-report`, async ({ params, request }) => {
        const incidentId = Number(params.id)
        const body = (await request.json()) as DamageReportPatch
        this.reportRequests.push({ method: 'PATCH', incidentId, body })
        const current = this.reports.get(incidentId)
        if (!current) return problem(404, 'not_found', 'No report')
        const updated = { ...current, ...body, updated_at: '2026-11-10T11:00:00.000Z' }
        this.reports.set(incidentId, updated)
        return HttpResponse.json(updated)
      }),
      http.post(`${API}/api/v1/incidents/:id/nearby`, async ({ params, request }) => {
        const incidentId = Number(params.id)
        const body = (await request.json()) as { radius_km: number }
        this.nearbyRequests.push({ incidentId, body })
        const incident = this.incidents.find((i) => i.id === incidentId)
        if (!incident) return problem(404, 'not_found', 'Incident not found')
        if (!incident.location) return problem(409, 'no_location', 'No location')
        const next = this.nearbyScript.shift() ?? PLACES
        // Like the server: a failure keeps the previous snapshot.
        if ('reason' in next) return problem(next.status, next.reason, 'internal detail')
        const nearby: NearbyRead = {
          status: next.length > 0 ? 'found' : 'none',
          places: next,
          radius_km: body.radius_km,
          fetched_at: '2026-11-10T10:00:20.000Z',
        }
        this.incidents = this.incidents.map((i) => (i.id === incidentId ? { ...i, nearby } : i))
        return HttpResponse.json(nearby)
      }),
      http.post(`${API}/api/v1/incidents/:id/photos`, async ({ params, request }) => {
        const incidentId = Number(params.id)
        const multipart = (request.headers.get('Content-Type') ?? '').startsWith(
          'multipart/form-data',
        )
        if (multipart) {
          // Read from the raw body: undici's formData() can't build a File under jsdom.
          const part = /name="file"; filename="([^"]*)"\r\nContent-Type: ([^\r]*)/.exec(
            await request.text(),
          )
          if (!part) return problem(422, 'validation_error', 'No file')
          this.photoRequests.push({
            incidentId,
            file: { name: part[1] ?? '', type: part[2] ?? '' },
          })
        } else {
          const body = (await request.json()) as { sample_id: string }
          this.photoRequests.push({ incidentId, sampleId: body.sample_id })
        }
        if (this.photoGate) await this.photoGate
        const incident = this.incidents.find((i) => i.id === incidentId)
        if (!incident) return problem(404, 'not_found', 'Incident not found')
        // Like the server: demo mode refuses files.
        if (multipart && this.config.demo_mode)
          return problem(403, 'demo_uploads_disabled', 'Demo mode')
        if (incident.photos.length >= 5) return problem(409, 'photo_limit', 'Five photos')
        const next = this.photoScript.shift() ?? 'ok'
        if (next !== 'ok') return problem(next.status, next.reason, 'internal detail')
        const id = this.nextPhotoId++
        const photo: PhotoRead = {
          id,
          url: `/api/v1/photos/${String(id)}`,
          content_type: 'image/jpeg',
          width: 1600,
          height: 1200,
          created_at: '2026-11-10T10:00:10.000Z',
        }
        this.incidents = this.incidents.map((i) =>
          i.id === incidentId ? { ...i, photos: [...i.photos, photo] } : i,
        )
        return HttpResponse.json(photo, { status: 201, headers: { Location: photo.url } })
      }),
      http.delete(`${API}/api/v1/photos/:id`, ({ params }) => {
        const id = Number(params.id)
        const owner = this.incidents.find((i) => i.photos.some((p) => p.id === id))
        if (!owner) return problem(404, 'not_found', 'Photo not found')
        this.incidents = this.incidents.map((i) =>
          i.id === owner.id ? { ...i, photos: i.photos.filter((p) => p.id !== id) } : i,
        )
        return new HttpResponse(null, { status: 204 })
      }),
      http.get(`${API}/api/v1/incidents/:id`, ({ params }) => {
        const found = this.incidents.find((i) => i.id === Number(params.id))
        return found
          ? HttpResponse.json({
              ...found,
              damage_report_status: this.reports.get(found.id)?.status ?? null,
            })
          : problem(404, 'not_found', 'Incident not found')
      }),
      http.delete(`${API}/api/v1/vehicles/:id`, ({ params }) => {
        const before = this.vehicles.length
        this.vehicles = this.vehicles.filter((v) => v.id !== Number(params.id))
        if (this.vehicles.length === before) return notFound()
        // The incident outlives its vehicle (ON DELETE SET NULL).
        this.incidents = this.incidents.map((i) =>
          i.vehicle_id === Number(params.id) ? { ...i, vehicle_id: null } : i,
        )
        return new HttpResponse(null, { status: 204 })
      }),
    ]
  }
}

export function problem(status: number, reason: string, detail: string) {
  return HttpResponse.json(
    { type: 'about:blank', title: 'Error', status, detail, instance: '/x', reason },
    { status, headers: { 'Content-Type': 'application/problem+json' } },
  )
}

export const fakeApi = new FakeApi()
