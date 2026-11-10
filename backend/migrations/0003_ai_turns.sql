-- The AI answer, append-only (ADR 0004): rows are inserted, never updated.
CREATE TABLE ai_turns (
  id INTEGER PRIMARY KEY,
  incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  seq INTEGER NOT NULL CHECK (seq >= 1),
  kind TEXT NOT NULL CHECK (kind IN ('question', 'reply', 'advice')),
  -- The validated model output, or the driver's reply.
  payload TEXT NOT NULL CHECK (json_valid(payload)),
  -- Model rows only: what the turn was produced from, and by what.
  inputs TEXT CHECK (inputs IS NULL OR json_valid(inputs)),
  locale TEXT CHECK (locale IN ('pl', 'en')),
  prompt_version TEXT,
  provider TEXT,
  model TEXT,
  created_at TEXT NOT NULL,
  UNIQUE (incident_id, seq),
  CHECK ((kind = 'reply') = (inputs IS NULL)),
  CHECK ((kind = 'reply') = (locale IS NULL)),
  CHECK ((kind = 'reply') = (prompt_version IS NULL)),
  CHECK ((kind = 'reply') = (provider IS NULL)),
  CHECK ((kind = 'reply') = (model IS NULL))
) STRICT;

-- At most one advice per incident: it closes the AI answer.
CREATE UNIQUE INDEX one_advice_per_incident ON ai_turns(incident_id) WHERE kind = 'advice';
