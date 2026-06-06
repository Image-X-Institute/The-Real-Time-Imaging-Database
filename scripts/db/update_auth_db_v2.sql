-- Add trial metadata and storage markers for dynamic trial fields.
-- Safe to run multiple times.

ALTER TABLE trials
  ADD COLUMN IF NOT EXISTS rds_path VARCHAR;

COMMENT ON COLUMN trials.rds_path
  IS 'Root RDS path for this trial.';

UPDATE trials
SET trial_structure = jsonb_set(
  jsonb_set(
    trial_structure,
    '{prescription}',
    COALESCE(
      (
        SELECT jsonb_object_agg(
          key,
          CASE
            WHEN jsonb_typeof(value) = 'object' AND NOT (value ? 'storage')
              THEN value || '{"storage":"column"}'::jsonb
            ELSE value
          END
        )
        FROM jsonb_each(trial_structure->'prescription')
      ),
      '{}'::jsonb
    ),
    true
  ),
  '{fraction}',
  COALESCE(
    (
      SELECT jsonb_object_agg(
        key,
        CASE
          WHEN jsonb_typeof(value) = 'object' AND NOT (value ? 'storage')
            THEN value || '{"storage":"column"}'::jsonb
          ELSE value
        END
      )
      FROM jsonb_each(trial_structure->'fraction')
    ),
    '{}'::jsonb
  ),
  true
)
WHERE trial_structure IS NOT NULL;
