# DICOM Deidentification Tool

## Setting Up the Python Environment
To run the tool as a Python script or to build a standalone executable, a valid Python environment is required, which can be created by using the `requirements.txt` file, which lists the required Python packages.  To create a conda based environment, the following commands can be used: 

```
conda create -n dicom_env python=3
conda activate dicom_env
pip install -r requirements.txt

```
__NOTE:__ Please use an environment name of your choice in place of `dicom_env` if needed.

## Creating a Standalone Executable

To create an executable from the DICOM anonymisation script, the `build.bat` (on Windows) or `build.sh` (on Linux/UNIX) can be used. This could create the executable in a temporary folder named `dist`.

```
build.bat
```

