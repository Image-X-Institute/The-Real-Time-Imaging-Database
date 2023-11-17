# /bin/bash

PATIENT_DATA_PATH="$1"
# PATIENT_DATA_PATH="data/new_patient_data.json"

TEMPLATE_FILE="$2"
# TEMPLATE_FILE="../../docs/trial_folder_structure/LARK.json"

RDS_PATH="$3"
# RDS_PATH="/Volumes/research-data/PRJ-RPL/2RESEARCH/1_ClinicalData"

OUTPUT_PATH="$4"
# OUTPUT_PATH="data/sql_output.sql"


python newFilesystemScrubber.py --template $TEMPLATE_FILE --patientData $PATIENT_DATA_PATH --rdsRoot $RDS_PATH --outputPath $OUTPUT_PATH