# DB Updater Data
This folder contains the the data files required for scrubbing the clinical data shared drive filesystem and gather relevant data from them.

## The Patient Meta Data

The file `patients_meta_data.json` contains a limited set of details for all the patients who have participated in the various trials. The list of patients are placed under the Trial > Treatment centre hierarchy. The relevant details for each patient are as follows:

```json
{
    "clinical_data": [
        {
            "clinical_trial": "<name of trial>",
            "centres": [
                {
                    "centre": "<name of centre>",
                    "patients": [
                        {
                            "patient_trial_id": "<TROG Study ID>",
                            "centre_patient_no": "<sequence of the patient> : int",
                            "age": "<Age of the patient during treatment> : int",
                            "gender": "<Gender> : M/F/O",
                            "tumour_site": "<organ/location of tumour>",
                            "number_of_markers": "<number of markers> : int",
                            "LINAC_type": "<LINAC used>"
                        },
                    ]
                }
            ]
        }
    ]
}

```
This file maps the sequence of patient (often the sequence in which the patient started their trial in a certain treatment centre) and this serves as a skeleton on which the rest of the patient data is gathered from the file system. The details of the patient are collected from the TROG data.

## The Scrubbed Fractions Data
The files with the name `<trial_name>_<treatment_centre_name>_scrubbed_fraction_data.json` such as `SPARK_CNM_scrubbed_fraction_data.json` contain the fraction specific details for all the patients being treated in a certain treatment centre.

The fraction details are stored in a flat hierarcy, as elemnts of a list containing the information below:

```json
{
    "fractions": [
        {
            "fraction_number": "<the fraction number> : int",
            "test_centre": "<name of the test centre>",
            "patient_sequence": "<the patient sequence> : int",
            "fraction_name": "<name of the fraction folder>",
            "fraction_date": "<date of faction treatment in ISO format>",
            "num_gating_events": "<number of KIM gating events> : int"
        }
    ]
}
```

These files can be created automatically by the `FileSystemScrubber.py` module but if the file is already present in this folder, then it treats them as cached fraction information and skips generating them, speeding up the file scrubbing action.

