-- The damage report (ADR 0009): a draft letter to the road manager, at most one per incident.
-- The body is the rendered letter the driver edits; the narrative the model wrote and what it
-- was written from are kept beside it, as for an AI turn. The driver's own details are never
-- stored: they fill the body's placeholders in the browser.
CREATE TABLE damage_reports (
  incident_id INTEGER PRIMARY KEY REFERENCES incidents(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('draft', 'sent')),
  locale TEXT NOT NULL CHECK (locale IN ('pl', 'en')),
  body TEXT NOT NULL,
  -- The validated model output: {description, damage_summary}.
  narrative TEXT NOT NULL CHECK (json_valid(narrative)),
  inputs TEXT NOT NULL CHECK (json_valid(inputs)),
  prompt_version TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
) STRICT;
