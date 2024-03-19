# Define Trial Interface
At the first step, we need to confirm which data we want to upload to the database, and fill up the template.json file, which could be download here: [template.json](/docs/trial_folder_structure/template.json). The top levels of the template file are prescription and fraction. A file item could be in either prescription level or fraction level, but it could not be in both level. The keys under the prescription level and fraction level are free to delete if the new trial does not require them.

# Define Folder Structure
After we defined the trial interface, we need to define the folder structure of the trial. There are two types of paramaters. Parameters defined at the patient level that do not change during treatment fractions, e.g., patient plan are defined under "prescription" and parameters defined at the fraction level are defined under "fractions". 

The folder structure should be defined and created before uploading any data. Once we have the folder structure defined, we can upload the data to the trial folder. Caution: Do not change the folder structure once the data is uploaded. The folder structure could be define under the key - path in each item. For example, if we want to save the kv images under this path:
```
/LARK/RNSH/Patient Images/Patient 1/Fx1/Fx1-A/KIM-KV/
```
The path should be defined as:
```
/{clinical_trial}/{test_centre}/Patient Images/Patient {centre_patient_no}/{fraction_name}/{sub_fraction_name}/KIM-KV/
```
These items in braces are variables, which will be filled up during the data uploading process.

# Define Other Parameters
```
  "display_name":"", # The common name of the item which will be displayed on the contentUploader page
	"field_type":"", # This is the type of upload item, if the item contains multiple files, the type should be "folder". Single file should be "file"
	"level": "", # This is the level of the item, it could be "prescription" or "fraction"
	"allowed":["application/dicom"] # This is the allowed file type, required to state the exact file type. For example, if the allowed file type is "application/dicom", the file type should be "application/dicom", not "dicom". All available file types could be found here: https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
```
