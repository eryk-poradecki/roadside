CREATE TABLE vehicles (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  make_model TEXT,
  year INTEGER,
  fuel_type TEXT CHECK (fuel_type IN
    ('petrol', 'diesel', 'lpg', 'hybrid', 'plug_in_hybrid', 'electric')),
  transmission TEXT CHECK (transmission IN ('manual', 'automatic')),
  tyre_size TEXT,
  spare_wheel TEXT CHECK (spare_wheel IN ('full_size', 'space_saver', 'repair_kit', 'none')),
  wheel_locks INTEGER CHECK (wheel_locks IN (0, 1)),
  lock_key_location TEXT,
  registration TEXT,
  assistance_insurer TEXT,
  assistance_phone TEXT,
  policy_number TEXT,
  is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
) STRICT;

CREATE UNIQUE INDEX one_default_vehicle ON vehicles(is_default) WHERE is_default = 1;
