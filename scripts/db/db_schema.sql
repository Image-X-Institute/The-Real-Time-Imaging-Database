DROP FUNCTION IF EXISTS meta_info_change_restrictor CASCADE;
DROP TABLE IF EXISTS meta_info;
DROP TABLE IF EXISTS dose;
-- DROP TABLE IF EXISTS respiratory_data;
DROP TABLE IF EXISTS images;
DROP INDEX IF EXISTS unique_fraction_index;
DROP TABLE IF EXISTS fraction;
DROP TABLE IF EXISTS prescription;
DROP TABLE IF EXISTS patient;

DROP FUNCTION IF EXISTS get_patient_id;
DROP FUNCTION IF EXISTS get_prescription_id_for_patient;
DROP FUNCTION IF EXISTS get_fraction_id_for_patient;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- this table would only have one row and exists to document the schema version, useful during migrations
CREATE TABLE meta_info
(
	ver_major INT NOT NULL,
	ver_minor INT NOT NULL,
	ver_release	VARCHAR NOT NULL
);

INSERT INTO meta_info (ver_major, ver_minor, ver_release) VALUES (0, 7, 'development');

CREATE FUNCTION meta_info_change_restrictor()
	RETURNS TRIGGER AS
$$
BEGIN
	RAISE EXCEPTION 'Cannot modify meta info table, since it stores the schema version of this DB instance';
END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER meta_info_change_trigger 
	BEFORE INSERT OR UPDATE OR DELETE ON "meta_info"
	EXECUTE PROCEDURE meta_info_change_restrictor();


CREATE TABLE patient 
(
	id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),  -- primary key, not the hspital/MRN patient ID
	-- TODO: revert to NOT NULL; modifying age to be NULL to allow anonymised data for now
	age INTEGER,  	-- age at the time of the start of treatment in years
	--v2: height INTEGER,  -- patient height in cm
	--v2: weight INTEGER,  -- patient weight during treatment in Kg
	gender CHAR, -- M = Male, F = Female, O = Others, NULL = Unknown
	clinical_diag TEXT,  -- free form clincal diagnosis field
	tumour_site VARCHAR NOT NULL,  -- organ/anatomical region where the tumour is located
	patient_trial_id VARCHAR NOT NULL,  -- the patient ID used in clinical trials
	clinical_trial VARCHAR NOT NULL,    -- the name/code of the clinical trial
	test_centre VARCHAR NOT NULL,       -- test centre where the patient recieved treatment
	centre_patient_no INTEGER NOT NULL, -- the patient's number within a centre	
	number_of_markers INTEGER, -- the number of gold markers implanted at tumour site
	--v2: respiratory_mc BOOLEAN,   -- respiratory motion control: is the patient holding breath or free breathing?
	avg_treatment_time INTERVAL,
	--v2: kim_result BOOLEAN,
	kim_accuracy FLOAT,
	row_entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- auto populated field indicating when the row was created
	CONSTRAINT unique_patient_trial_id UNIQUE (patient_trial_id)
);

-- TODO: add parameters for trial and centre to avoid mismatch for non unique trial patient ids.
CREATE OR REPLACE FUNCTION get_patient_id (pid VARCHAR)
    RETURNS TABLE(presc_id UUID) AS
$$
BEGIN
	RETURN QUERY
    SELECT id
    FROM patient 
    WHERE patient.patient_trial_id = pid;
END;
$$
LANGUAGE plpgsql;


CREATE TABLE prescription
(
	prescription_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
	patient_id UUID REFERENCES patient (id),
	LINAC_type VARCHAR NOT NULL,
	RT_plan_path VARCHAR,  -- NOT NULL
	RT_CT_path VARCHAR,  -- NOT NULL
	RT_structure_path VARCHAR,  -- NOT NULL
	RT_dose_path VARCHAR,  -- NOT NULL
	RT_MRI_path VARCHAR,
	RT_DVH_original_path VARCHAR,
	centroid_path VARCHAR
	--v2: beam_model VARCHAR
);

CREATE OR REPLACE FUNCTION get_prescription_id_for_patient (pid VARCHAR)
    RETURNS TABLE(presc_id UUID) AS
$$
BEGIN
	RETURN QUERY
    SELECT prescription_id
    FROM prescription, patient 
    WHERE prescription.patient_id = patient.id 
        AND patient.patient_trial_id = pid;
END;
$$
LANGUAGE plpgsql;


CREATE TABLE fraction
(
	fraction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
	prescription_id UUID REFERENCES prescription (prescription_id),
	fraction_date DATE,
	fraction_number INTEGER,
	num_gating_events INTEGER,
	fraction_name VARCHAR,
	--v2: breathing_technique VARCHAR,
	--v2: kim_threshold JSON,
	mvsdd FLOAT DEFAULT 0.0,
	kvsdd FLOAT DEFAULT 0.0
	--v2: kv_field_size FLOAT,
	--v2: dose_rate FLOAT,
	--v2: kim_starting_angle INTEGER,
	-- kim_result BOOLEAN
);

-- CREATE UNIQUE INDEX IF NOT EXISTS unique_fraction_index ON fraction
-- (
-- 	fraction_date, 
-- 	fraction_number, 
-- 	fraction_name
-- );

CREATE OR REPLACE FUNCTION get_fraction_id_for_patient (pid VARCHAR, fracname VARCHAR)
    RETURNS TABLE(presc_id UUID) AS
$$
BEGIN
	RETURN QUERY
    SELECT fraction_id
    FROM prescription, patient, fraction
    WHERE prescription.patient_id = patient.id 
		AND prescription.prescription_id = fraction.prescription_id
		AND fraction.fraction_name = fracname
        AND patient.patient_trial_id = pid;
END;
$$
LANGUAGE plpgsql;


CREATE TABLE images
(
	image_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
	fraction_id UUID REFERENCES fraction (fraction_id),
	kim_logs_path VARCHAR,  -- NOT NULL
	KV_images_path VARCHAR,  -- NOT NULL
	MV_images_path VARCHAR,  -- NOT NULL
	metrics_path VARCHAR,
	triangulation_path VARCHAR,
	trajectory_logs_path VARCHAR,
	DVH_track_path VARCHAR,
	DVH_no_track_path VARCHAR,
	DICOM_track_plan_path VARCHAR,
	DICOM_no_track_plan_path VARCHAR,
	respiratory_files_path VARCHAR,
	notes_path VARCHAR
	--v2: image_kv FLOAT NOT NULL,
	--v2: image_ma FLOAT NOT NULL,
	--v2: image_freq INTEGER NOT NULL
);

CREATE TABLE dose
(
	dose_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
	foreign_id UUID NOT NULL,  -- not explicitly a foreign key
	dose_level VARCHAR NOT NULL,
	is_tracked BOOLEAN,
	structure VARCHAR NOT NULL,
	plan VARCHAR NOT NULL,
	approved BOOLEAN,
	structure_volume FLOAT,
	dose_coverage FLOAT,
	min_dose FLOAT,
	max_dose FLOAT,
	mean_dose FLOAT,
	modal_dose FLOAT,
	median_dose FLOAT,
	std_dev FLOAT,
	d95 FLOAT,
	d100 FLOAT
);

-- CREATE TABLE respiratory_data
-- (
-- 	respiratory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
-- 	fraction_id UUID REFERENCES fraction (fraction_id),
-- 	f_number INTEGER NOT NULL,
-- 	wave INTEGER NOT NULL,
-- 	rpm_path VARCHAR NOT NULL
-- );
