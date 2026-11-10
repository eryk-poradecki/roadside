-- Location context (ADR 0004): derived from one Nominatim call at the first AI turn and
-- cached here. NULL means not looked up yet; a new location clears it.
ALTER TABLE incidents ADD COLUMN road_class TEXT CHECK (road_class IN
  ('motorway_expressway', 'main_road', 'local_street', 'unknown'));
ALTER TABLE incidents ADD COLUMN settlement TEXT CHECK (settlement IN
  ('city', 'town', 'village', 'countryside', 'unknown'));
