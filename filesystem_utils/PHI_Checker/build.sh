#!/bin/bash
pyinstaller --clean --onefile --hiddenimport=pydicom.encoders.gdcm \
    --hiddenimport=pydicom.encoders.pylibjpeg \
    PHIChecker.py