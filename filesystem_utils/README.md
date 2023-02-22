# Filesystem Utility Scripts and Programs

Thsi folder contains the filesystem utility scripts that are are used for performing various filesystem operations such as searching for specific files, unzipping comrpessed files etc., which are relevant to processing the clinical trials data.

## Script Details
### Recursive File Expander
[This script](RecursiveFileExpander.py) seeks zipped files starting at a folder level and going down the sub folders and then unzips them. Deepnding on the arguments passed, it may delete the processed file or rename it, so that it is no processed ina future run of this script. This script can be built into an executable too.

To use this script, the following arguments can be passed to it:
```bash
# Run the utility to uncompress files and rename them by appending "_done"
python RecursiveFileExpander.py <top level folder>

# Run the utility to uncompress files and delete them afterwards
python RecursiveFileExpander.py --delete <top level folder>

# In case the script is built into an executable, the same args can be used
RecursiveFileExpander.exe <top level folder>

```

### Path Finder
[The Path Finder](PathFinder.py) script can be used to find folders and sub folders (starting at a top level folder), which contain a certain type of files. The expected name of the files can be specified as a regular expression pattern. 

This script can be used as follows:
```bash
# specify the search pattern first and then the top level folder
python PathFinder.py CT_?[0-9,.].dcm /Clinical/data/path
```

## Setting up Development Environement
To install the required dependencies and python libraries, the [requirements.txt](requirements.txt) file can be used.

Please run the following commands to setup your python environment (this is required only once). Please ensure that the correct environment is set before installing the requirements. For example, if using conda, ensure that `conda activate <proper_environment_name>` has been executed.

### Anaconda/Miniconda based install
```bash
conda install --file requirements.txt
```

### Pip based install
```bash
pip install -r requirements.txt
```

## Building Executables
To make copying and using these scripts easier, they can be built into executables using the Python PyInstaller module. To do so on Windows, execute the [build batch file](build_utils.bat) on the command line with the appropriate Python environment set. This would build the scripts listed in the batch file and place the final execuatable in a folder named dist. These are standalone executable and usually can be run directly on any target system without needing to install any dependencies.