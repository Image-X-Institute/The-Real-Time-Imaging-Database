# DB Updater
This folder contains the modules and data relevant to generating the database SQL scripts by walking through the clinical data file system and parsing files to collect data about them. To make the walking process efficient, the `data` and `data/templates` folders under this folder contain a set of files which define the structure in which the data should be collected and pointers to where the data should be collected from. Please refer to [data documentation](data/README.md) for more details on these files.

### Generating Database Scripts from Clinical Data
The `generateSQL.sh` script runs all the python modules in the correct order to generate the SQL scripts. Please note that the data templates named `new_patient_data.json` to be present in the `data/templates` folder.

The `generateSQL.sh` script requires 4 arguments to be passed to it. These are:
1. The path to the formated patient data in json format.
2. The path to the trial structure template file, normally you could find this file in the `/docs/trial_folder_structure/` folder.
3. The path to the RDS mounted folder where the clinical data is stored.
4. The output file path where the SQL scripts will be stored.

An example of how to run the `generateSQL.sh` script is as follows:
```bash
bash generateSQL.sh "data/new_patient_data.json" "../../docs/trial_folder_structure/LARK.json" "/Volumes/research-data/PRJ-RPL/2RESEARCH/1_ClinicalData" "data/sql_output.sql"
```

If the script is run successfully, the generated SQL scripts will be stored in the data folder under the name `sql_scripts.sql`.


<!-- The python modules in this folder look at `data/local_settings.json` for local system specific settings. On a fresh clone of the repository, this file needs to be created (and not added to source control there after). To create this file, the template located at `data/templates/local_settings_template.json` can be copied and changed to reflect the local system settings. Please refer to [data templates documentation](data/templates/README.md) for details. -->

<!-- ## Generating Database Scripts from Clinical Data
This folder contains a set of Python modules for scrubbing the filesystem data and generating SQL scripts from them.
The easest way to generate the SQL scripts is to run the `generateSQL.sh` script. This script runs all the python modules in the correct order to generate the SQL scripts. The generated SQL scripts are stored in the data folder under the name `sql_scripts.sql`. Please note that this script requires the `data/local_settings.json` file to be present, and the data templates named `new_patient_data.json` to be present in the `data/templates` folder. -->

<!-- ### Scrubbing Filesystem
The module [newFilesystemScrubber.py](newFilesystemScrubber.py) is responsible for walking through the clinical data drive based on the data templates named `new_patient_data.json` and generates a file named `scrubbed_patient_data.json` everytime the filesystem scrubber is run. This is an intermediate file, which contains all the parsed data is used as an input for generating the SQL scripts to insert data into the database.

To run this python module, run the following command:
```bash
python newFilesystemScrubber.py
``` -->

<!-- ### Generating SQL scripts
The module [PatientDataReader.py](PatientDataReader.py) uses the `scrubbed_patient_data.json` file to generate the SQL insersion scripts. It expects all the paths, patient and fraction details to be in this JSON file and uses the `DVHParser.py` to parse DVH files to get the dosage information.

To run this python module, execute the following command:
```bash
python PatientDataReader.py
``` -->

<!-- ### Generating SQL scripts
The module [sqlGenerator.py](sqlGenerator.py) uses the `scrubbed_patient_data.json` file to generate the SQL insersion scripts. It expects all the paths, patient and fraction details to be in this JSON file. The generated SQL scripts are stored in the data folder under the name `sql_scripts.sql`.

To run this python module, execute the following command:
```bash
python sqlGenerator.py
``` -->

<!-- ### Parsing Dose Value Histograms
While the `PatientDataReader.py` internally uses the [DVHParser.py](DVHParser.py) module to extract the dosage information, the module can be imported directly in Python code too. To use it, the `DVHParser` class can be used as follows:
```python
from DVHParser import DVHParser

parser = DVHParser(<path of the DVH file>)
parser.parse() -->

<!-- # print all the structures contained in the DVH file:
parser.getAllStructureNames()

``` -->
