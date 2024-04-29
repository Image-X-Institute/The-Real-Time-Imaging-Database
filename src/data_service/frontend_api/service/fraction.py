from flask import make_response
from .util import executeQuery
import sys
import config
import os
import re

def getFractionDetialByPatientId(req):
  patientId = req.args.get("patientId")
  trial = req.args.get("trialName")
  sqlStmt = f"Select * from patient, prescription, fraction, images where patient.id = prescription.patient_id and prescription.prescription_id=fraction.prescription_id and images.fraction_id=fraction.fraction_id and patient.patient_trial_id='{patientId}'"
  result = executeQuery(sqlStmt, withDictCursor=True)
  if result is None:
    return make_response("No fraction found", 400)

  trialStructure = executeQuery(f"SELECT trial_structure FROM trials WHERE trial_name='{trial}'", authDB=True)[0][0]['fraction']
  requiredFields = list(trialStructure.keys()) + ["fraction_number","fraction_name"]
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
  try:
    coloumnStr = ', '.join([f"{key}='{payload[key]}'" for key in payload if key not in ['patientId', 'fractionName']])
    sqlStmt = f"UPDATE images SET {coloumnStr} WHERE fraction_id=(SELECT get_fraction_id_for_patient ('{patientId}', '{fractionName}'));"
    executeQuery(sqlStmt)
    return make_response({"message": "Fraction info updated successfully"}, 200)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": "Failed to update patient info"}, 400)
  
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
          pathWithFraction = formatedPath + f'Fx{field["fraction_number"]}/'
          pathWithFractionName = pathWithFraction + field['fraction_name'] + '/'
          
          KV_pattern = r"kv"
          MV_pattern = r"mv"
          
          if re.search(KV_pattern, key):
            pathWithFractionName = pathWithFractionName + 'KIM-KV/'
            pathWithFraction = pathWithFraction + 'KIM-KV/'
          elif re.search(MV_pattern, key):
            pathWithFractionName = pathWithFractionName + 'KIM-MV/'
            pathWithFraction = pathWithFraction + 'KIM-MV/'

          if os.path.exists(rootPath + pathWithFractionName):
            patientPack['updateFields'][key] = pathWithFractionName
          elif os.path.exists(rootPath + pathWithFraction):
            patientPack['updateFields'][key] = pathWithFraction
      if patientPack['updateFields']:
        returnPack.append(patientPack)
    return make_response(returnPack)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)
  
def updateFractionField(req):
  updatePack = req.json
  if updatePack == None:
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)
  for update in updatePack:
    patientId = update["patient_trial_id"]
    fractionName = update["fraction_name"]
    for key in update["updateFields"]:
      try:
        sqlStmt = f"UPDATE images SET {key}='{update['updateFields'][key]}' WHERE fraction_id=(SELECT get_fraction_id_for_patient ('{patientId}', '{fractionName}'));"
        executeQuery(sqlStmt)
      except Exception as err:
        print(err, file=sys.stderr)
        return make_response({"message": "Failed to update patient info"}, 400)

  return make_response({"message": "Fraction info updated successfully"}, 200)