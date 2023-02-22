-- This file shoudlbe executed after PostgreSQL is freshly installed on a system
-- Execute as the user postgres

-- update the user and DB name to something proper
CREATE USER indrajit WITH CREATEDB PASSWORD 'indrajit';
CREATE DATABASE testdb WITH OWNER indrajit;

CREATE DATABASE auth_audit_db WITH OWNER indrajit;