ALTER TABLE vehicles ADD COLUMN demo_profile TEXT;
CREATE UNIQUE INDEX vehicles_demo_profile ON vehicles (demo_profile);
