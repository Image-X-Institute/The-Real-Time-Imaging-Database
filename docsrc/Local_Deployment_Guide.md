# LEARN DB Deployment Guide

## Introduction

This document describes the process of setting up the Clinical Trial database, the data service and populating the database with data catalogued from the clinical trail data shared drive. It assumes that the person setting up the service has access to the codebase (which is composed mostly of Python files) and the relevant data shares.

## Pre Install Requirements

### Hardware Requirements

There are no specific hardware requirements for the database service to be installed. The system on which the service is installed should be capable of running either Windows 10 or any of the latest distributions of Linux and have sufficient resources to host the PostgreSQL database server.

### Software and Environment Setup

The data service has been designed to run on a windows based system (as a service, after being compiled into an executable) or a Linux based system. In either case, the following requirements should be met.

#### PostgreSQL Database server

 The data service uses PostgreSQL as the backend database for both the clinical trial data as well as the user authentication and authorisation functionality. It has been tested with PostgreSQL versions 12.x, 13.x and 14.x and should be able to function satisfactorily with an install of either of these versions. 
 
 To install the database server, please use the system packages in case of Ubuntu, RedHat or any other Linux distribution of choice and in case of Windows, EDB provides opensource [Windows installer builds](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads).

 ```bash
 # On Ubuntu based systems, install the top level PostgreSQL package
 apt update
 apt install postgresql

 ```
 
 __NOTE:__ The database setup instructions in this document are carried out using the `psql` command line client. After installation, this should be available on Linux as a command to be executed on the shell. On Windows, use the `SQL Shell (psql)` program under `Start > Programs > PostgreSQL XX > SQL Shell (psql)`, where XX indicates the installed PostgreSQL version.

#### Python Environment
 
 Python should be installed to be able to run the data service and other related modules. While the default system python install can be used directly, it would be preferable to either use a [virtual environment](https://docs.python.org/3/library/venv.html) or [`Miniconda`](https://docs.conda.io/en/latest/miniconda.html) for setting up the appropriate environments.

 ````bash
 # On Linux based systems, run the following to get latest Miniconda
 cd ~/Downloads
 wget -c https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
 chmod +x Miniconda3-latest-Linux-x86_64.sh
 ./Miniconda3-latest-Linux-x86_64.sh
 ````

#### Storage Access
 
 The actual clinical trial data is kept in the University of Sydney [research drives](https://sydneyuni.atlassian.net/wiki/spaces/RC/pages/228589620/Research+Data+Store). Hence, the system running the data service should have access to these (or an alternative in case being run on a different storage location). It should be possible to mount the CIFS/Windows Share using a valid `unikey`, which has the authorisation to access the Image-X shared drive.

 ```bash
 # On windows, map the shared drive to a drive letter
 # On Linux, mount it as a cifs partition by providing your <unikey>
 
 sudo mkdir /mnt/rds    # needed only once
 sudo mount -tcifs //shared.sydney.edu.au/research-data/PRJ-RPL /mnt/rds/ -osec=ntlmv2,domain=SHARED,username=<unikey>,uid=$(id -u),gid=$(id -g),vers=3.0
 ```
__NOTE:__ On Linux, it would be necessary for the CIFS module to the installed for being able to mount the shared drive. It might be a good idea to add the mount instructions to the `/etc/fstab` file for automatically having the shared drive mounted everytime the system boots up.

__NOTE:__ The clinical trial data is kept on RDS under the project `RPJ-RPL` in the folder `/2RESEARCH/1_ClinicalData/` (one folder per Trial). Please ensure that you have access to it on [DashR](https://dashr.sydney.edu.au). Otherwise, if this data service is used to host data from an alternate location, then use the appropropriate mount/map instruction accordingly.

#### Source Control Tools
 
 The source and scripts for the service is kept under source control in GitHub and hence the git client side tools would be required to clone the repository and access them. The git [command line tool](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) should be sufficient to do this. 

 ```bash
 # On ubuntu based systems:
 apt update
 apt install git
 ```

## Setup and Deployment

We would be taking a build from scratch approach for setting up the data service and the following sections would guide one though the process of doing so.

### Setting Up a Staging Area

The staging area is the filesystem path in which the source code is placed (by cloning from `git origin` or, less preferably, by copying the source).

This staging area is referred to as the _<REPO_ROOT>_ in the rest of the document.

### Creating Databases

There are two databases that need to be created on PostgreSQL as well as a user role to grant access to them. The scripts for creating and initialising the databases is kept in `<RPO_ROOT>/scripts/db` and this would be referred to as the DB scripts folder in the sections below. To run the database SQL scripts, the PostgreSQL command line tool `psql` can be used.

#### Creating a User Role and Databases
The template for the database user role creation is present in the script `db_init.sql` in the DB scripts folder. It can be run as-is using the default `postgres` user and it would create the default user defined in the scripts. However, for additional security, it is recommended the name and password for the database user be changed in this script by opening it in a text editor and setting the database user and password in the `<database user name>` and `<password of your choice>` placeholders in the following lines:

```SQL
CREATE USER <database user name> WITH CREATEDB PASSWORD <password of your choice>
CREATE DATABASE testdb WITH OWNER <database user name>;

CREATE DATABASE auth_audit_db WITH OWNER <database user name>;
```

__NOTE:__ For a development setup, these modifications are not required and the data service can run properly even with the default values defined in the script. If these values are changed, then they should be updated in the configuration file that would be described in configuration step below.

To create the user role, the `db_init.sql` (or the modified one) can be run as follows:

```bash
cd <RPO_ROOT>/scripts/db
psql -U postgres -f db_init.sql
```
__NOTE:__ On Linux, it might be necessary to `su` to the `postgres` user, which is created when PostgreSQL is installed on the system. Since this is a system user, it might not have any password assigned to it. In that case, using `sudo su - postgres` might do the trick. On Windows, running the above command would prompt for the password that was set while installing the PostgreSQL server.

The script should produce a `CREATE ROLE` followed by a number of `CREATE DATABASE` output without any errors to indicate successful creation of the appropriate role and databases.

#### Setting up the Databases

In the DB scripts folder, the following scripts need to be executed using the PostgreSQL client one by one to setup the actual tables in the databases created above and initialise them with some required data. Replace the `<database user name>` in the statements below with the appropriate user name (or `indrajit` if the script was executed unchanged in the previous section),

```bash
psql -U <database user name> -d testdb -f db_schema.sql

psql -U <database user name> -d auth_audit_db -f auth_db_schema.sql

psql -U <database user name> -d auth_audit_db -f auth_db_init.sql
```
__NOTE:__ If the above scripts are executed for the very first time on a new install of PostgreSQL, it is normal to see a number of `NOTICE: table <table name> does not exist, skipping` errors.

__NOTE:__ Be careful with the name of the database (the `-d <database name>` parameter while executing the `psql` statements)

### Setting Up the Configuration

The configuration related to the data service should be present in the folder `<REPO_ROOT>/data_service`. However, no default configuration is provided in the codebase. Instead, a configuration file template is provided in `<REPO_ROOT>/data_service/templates` folder by the name `local_settings_template.json`. Copy this template file into the `data_service` folder and rename it as `local_settings.json`

Next, the `local_settings.json` configuration file would need to be modified to match the local system settings. To do this, open the `local_settings.json` file in a text editor and change the key-value pairs specified below.

```json
    "root_filesystem_path": "X:\\2RESEARCH\\1_ClinicalData",
    ...

    "imaging_db_user": "<database user name>",
    "imaging_db_password": "<database password>",
    "imaging_db_name": "testdb",
    ...

    "auth_db_name": "auth_audit_db",
    "auth_db_user": "<database user name>",
    "auth_db_password": "<database password>",
    ...
    
    "debug_mode": true,
```
__NOTE:__ The `root_filesystem_path` should be set to the shared drive path, which has been mapped in case of windows or mounted in case of Linux. The `debug_mode` key is set to `false` by default and this can be set to `true` in a development setup to be able to look at extra debug messages.

### Running The Data Service

The data service provides the RESTful API based interface for clinical trail data and is a web service, which can be queried manually using a web browser or through the client libraries. to run this service, a Python environment needs to be setup for executing the service. In the following set of instructions, it is assumed that `miniconda` is used. However, any python environment with the `pip` tool can be used to do so.

```bash
conda create -n data_service_env python=3

conda activate data_service_env

cd <REPT_ROOT>/data_service

pip install -r requirements.txt
```

__NOTE:__ The name of the environment in the above instructions is `data_service_env`. It can be instead set to any other convenient name.

To run the data service, the `application.py` module can be executed in the python environment with all the requirements installed.

```bash
python application.py
```

By default, the web service starts listening on the port 8090 of the system, on which it is run. To test the service, a web browser can be used as follows.

```bash
firefox http://localhost:8090/apidoc
```

This would open the API documentation page, which can be used to access the individual APIs.

__NOTE:__ The default configuration of the data service runs it in a token validation mode, where access to all of the API endpoints used for accessing the data are protected via an authentication mechanism. This is an appropriate behaviour for the actual production deployment. However, for development and testing the APIs can be used from a web browser without needing to add an authentication token by modifying the `config.py` file and setting the `VALIDATE_TOKEN` value to `False` instead of `True`.

### Installing Data Service as an OS Service

__NOTE:__ This section is currently applicable only to a Windows based platform and is not required for a development (or any non-production) environment.

The data service can be built into a windows executable using the `pyinstaller` package that is installed by the `requirements.txt` of the data service. To build the service the `build_win_service.bat` script can be used.

```cmd
conda activate data_service_env

cd <REPT_ROOT>/data_service

build_win_service.bat
```

This would build a Windows executable of the service, which can then be installed on a Windows system as a background service using the service installer script as follows.

__NOTE:__ The following commands need to be executed with the administrator privilege. To do so, open a command prompt by right clicking and selecting "run as administrator".
```cmd
cd <REPT_ROOT>

scripts/service/install_service.bat
```

## Importing Clinical Trial Data

The database uses a JSON based clinical trial data template to go though the physical data storage filesystem and then catalogue it. This is done using the `db_updater` tools.

The data ingest occurs as a two step process: first the `FilesystemScrubber` needs to be run, which uses the `patients_meta_data.json` file kept in `<REPO_ROOT>/db_updater/data`. This file is a registry of clinical trial patients (using an ID that is either generated by TROG or a similar authority) and contains a high level information about each patient. It also needs the "site and trial" data description file (one for each site-trial combination), which should also be present in `<REPO_ROOT>/db_updater/data`. The `FilesystemScrubber` generates an intermediate JSON file, which is then used by the next step of the ingest process.

The next step is handled by `PatientDataReader`, which uses the intermediate file generated by the `FilesystemScrubber` to finally produce an SQL script that contains a long list of statements to insert the clinical trail catalogue into the appropriate database tables.

### Setting Up the Python Environment

A separate Python environment needs to be setup for the `db_updater` tools. This can done similar to the previous section, using `miniconda`, as an example, to create the environment.

```bash
conda create -n db_updater_env python=3

conda activate db_updater_env

cd <REPT_ROOT>/db_updater

pip install -r requirements.txt
```

### Scrubbing the Filesystem
 
To scrub the clinical trial storage filesystem, the first step is to create a local settings file similar to the data service's local settings. To do so, copy the configurations template from `<REPO_DATA>/db_updater/data/templates/local_settings_template.json` into the data folder as `local_settings.json`.

```bash
cp <REPO_DATA>/db_updater/data/templates/local_settings_template.json <REPO_DATA>/db_updater/data/local_settings.json
```

Next, open the configuration JSON file in a text editor and then modify the `root_filesystem_path` key to have the path to the clinical trail data similar to the following example.

```json
    "root_filesystem_path": "X:\\2RESEARCH\\1_ClinicalData"

    OR

    "root_filesystem_path": "/mnt/rds/2RESEARCH/1_ClinicalData"

```
With the clinical trail data path set, the file system scrubber can be executed to collect the data after an appropriate python environment is setup for this tool.

```bash
conda activate db_updater_env

cd <REPT_ROOT>/db_updater

python FilesystemScrubber.py
```
__NOTE:__ Running the `FilesystemScrubber` would take anything between 15 to 20 minutes  based on the current amount of data present in the clinical trail data drive and it would display the names of the clinical trial sites as it processes the data for each of them.

After the filesystem scrubbing process is complete, a `scrubbed_patient_data.json` file should be generated in the `<REPO_DATA>/db_updater` folder. This is the intermediate file that is used by the second step of the data import.

### Producing the Final Data Import SQL

The second stage of the import uses the `scrubbed_patient_data.json` file generated by the filesystem scrubber.

```bash
conda activate db_updater_env

cd <REPT_ROOT>/db_updater

python PatientDataReader.py
```

__NOTE:__ As a part of the final data compilation, the DVH files are read to extract the dose information. For some trials (such as SPARK/PWC), this might generate errors such as `ERROR: Unsupported format`. This is normal and can be ignored as long as the process completes without showing any Python errors and exceptions.

After the successful execution of this process, the compiled output is generated in the folder `<REPO_DATA>/db_updater` as `dbInserts.sql`. This SQL file can then be used to populate the database as follows.

```bash
psql -U <database user name> -d testdb -f dbInserts.sql
```
__WARNING:__ Running the `dbInserts.sql` script would overwrite all the previous data in the database and populate it with the newly compiled data. Hence, in a production environment, use with caution!

---

Please feel free to contact Indrajit in case of any doubts or questions: _indrajit.ghosh@sydney.edu.au_
