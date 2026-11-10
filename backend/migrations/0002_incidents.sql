CREATE TABLE incidents (
  id INTEGER PRIMARY KEY,
  problem_type TEXT NOT NULL CHECK (problem_type IN
    ('flat_tyre', 'flat_battery', 'out_of_fuel', 'pothole_damage', 'other')),
  status TEXT NOT NULL CHECK (status IN ('open', 'resolved')),
  -- The incident outlives its vehicle (ADR 0001).
  vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE SET NULL,
  note TEXT,
  lat REAL CHECK (lat BETWEEN -90 AND 90),
  lon REAL CHECK (lon BETWEEN -180 AND 180),
  accuracy_m REAL CHECK (accuracy_m >= 0),
  location_label TEXT,
  -- Light idempotency on create (ADR 0005): the key lives as long as the incident.
  idempotency_key TEXT UNIQUE,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK ((lat IS NULL) = (lon IS NULL)),
  CHECK (accuracy_m IS NULL OR lat IS NOT NULL)
) STRICT;

CREATE INDEX incidents_created_at ON incidents(created_at);
CREATE INDEX incidents_vehicle_id ON incidents(vehicle_id);
