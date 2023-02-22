-- This script is only meant to be run on an instance of clinical trial database
-- to transform it into a staging area for accepting uploads from the content
-- uploader or a similar client tool. The contents of this staging database 
-- would then be moved to the actual instance of the database.

CREATE TABLE uploads
(
	id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    uploader VARCHAR NOT NULL,
    upload_host VARCHAR,
    data_server_host VARCHAR,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE patient ADD COLUMN upload_id UUID REFERENCES uploads(id);

-- allow multiple entries for a patient trial id for different uploads
ALTER TABLE patient DROP CONSTRAINT unique_patient_trial_id;  