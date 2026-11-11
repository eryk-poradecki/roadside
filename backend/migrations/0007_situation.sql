-- Situation (#93): where the car stands, chosen by the driver in the help sheet. Never inferred
-- from the location, and on the road unless the driver says parked: the full roadside checklist
-- is the safe default.
ALTER TABLE incidents ADD COLUMN situation TEXT NOT NULL DEFAULT 'on_road'
  CHECK (situation IN ('on_road', 'parked'));
