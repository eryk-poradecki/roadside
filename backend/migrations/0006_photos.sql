-- Photos (ADR 0002): the bytes are files in UPLOAD_DIR, one row per file. The cascade removes
-- rows only; the incident service removes the files.
CREATE TABLE incident_photos (
  id INTEGER PRIMARY KEY,
  incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  -- Server-generated (a UUID and the extension), never the client's file name.
  stored_name TEXT NOT NULL UNIQUE,
  content_type TEXT NOT NULL CHECK (content_type IN ('image/jpeg', 'image/png', 'image/webp')),
  size_bytes INTEGER NOT NULL CHECK (size_bytes > 0),
  width INTEGER NOT NULL CHECK (width > 0),
  height INTEGER NOT NULL CHECK (height > 0),
  -- The bundled sample it was copied from in demo mode; part of the replay key (#58).
  sample_id TEXT,
  created_at TEXT NOT NULL
) STRICT;

CREATE INDEX incident_photos_incident_id ON incident_photos(incident_id, id);
