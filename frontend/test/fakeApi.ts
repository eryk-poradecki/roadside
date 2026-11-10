import { http, HttpResponse, type HttpHandler } from 'msw'
import type {
  IncidentCreate,
  IncidentPatch,
  IncidentRead,
  IncidentSummary,
} from '../src/api/incidents'
import type { VehicleCreate, VehicleRead } from '../src/api/vehicles'

export const API = 'http://api.test'

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
  private nextId = 1
  private nextIncidentId = 1
  private keys = new Map<string, number>()

  reset() {
    this.vehicles = []
    this.incidents = []
    this.requests = []
    this.incidentRequests = []
    this.loseNextCreateResponse = false
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
      vehicle_id: body.vehicle_id ?? null,
      note: body.note ?? null,
      location,
      location_label: null,
      created_at: now,
      updated_at: now,
    }
    this.incidents.push(incident)
    return incident
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
          demo_mode: true,
          vision_enabled: false,
          max_photos: 5,
          max_photo_bytes: 1000,
          sample_photos: [],
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
        if (raw.status === null || raw.problem_type === null)
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
          if (moved) updated.location_label = null
        }
        this.incidents = this.incidents.map((i) => (i.id === current.id ? updated : i))
        return HttpResponse.json(updated)
      }),
      http.delete(`${API}/api/v1/incidents/:id`, ({ params }) => {
        const before = this.incidents.length
        this.incidents = this.incidents.filter((i) => i.id !== Number(params.id))
        return this.incidents.length === before
          ? problem(404, 'not_found', 'Incident not found')
          : new HttpResponse(null, { status: 204 })
      }),
      http.get(`${API}/api/v1/incidents/:id`, ({ params }) => {
        const found = this.incidents.find((i) => i.id === Number(params.id))
        return found ? HttpResponse.json(found) : problem(404, 'not_found', 'Incident not found')
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
