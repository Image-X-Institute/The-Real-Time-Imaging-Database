```
. 'y' - represents the patient no. and 'i' represents the fraction no.  
└── center/
    ├── Dose Reconstruction/ - Contains planned dose dicom, DVH and motion-included delivered dose dicoms and DVHs. '_track' indicates real-time motion tracking with KIM. 'No_track' indicates estimated no tracking scenario.
    │   ├── DVH/
    │   │   └── Patient y/
    │   │       ├── summed/
    │   │       │   ├── planned_dvh_path
    │   │       │   ├── DVH_no_track_path
    │   │       │   └── DVH_track_path
    │   │       └── Fxi/
    │   │           ├── planned_dvh_path
    │   │           ├── DVH_no_track_path
    │   │           └── DVH_track_path
    │   └── DICOM/
    │       └── Patient y/
    │           ├── summed/
    │           │   ├── planned_dicom_path
    │           │   ├── Dicom_no_track_path
    │           │   └── Dicom_track_path
    │           └── Fxi/
    │               ├── planned_dicom_path
    │               ├── no_track_plan_path
    │               └── track_plan_path
    ├── Patient Plans/ - Contains Patient CT, MRI images, patient plan, planned dose dicom.  
    │   └── Patient y/
    │       └── Fxi/
    │           └── files/
    │               ├── CT/
    │               │   └── rt_ct_path
    │               ├── Dose/
    │               │   └── rt_dose_path
    │               ├── MRI/
    │               │   └── rt_mri_path
    │               └── Plan/
    │                   └── rt_plan_path
    ├── Patient Measured Motion/ - Contains KIM measured patient motion. 
    │   └── Patient y/
    │       └── Fxi/
    │           └── Fxi-A/
    │               └── kim_logs

    ├── Triangulation/ - Contains triangulation results. 
    │   └── Patient y/
    │       └── Fxi/
    │           └── Fxi-A/
    │               ├── metrics
    │               └── triangulation

    ├── Trajectory Logs/ - Contains linac trajectory logs.
    │   └── Patient y/
    │       └── Fxi/
    │           └── trajectory_logs

    ├── Patient Images/ - Contains intrafraction kV and MV images and any notes. 
    │   └── Patient y/
    │       └── Fxi/
    │           └── Fxi-j/
    │               ├── KIM-KV/
    │               │   └── kv_images
    │               └── KIM-MV/
    │                   └── mv_images

    ├── Patient Files/ - Contains patient centroid (planned marker positions), patients margin files where applicable.   
    │   └── Patient y/
    │       └── Fxi/
    │           └── centroid_path

    └── Patient Structure Sets/ - It's already up there. 
        └── Patient 15/
            └── FXi/
                └── rt_structure_path
```
