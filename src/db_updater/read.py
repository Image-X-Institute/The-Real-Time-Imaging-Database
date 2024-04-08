
import json
import os
import re
folder_path = "/Volumes/research-data/PRJ-RPL/2RESEARCH/1_ClinicalData/SpanC/RNSH/Patient Images"

relist = []
patList = []
for name in os.listdir(folder_path):
  if not name.find("PAT"):
    patList.append(name)

patList.sort()
for pat in patList:
  fractfolder = os.listdir(f"{folder_path}/{pat}")
  fractfolderList = []
  for name in fractfolder:
    if re.fullmatch(r"Fx\d+", name):
      fracPack = {
        "fraction_number": int(name[2:]),
        "fraction_name": [name],
        "fraction_date": ""
      }
      fractfolderList.append(fracPack)
  patPack = {
    "patient_trial_id": f"SPANC_{pat[3:]}",
    "centre_patient_no": int(pat[3:]),
    "age": 0,
    "gender": "",
    "tumour_site": "",
    "number_of_markers": 0,
    "LINAC_type": "",
    "fractions": fractfolderList,
  }
  relist.append(patPack)

with open("data.json", "w") as f:
  json.dump(relist, f, indent=2)