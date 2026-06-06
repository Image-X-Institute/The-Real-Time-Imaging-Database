-- Add JSONB extension columns for trial-specific dynamic fields.
-- Safe to run multiple times.

ALTER TABLE prescription
  ADD COLUMN IF NOT EXISTS extended_data JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE fraction
  ADD COLUMN IF NOT EXISTS extended_data JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE images
  ADD COLUMN IF NOT EXISTS extended_data JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN prescription.extended_data
  IS 'Future trial-specific prescription fields stored as JSONB.';

COMMENT ON COLUMN fraction.extended_data
  IS 'Future trial-specific fraction fields stored as JSONB.';

COMMENT ON COLUMN images.extended_data
  IS 'Future trial-specific image/path fields stored as JSONB.';
