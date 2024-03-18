-- Active: 1685670005858@@127.0.0.1@5432@testdb
ALTER TABLE prescription 
  RENAME COLUMN rt_ct_path TO rt_ct_pres;

ALTER TABLE prescription
  ALTER COLUMN rt_dose_path TO rt_dose_pres;

ALTER TABLE prescription
  ALTER COLUMN rt_mri_path TO rt_mri_pres;

ALTER TABLE prescription 
  RENAME COLUMN rt_plan_path TO rt_plan_pres;

ALTER TABLE prescription 
  RENAME COLUMN rt_structure_path TO rt_structure_pres;

ALTER TABLE prescription
  ALTER COLUMN RT_DVH_original_path TO planned_dvh_pres;

ALTER TABLE prescription
  ADD COLUMN planned_dicom_pres VARCHAR;

ALTER TABLE prescription 
  ADD COLUMN centroid_pres VARCHAR;

ALTER TABLE prescription
  ADD COLUMN magik_visual VARCHAR;

ALTER TABLE prescription
  ADD COLUMN magik_model VARCHAR;

ALTER TABLE prescription
  ADD COLUMN marker_offsets VARCHAR;

ALTER TABLE prescription
  ADD COLUMN cardio_ct VARCHAR;

-- ADD COLUMN at fraction/image level
ALTER TABLE images
  ADD COLUMN rt_ct_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN rt_dose_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN rt_mri_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN rt_plan_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN rt_structure_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN centroid_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN planned_dvh_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN planned_dicom_fraction VARCHAR;

ALTER TABLE images
  ADD COLUMN scan_file VARCHAR;

ALTER TABLE images
  ADD COLUMN rpm_path VARCHAR;

ALTER TABLE images
  ADD COLUMN kim_threshold VARCHAR;

ALTER TABLE images
  ADD COLUMN couch_shift_file VARCHAR;

ALTER TABLE images
  ADD COLUMN cbct_images_path VARCHAR;

ALTER TABLE images
  ADD COLUMN contour_files_path VARCHAR;

ALTER TABLE images
  ADD COLUMN fluoro_images_path VARCHAR;

ALTER TABLE images
  ADD COLUMN pet_image_path VARCHAR;

ALTER TABLE images
  ADD COLUMN pet_3d_attenuation_ct_path VARCHAR;

ALTER TABLE images
  ADD COLUMN pet_listmode_path VARCHAR;

ALTER TABLE images
  ADD COLUMN pet_4d_attenuation_ct_path VARCHAR;

ALTER TABLE images
  ADD COLUMN petct_files VARCHAR;

ALTER TABLE images
  ADD COLUMN spect_image_path VARCHAR;

ALTER TABLE images
  ADD COLUMN spect_3d_attenuation_ct_path VARCHAR;

ALTER TABLE images
  ADD COLUMN timepoint_ct_path VARCHAR;

ALTER TABLE images
  ADD COLUMN magik_logs VARCHAR;

ALTER TABLE images
  ADD COLUMN projections VARCHAR;
