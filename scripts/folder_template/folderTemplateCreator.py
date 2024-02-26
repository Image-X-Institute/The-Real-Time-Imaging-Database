
import os
import json

def createFolderTemplate(clinicalTrial, centerName, templatePath, samplePatient):
  if not os.path.exists(templatePath):
    print("Path does not exist")
    return False
  
  # Read the template file
  if not os.path.exists(templatePath + clinicalTrial + ".json"):
    print("Template file does not exist")
    return False
  
  with open(templatePath + clinicalTrial + ".json") as f:
    trialData = json.load(f)

  print("Creating folder structure for clinical trial: " + clinicalTrial + " at test centre: " + centerName)
  # Create the folder structure
  if not os.path.exists(os.getcwd() + "/" + clinicalTrial):
    os.mkdir(os.getcwd() + "/" + clinicalTrial)

  # Create presciption folder for each patient
  for itemName in trialData["prescription"]:
    item = trialData["prescription"][itemName]
    for patientId in samplePatient["patient_id"]:
      itemPath = item["path"].format(clinical_trial=clinicalTrial, test_centre=centerName, centre_patient_no=patientId.zfill(2))
      if not os.path.exists(os.getcwd() + itemPath):
        os.makedirs(os.getcwd() + itemPath)


  # Create the fraction folder for each patient
  for itemName in trialData["fraction"]:
    item = trialData["fraction"][itemName]
    for patientId in samplePatient["patient_id"]:
      itemPath = item["path"].format(clinical_trial=clinicalTrial, test_centre=centerName, centre_patient_no=patientId.zfill(2))
      if not os.path.exists(os.getcwd() + itemPath):
        os.makedirs(os.getcwd() + itemPath)
      fractionList = samplePatient["fraction"][patientId]
      for fraction in fractionList:
        fractionPath = itemPath + fraction["fraction_name"]
        if not os.path.exists(os.getcwd() + fractionPath):
          os.makedirs(os.getcwd() + fractionPath)
        if fraction["subfraction"]:
          for subfraction in fraction["subfraction"]:
            subfractionPath = fractionPath + "/" + subfraction
            if not os.path.exists(os.getcwd() + subfractionPath):
              os.makedirs(os.getcwd() + subfractionPath)
  print("Folder structure created successfully")

if __name__ == "__main__":
  clinicalTrial = "RAVENTA"
  centerName = "SampleCenter"
  templatePath = os.getcwd() + "/../../docs/trial_folder_structure/"
  samplePatient = {
    "patient_id": ["1", "2"],
    "fraction":{
      "1": [{
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
      },
      {
        "fraction_name": "Fx2",
        "subfraction": []
      }],
      "2": [{
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
      },
      {
        "fraction_name": "Fx2",
        "subfraction": ["Fx2-a", "Fx2-b"]
      },
      {
        "fraction_name": "Fx3",
        "subfraction": []
      }]
    }
  }

  createFolderTemplate(clinicalTrial, centerName, templatePath, samplePatient)