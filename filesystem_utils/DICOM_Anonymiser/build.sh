#!/bin/bash
pyinstaller --clean --onefile --hiddenimport=pydicom.encoders.gdcm \
    --hiddenimport=pydicom.encoders.pylibjpeg \
    --add-data dicom_anonymisation_rules_default.json:. dicom_anonymiser.py