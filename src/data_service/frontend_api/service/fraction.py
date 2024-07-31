from flask import make_response
from .util import executeQuery
import sys
import config
import os
import re

fractionTableItemList = [
    "fraction_number",
    "fraction_name",
    "mvsdd",
    "kvsdd",
    "kv_pixel_size",
    "mv_pixel_size",
    "marker_length",
    "marker_width"
  ]


def getFractionDetailByPatientId(req):
  patientId = req.args.get("patientId")
  trial = req.args.get("trialName")
  sqlStmt = f"Select * from patient, prescription, fraction, images where patient.id = prescription.patient_id and prescription.prescription_id=fraction.prescription_id and images.fraction_id=fraction.fraction_id and patient.patient_trial_id='{patientId}'"
  result = executeQuery(sqlStmt, withDictCursor=True)
  if result is None:
    return make_response("No fraction found", 400)

  trialStructure = executeQuery(f"SELECT trial_structure FROM trials WHERE trial_name='{trial}'", authDB=True)[0][0]['fraction']
  requiredFields = list(trialStructure.keys()) + fractionTableItemList
  result = [{key: row[key.lower()] for key in requiredFields} for row in result]
  fractionPack = {}
  for row in result:
    if row["fraction_number"] not in fractionPack.keys():
      fractionPack[row["fraction_number"]] = []
    fractionPack[row["fraction_number"]].append(row)

  return make_response(fractionPack)


def updateFractionInfo(req):
  payload = req.json
  patientId = payload["patientId"]
  fractionName = payload["fractionName"]

  for key in payload:
    if key not in ['patientId', 'fractionName']:
      try:
        if key in fractionTableItemList:
          sqlStmt = f"UPDATE fraction SET {key}='{payload[key]}' WHERE fraction_id=(SELECT get_fraction_id_for_patient ('{patientId}', '{fractionName}'));"
          executeQuery(sqlStmt)
        else:
          sqlStmt = f"UPDATE images SET {key}='{payload[key]}' WHERE fraction_id=(SELECT get_fraction_id_for_patient ('{patientId}', '{fractionName}'));"
          executeQuery(sqlStmt)
      except Exception as err:
        print(err, file=sys.stderr)
        return make_response({"message": "Failed to update patient info"}, 400)
  
  return make_response({"message": "Fraction info updated successfully"}, 200)
  
def updateFractionField(req):
  updatePack = req.json
  if updatePack == None:
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)
  for update in updatePack:
    patientId = update["patient_trial_id"]
    fractionName = update["fraction_name"]
    for key in update["updateFields"]:
      try:
        if key in fractionTableItemList:
          sqlStmt = f"UPDATE fraction SET {key}='{update['updateFields'][key]}' WHERE fraction_id=(SELECT get_fraction_id_for_patient ('{patientId}', '{fractionName}'));"
          executeQuery(sqlStmt)
        else:
          sqlStmt = f"UPDATE images SET {key}='{update['updateFields'][key]}' WHERE fraction_id=(SELECT get_fraction_id_for_patient ('{patientId}', '{fractionName}'));"
          executeQuery(sqlStmt)
      except Exception as err:
        print(err, file=sys.stderr)
        return make_response({"message": "Failed to update patient info"}, 400)

  return make_response({"message": "Fraction info updated successfully"}, 200)
  
def _getMissingFractionFieldCheck(req):
  try:
    trialName = req.args.get("trialName")
    sqlStmt = f"SELECT * FROM patient, prescription, fraction, images WHERE clinical_trial='{trialName}' AND patient.id = prescription.patient_id AND prescription.prescription_id=fraction.prescription_id and fraction.fraction_id=images.fraction_id"
    fetchedRows = executeQuery(sqlStmt, withDictCursor=True)
    sqlStmt2 = f"SELECT trial_structure FROM trials WHERE trial_name='{trialName}'"
    fetchedRows2 = executeQuery(sqlStmt2, authDB=True)
    trialStructure = fetchedRows2[0][0]['fraction']
    requiredFields = list(trialStructure.keys()) + ["fraction_number","fraction_name"]
    missingFields = []
    for row in fetchedRows:
      missedPack = {}
      missedPack['patient_trial_id'] = row['patient_trial_id']
      missedPack['clinical_trial'] = row['clinical_trial']
      missedPack['centre_patient_no'] = row['centre_patient_no']
      missedPack['test_centre'] = row['test_centre']
      missedPack['fraction_number'] = row['fraction_number']
      missedPack['fraction_name'] = row['fraction_name']
      missedPack['missedFields'] = {key: row[key.lower()] for key in requiredFields if row[key.lower()] == None or row[key.lower()] == "not found" or row[key.lower()] == ""}
      missingFields.append(missedPack)
    return missingFields
  except Exception as err:
    print(err, file=sys.stderr)
    return None

def getMissingFractionFieldCheck(req):
  missingFields = _getMissingFractionFieldCheck(req)
  if missingFields == None:
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)
  return make_response(missingFields)

def _tryToFindKVorMVFolder(rootPath, mainPath, case):
  # For many of the trials, the name of the KV folder could be different, so we need to check all the possible names. 
  # If the folder name is neither KIM-KV nor kV, we can't do anything, but return the path to fraction folder level. 

  possibleKVFolderNames = ['KIM-KV', 'KIM-kV', 'kV', 'KV', 'kv']
  possibleMVFolderNames = ['KIM-MV', 'MV', 'mv']

  if case == "KV":
    for folderName in possibleKVFolderNames:

      if os.path.exists(rootPath + mainPath + '/' + folderName):
        return mainPath + '/' + folderName
  else:
    for folderName in possibleMVFolderNames:
      if os.path.exists(rootPath + mainPath + '/' + folderName):
        return mainPath + '/' + folderName
      
  return mainPath
  
def getUpdateFractionField(req):
  missingFields = _getMissingFractionFieldCheck(req)
  if missingFields == None:
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)
  try:
    trialName = req.args.get("trialName")
    sqlStmt2 = f"SELECT trial_structure FROM trials WHERE trial_name='{trialName}'"
    fetchedRows2 = executeQuery(sqlStmt2, authDB=True)
    trialStructure = fetchedRows2[0][0]['fraction']
    rootPath = config.DATA_FILESYSTEM_ROOT
    returnPack = []
    for field in missingFields:
      patientPack = {
        "patient_trial_id": field['patient_trial_id'],
        "fraction_number": field['fraction_number'],
        "fraction_name": field['fraction_name'],
        "updateFields": {}
      }
      for key in field['missedFields']:
        if key in trialStructure.keys():
          filePath = trialStructure[key]['path']
          formatedPath = filePath.format(clinical_trial=trialName, test_centre=field['test_centre'], centre_patient_no=str(field['centre_patient_no']).zfill(2))
          pathWithFraction = formatedPath + f'Fx{field["fraction_number"]}'
          pathWithFractionName = pathWithFraction + '/' + field['fraction_name']
          if os.path.exists(rootPath + formatedPath + field['fraction_name']):
            pathWithFractionName = formatedPath + field['fraction_name']
          
          KV_pattern = r"kv"
          MV_pattern = r"mv"

          # The logic here is to check if the path with fraction name exists, if not, check if the path with fraction exists.
          if os.path.exists(rootPath + pathWithFractionName):
            # If the key is KV or MV, we need to check if the folder name is different from the expected one.
            if re.search(KV_pattern, key):
              # If the key is KV, we need to add the KV folder name to the path.
              pathWithFractionName = _tryToFindKVorMVFolder(rootPath, pathWithFractionName, 'KV')
              # The function will return the path with KV folder name if it exists, otherwise, it will return the path with fraction name.
              # The below step is to check if the path contains KV, if it does, we will add it to the updateFields.
              if re.search(KV_pattern, pathWithFractionName):
                patientPack['updateFields'][key] = pathWithFractionName
            # The same logic as above, but for MV.
            elif re.search(MV_pattern, key):
              pathWithFractionName = _tryToFindKVorMVFolder(rootPath, pathWithFractionName, 'MV')
              # The function will return the path with MV folder name if it exists, otherwise, it will return the path with fraction name.
              # The below step is to check if the path contains MV, if it does, we will add it to the updateFields.
              if re.search(MV_pattern, pathWithFractionName):
                patientPack['updateFields'][key] = pathWithFractionName
            else:
              patientPack['updateFields'][key] = pathWithFractionName
          # If the path with fraction name does not exist, we will check if the path with fraction exists.
          elif os.path.exists(rootPath + pathWithFraction):
            if re.search(KV_pattern, key):
              pathWithFraction = _tryToFindKVorMVFolder(rootPath, pathWithFraction, 'KV')
              if re.search(KV_pattern, pathWithFraction):
                patientPack['updateFields'][key] = pathWithFraction
            elif re.search(MV_pattern, key):
              pathWithFraction = _tryToFindKVorMVFolder(rootPath, pathWithFraction, 'MV')
              if re.search(MV_pattern, pathWithFraction):
                patientPack['updateFields'][key] = pathWithFraction
            else:
              patientPack['updateFields'][key] = pathWithFraction
      if patientPack['updateFields']:
        returnPack.append(patientPack)
    return make_response(returnPack)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)

def addNewFraction(req):
  payload = req.json
  patientId = payload["patientId"]
  fractionName = payload["fractionName"]
  # check if fraction name exists
  sqlStmt = f"SELECT get_fraction_id_for_patient ('{patientId}', '{fractionName}')"
  result = executeQuery(sqlStmt)
  print(result)
  if result:
    return make_response({"message": "Fraction name already exists"}, 400)
  fractionDate = payload["fractionDate"] if "fractionDate" in payload else 'Null'
  if fractionDate != 'Null':
    fractionDate = f"'{fractionDate}'"
  mvsdd = payload["mvsdd"] if "mvsdd" in payload else 'Null'
  kvsdd = payload["kvsdd"] if "kvsdd" in payload else 'Null'
  kvPixelSize = payload["kvPixelSize"] if "kvPixelSize" in payload else 'Null'
  mvPixelSize = payload["mvPixelSize"] if "mvPixelSize" in payload else 'Null'
  markerLength = payload["markerLength"] if "markerLength" in payload else 'Null'
  markerWidth = payload["markerWidth"] if "markerWidth" in payload else 'Null'

  try:
    sqlStmt = f"INSERT INTO fraction (prescription_id, fraction_number, fraction_name, fraction_date, mvsdd, kvsdd, kv_pixel_size, mv_pixel_size, marker_length, marker_width) VALUES ((SELECT prescription_id FROM prescription WHERE patient_id=(SELECT id FROM patient WHERE patient_trial_id='{patientId}')), {payload['fractionNumber']}, '{fractionName}', {fractionDate}, {mvsdd}, {kvsdd}, {kvPixelSize}, {mvPixelSize}, {markerLength}, {markerWidth})"
    executeQuery(sqlStmt)
    fractionId = executeQuery(f"SELECT get_fraction_id_for_patient ('{patientId}', '{fractionName}')")[0][0]
    sqlStmt = f"INSERT INTO images (fraction_id) VALUES ({fractionId})"
    executeQuery(sqlStmt)    
    return make_response({"message": "Fraction added successfully"}, 200)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": "Failed to add fraction"}, 400)