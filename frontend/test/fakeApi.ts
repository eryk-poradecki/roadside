import { http, HttpResponse, type HttpHandler } from 'msw'
import type { IncidentCreate, IncidentRead } from '../src/api/incidents'
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
  private keys = new Map<string, number>()

  reset() {
    this.vehicles = []
    this.incidents = []
    this.requests = []
    this.incidentRequests = []
    this.loseNextCreateResponse = false
    this.nextId = 1
    this.keys.clear()
  }

  seedIncident(body: IncidentCreate): IncidentRead {
    return this.createIncident(body)
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
      id: this.incidents.length + 1,
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
      http.get(`${API}/api/v1/incidents/:id`, ({ params }) => {
        const found = this.incidents.find((i) => i.id === Number(params.id))
        return found ? HttpResponse.json(found) : problem(404, 'not_found', 'Incident not found')
      }),
      http.delete(`${API}/api/v1/vehicles/:id`, ({ params }) => {
        const before = this.vehicles.length
        this.vehicles = this.vehicles.filter((v) => v.id !== Number(params.id))
        return this.vehicles.length === before
          ? notFound()
          : new HttpResponse(null, { status: 204 })
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
