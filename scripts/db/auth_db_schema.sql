DROP TABLE IF EXISTS acl_roles;
DROP TABLE IF EXISTS trial_site_mapping;
DROP TABLE IF EXISTS trials;
DROP TABLE IF EXISTS treatment_sites;
DROP TABLE IF EXISTS token_details;
DROP SEQUENCE IF EXISTS jtid_sequence;


CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SEQUENCE jtid_sequence START WITH 100 INCREMENT BY 1 NO MAXVALUE;

CREATE TABLE token_details
(
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_subject VARCHAR NOT NULL,
    subject_email VARCHAR,
    audience VARCHAR NOT NULL,
    issued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP + INTERVAL '365 days',
    jwt_id TEXT NOT NULL DEFAULT 'JTID00'||nextval('jtid_sequence')::TEXT,
    is_enabled BOOLEAN DEFAULT FALSE,
    hashed_secret VARCHAR,
    host_locked BOOLEAN DEFAULT FALSE,  -- denotes if the token should only be allowed for requests from host_address
    host_address VARCHAR,
    reason TEXT
);

CREATE TABLE trials
(
    trial_id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_name VARCHAR NOT NULL UNIQUE,
    trial_full_name VARCHAR,
    trial_structure JSONB,
);

CREATE TABLE treatment_sites
(
    site_id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_name VARCHAR NOT NULL UNIQUE,
    site_full_name VARCHAR,
    site_location VARCHAR
);

CREATE TABLE trial_site_mapping
(
    trial_id uuid REFERENCES trials(trial_id),
    site_id uuid REFERENCES treatment_sites(site_id)
);

CREATE TABLE acl_roles
(
    acl_id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id uuid REFERENCES token_details(id),
    trial_id uuid REFERENCES trials(trial_id),
    site_id uuid REFERENCES treatment_sites(site_id),
    admin_access BOOLEAN DEFAULT FALSE, 
    read_access BOOLEAN DEFAULT FALSE,
    write_access BOOLEAN DEFAULT FALSE
);
