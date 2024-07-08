
import json
import os
import re
import time
folder_path = "/Volumes/research-data/PRJ-RPL/2RESEARCH/1_ClinicalData/LARK/Westmead/Patient Images"

id_centre_no = {

}

patList = []
for name in os.listdir(folder_path):
  if not name.find("PAT"):
    patList.append(name)
    

patList.sort()
patInfo =[]
for pat in patList:
  try:
    fractfolder = os.listdir(f"{folder_path}/{pat}")
  except FileNotFoundError:
    continue
  fractfolderList = []
  for name in fractfolder:
    if re.fullmatch(r"Fx\d+", name):
      subfolder = os.listdir(f"{folder_path}/{pat}/{name}")
      subFractionName = []
      for sub in subfolder:
        if re.fullmatch(r"Fx\d+[a-z]", sub) or re.fullmatch(r"Fx\d+", sub):
          subFractionName.append(sub)
      if subFractionName == []:
        subFractionName = [name]
      fracPack = {
        "fraction_number": int(name[2:]),
        "fraction_name": subFractionName,
        "fraction_date": ""
      }
      fractfolderList.append(fracPack)
  patPack = {
    "patient_trial_id": id_centre_no[pat],
    "centre_patient_no": int(pat[3:]),
    "LINAC_type": "Varian Medical Systems ARIA RadOnc",
    "fractions": fractfolderList,
  }
  patInfo.append(patPack)

with open("lark_new_data.json", "w") as f:
  json.dump(patInfo, f, indent=2)


