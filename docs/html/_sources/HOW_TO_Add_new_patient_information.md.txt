# HOW TO Add New Trial/Test Centre/Patient Information

The db_updater component in this repository is responsible for collecting the clinical trial related data from the file system (from the clinical trial shared drive) and then generating SQL scripts to populate the database. The [DB Updater documentation](../db_updater/README.md) details on the exact process of how the file system is scrubbed to extract the required details.

To add a new patient to an existing trial or add a new test centre, the following process should be followed:

1. Clone this repository locally and setup the python environment for the db_updater component as detailed in the [DB Updater documentation](../db_updater/README.md). Remember to a `local_settings.json` withe the local system settings.

2. For adding a new test centre to a trial, create a new file system scrubber template with the name `<Trial name>_<Site name>_data_template.json` in the `db_updater/data/templates` folder. For reference, please look at `SPARK_CMN_data_template.json`.

3. For adding a new patient to an existing trial, modify the `patient_meta_data.json` file kept under `db_updater/data` and add the fractions relevant to the patient in the relevant fraction file. See the [DB Updater data document](../db_updater/data/README.md) for details.

4. Run the Python module FileSystemScrubber.py in the db_updater folder

5. A new file named `scrubbed_patient_data.json` should be generated, open it and check if there are "not found" strings, if so then fix the `<Trial name>_<Site name>_data_template.json`; else once satisfied, proceed to the next step.

6. Run the Python module `PatientDataReader.py`

7. A new SQL file named `dbinserts.sql` would get generated, which can be used to populate the database.
