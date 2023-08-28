# DB updater Data Templates

This folder contains the template files that are used for gathering the data from the filesystem relevant to the patient and fractions levels. each treatment centre under each clinical trial has its own data template and the pattern of file name follows the convension `<trial_name>_<test_centre>_data_template.json`. 

These files contain key value pairs, where each key name is fixed (used by the Python modules) and the value part contains file paths or variables that are used by the file system scrubber to find the relevant files.

The templates support multi path options, where more than pne path may be specified with a "pipe" | seperator. The file system scrubber would first search for the first path and only if it is not found then it would search fof the second one and so on.

![Multiple path options](../../../docsrc/images/FS_scrubbing_multi_path_options.png)

It is possible to use regular expressions and variables within a path to make the search options more flexible.
![Path templates using regular expressions](../../../docsrc/images/FS_scrubbing_regular_expressions.png)
