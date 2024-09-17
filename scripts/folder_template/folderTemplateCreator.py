
import os
import json
import csv
import re


def checkPattern(itemName, path):
  mri_pattern = r'mri_intra'
  cbct_pattern = r'cbct'
  kv_pattern = r'kv'
  mv_pattern = r'mv'
  surface_pattern = r'surface'
  pet_pattern = r'pet'

  if re.search(mri_pattern, itemName):
    os.makedirs(path + "/MRI_intra")

  if re.search(cbct_pattern, itemName):
    os.makedirs(path + "/CBCT")
    os.makedirs(path + "/CBCT/CBCT1")
    os.makedirs(path + "/CBCT/CBCT2")
    os.makedirs(path + "/CBCT/CBCT3")

  if re.search(kv_pattern, itemName):
    os.makedirs(path + "/KIM-KV")

  if re.search(mv_pattern, itemName):
    os.makedirs(path + "/KIM-MV")

  if re.search(surface_pattern, itemName):
    os.makedirs(path + "/Surface")

  if re.search(pet_pattern, itemName):
    os.makedirs(path + "/PET_intra")



def createFolderTemplate(clinicalTrial, centerName, templatePath, samplePatient):
  if not os.path.exists(templatePath):
    print("Path does not exist")
    return False
  
  # Read the template file
  if not os.path.exists(templatePath + "LEARN" + ".json"):
    print("Template file does not exist")
    return False
  
  with open(templatePath + "LEARN" + ".json") as f:
    trialData = json.load(f)

  print("Creating folder structure for clinical trial: " + clinicalTrial + " at test centre: " + centerName)
  # Create the folder structure
  if not os.path.exists(os.getcwd() + "/" + clinicalTrial):
    os.mkdir(os.getcwd() + "/" + clinicalTrial)

  # Create presciption folder for each patient
  for itemName in trialData["prescription"]:
    item = trialData["prescription"][itemName]
    for patientId in samplePatient["patient_id"]:
      if "tumour_site" in samplePatient.keys():
        itemPath = item["path"].format(clinical_trial=clinicalTrial, test_centre=centerName, centre_patient_no=patientId.zfill(2), tumour_site=samplePatient["tumour_site"][patientId])
      else:
        itemPath = item["path"].format(clinical_trial=clinicalTrial, test_centre=centerName, centre_patient_no=patientId.zfill(2))
      if not os.path.exists(os.getcwd() + itemPath):
        os.makedirs(os.getcwd() + itemPath)


  # Create the fraction folder for each patient
  for itemName in trialData["fraction"]:
    item = trialData["fraction"][itemName]
    for patientId in samplePatient["patient_id"]:
      if "tumour_site" in samplePatient.keys():
        itemPath = item["path"].format(clinical_trial=clinicalTrial, test_centre=centerName, centre_patient_no=patientId.zfill(2), tumour_site=samplePatient["tumour_site"][patientId])
      else:
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
            checkPattern(itemName, os.getcwd() + subfractionPath)
            if not os.path.exists(os.getcwd() + subfractionPath):
              os.makedirs(os.getcwd() + subfractionPath)
        else:
          checkPattern(itemName, os.getcwd() + fractionPath)



  # Create patient info for importing into the database
  title = "patient_trial_id,clinical_trial,test_centre,centre_patient_no,age,gender,tumour_site,avg_treatment_time,clinical_diag,kim_accuracy,linac_type,number_of_markers,patient_note"
  title_list = title.split(",")
  with open(os.getcwd() + "/" + clinicalTrial + "/patient_info.csv", "a+") as f:
    writer = csv.writer(f)
    writer.writerow(title_list)
    for patientId in samplePatient["patient_id"]:
      col1 = f'{clinicalTrial}_{centerName}_{patientId.zfill(2)}'
      col2 = 'LEARN_test'
      col3 = f'{centerName}'
      col4 = f'{patientId}'
      col5 = ''
      col6 = ''
      col7 = f'{samplePatient["tumour_site"][patientId]}'
      col8 = ''
      col9 = ''
      col10 = ''
      col11 = ''
      col12 = ''
      col13 = ''
      writer.writerow([col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11, col12, col13])
  with open(os.getcwd() + "/" + clinicalTrial + "/patient_fraction.csv", "a+") as f:
    writer = csv.writer(f)
    writer.writerow(["patientId", "fractionName", "fractionNumber", "fractionDate", "mvsdd", "kvsdd", "kvPixelSize", "mvPixelSize", "markerLength", "markerWidth"])
    for patientId in samplePatient["patient_id"]:
      fractionList = samplePatient["fraction"][patientId]
      for fraction in fractionList:
        fractionNumber = fraction["fraction_name"].replace("Fx", "")
        if len(subfraction):
          for subfraction in fraction["subfraction"]:
            writer.writerow([f'{clinicalTrial}_{centerName}_{patientId.zfill(2)}', subfraction, fractionNumber, '', '', '', '', '', '', ''])
        else:
          writer.writerow([f'{clinicalTrial}_{centerName}_{patientId.zfill(2)}', fraction["fraction_name"], fractionNumber, '', '', '', '', '', '', ''])
if __name__ == "__main__":
  clinicalTrial = "LEARN_test"
  centerName = "RNSH"
  templatePath = os.getcwd() + "/../../docs/trial_folder_structure/"
  samplePatient = {
    "patient_id": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "100","345", "789", "1000", "523453"],
    "tumour_site": {
      "1": "Brain",
      "2": "Lung",
      "3": "Liver",
      "4": "Prostate",
      "5": "Breast",
      "6": "Brain",
      "7": "Lung",
      "8": "Pancreas",
      "9": "Spine",
      "10": "H&N",
      "11": "Kidney",
      "12": "Cardicac radioablation",
      "100": "Brain",
      "345": "Brain",
      "789": "Brain",
      "1000": "Brain",
      "523453": "Brain"
    },
    "fraction":{
      "1": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        },
        {
          "fraction_name": "Fx3",
          "subfraction": []
        }
      ],
      "2": [
        {
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
        }
      ],
      "3": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        }
      ],
      "4": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        }
      ],
      "5": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        }
      ],
      "6": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        }
      ],
      "7": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        },
        {
          "fraction_name": "Fx3",
          "subfraction": ["Fx3-a", "Fx3-b"]
        }
      ],
      "8": [
        {
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
        }
      ],
      "9": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        }
      ],
      "10": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        },
        {
          "fraction_name": "Fx3",
          "subfraction": ["Fx3-a", "Fx3-b"]
        }
      ],
      "11": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        }
      ],
      "12": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": ["Fx2-a", "Fx2-b"]
        }
      ],
      "100": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        },
        {
          "fraction_name": "Fx3",
          "subfraction": []
        }
      ],
      "345": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        },
        {
          "fraction_name": "Fx3",
          "subfraction": ["Fx3-a", "Fx3-b"]
        }
      ],
      "789": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        }
      ],
      "1000": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        }
      ],
      "523453": [
        {
        "fraction_name": "Fx1",
        "subfraction": ["Fx1-a", "Fx1-b", "Fx1-c"]
        },
        {
          "fraction_name": "Fx2",
          "subfraction": []
        }
      ]

    }
  }

  createFolderTemplate(clinicalTrial, centerName, templatePath, samplePatient)