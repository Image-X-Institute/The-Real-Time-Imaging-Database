ALTER TABLE prescription 
    RENAME COLUMN rt_plan_path TO rt_plan_pres;

ALTER TABLE prescription 
    RENAME COLUMN rt_ct_path TO rt_ct_pres;

ALTER TABLE prescription 
    RENAME COLUMN rt_structure_path TO rt_structure_pres;

ALTER TABLE prescription
    ALTER COLUMN rt_dose_path TO rt_dose_pres;

ALTER TABLE prescription
    ALTER COLUMN rt_mri_path TO rt_mri_pres;

ALTER TABLE prescription
    ALTER COLUMN RT_DVH_original_path TO planned_dvh_pres;

ALTER TABLE prescription 
  ADD COLUMN centroid_pres VARCHAR;

ALTER TABLE prescription 
  ADD COLUMN planned_dicom_pres VARCHAR;

ALTER TABLE images
  ADD COLUMN rt_ct_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN rt_dose_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN rt_plan_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN rt_structure_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN centroid_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN kim_threshold VARCHAR;

ALTER TABLE images
  ADD COLUMN planned_dvh_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN planned_dicom_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN rpm_path VARCHAR;

-- ALTER TABLE images
--   ADD COLUMN fluoro_images_path VARCHAR;

-- ALTER TABLE images
--   ADD COLUMN cbct_images_path VARCHAR;

-- ALTER TABLE images
--   ADD COLUMN timepoint_ct_path VARCHAR;

-- ALTER TABLE images
--   ADD COLUMN pet_iamges_path VARCHAR;