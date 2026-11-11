-- The nearby snapshot (ADR 0004, 0005): the last successful lookup for an incident, replaced
-- only by another success and cleared when the location changes.
CREATE TABLE incident_nearby (
  incident_id INTEGER PRIMARY KEY REFERENCES incidents(id) ON DELETE CASCADE,
  -- At most 20 places, nearest first: a JSON array of the API's place shape.
  places TEXT NOT NULL CHECK (json_valid(places) AND json_type(places) = 'array'),
  radius_km INTEGER NOT NULL CHECK (radius_km BETWEEN 1 AND 25),
  fetched_at TEXT NOT NULL,
  -- The Overpass endpoint that answered.
  source TEXT NOT NULL
) STRICT;
