```
. 'y' - represents the patient no. and 'i' represents the fraction no. 
└── center/
    ├── Patient Dose Files/ - Contains the Dicom dose files for each patient
    │   └── Patient y/
    │       └── files...
    ├── Patient Planning CTs/ - Dicom Planning CT files for each patient
    │   └── Patient y/
    │       └── Dicom Planning CT files...
    ├── Patient Structure Sets/ - The Dicom Structure sets for each patient
    │   └── Patient y/
    │       └── Dicom Structure files...
    ├── Patient Plans/ - The Dicom plans for each patient
    │   └── Patient y/
    │       └── Dicom Plan files...
    ├── Patient CBCT Images/ - The Dicom files for 3D-CBCT for each fraction for each patient 
    │   └── Patient y/
    │       ├── Fxi/
    │       │   └── Dicom CBCT Files...
    │       └── Fxi+1/
    │           └── Dicom CBCT Files...
    ├── Couch Registration Files/ - The Dicom couch registration files for each fraction for each patient
    │   └── Patient y/
    │       ├── Fxi/
    │       │   └── Dicom Registration Files...
    │       └── Fxi+1/
    │           └── Dicom Registration Files...
    └── Patient Images/ - The 2D kV images for each fraction for each patient
        └── Patient y/
            ├── Fxi/
            │   ├── kV images
            │   └── Scan file
            └── Fxi+1/
                ├── kV images
                └── Scan file
```
