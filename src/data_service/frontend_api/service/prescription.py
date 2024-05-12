from flask import make_response
from .util import executeQuery
import sys
import config
import os

def _getMissingPrescriptionFieldCheck(pack):
  try:
    trialName = pack.args.get("trialName")
    sqlStmt = f"SELECT * FROM patient, prescription WHERE clinical_trial='{trialName}' AND patient.id = prescription.patient_id"
    fetchedRows = executeQuery(sqlStmt, withDictCursor=True)
    sqlStmt2 = f"SELECT trial_structure FROM trials WHERE trial_name='{trialName}'"
    fetchedRows2 = executeQuery(sqlStmt2, authDB=True)
    trialStructure = fetchedRows2[0][0]['prescription']
    requiredFields = list(trialStructure.keys()) + ["age", "avg_treatment_time", "centre_patient_no", "clinical_diag", "clinical_trial", "gender", "linac_type","number_of_markers", "patient_note", "patient_trial_id", "tumour_site", "test_centre"]
    missingFields = []
    for row in fetchedRows:
      missedPack = {}
      missedPack['patient_trial_id'] = row['patient_trial_id']
      missedPack['clinical_trial'] = row['clinical_trial']
      missedPack['test_centre'] = row['test_centre']
      missedPack['centre_patient_no'] = row['centre_patient_no']
      missedPack['missedFields'] = {key: row[key] for key in requiredFields if row[key] == None or row[key] == "not found" or row[key] == ""}
      missingFields.append(missedPack)
    return missingFields
  except Exception as err:
    print(err, file=sys.stderr)
    return None

def getMissingPrescriptionFieldCheck(req):
  missingFields = _getMissingPrescriptionFieldCheck(req)
  if missingFields == None:
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)
  return make_response(missingFields)
  

def getUpdatePrescriptionField(req):
  missingFields = _getMissingPrescriptionFieldCheck(req)
  if missingFields == None:
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)
  try:
    trialName = req.args.get("trialName")
    sqlStmt2 = f"SELECT trial_structure FROM trials WHERE trial_name='{trialName}'"
    fetchedRows2 = executeQuery(sqlStmt2, authDB=True)
    trialStructure = fetchedRows2[0][0]['prescription']
    rootPath = config.DATA_FILESYSTEM_ROOT
    returnPack = []
    for field in missingFields:
      patientPack = {
        "patient_trial_id": field['patient_trial_id'],
        "updateFields": {}
      }
      for key in field['missedFields']:
        if key in trialStructure.keys():
          filePath = trialStructure[key]['path']
          formatedPath = filePath.format(clinical_trial=trialName, test_centre=field['test_centre'], centre_patient_no=str(field['centre_patient_no']).zfill(2))
          path = rootPath + formatedPath
          if os.path.exists(path):
            # sqlStmt = f"UPDATE prescription SET {key}='{formatedPath}' WHERE prescription_id=(SELECT get_prescription_id_for_patient('{field['patient_trial_id']}'))"
            # executeQuery(sqlStmt)
            patientPack['updateFields'][key] = formatedPath
      if patientPack['updateFields']:
        returnPack.append(patientPack)
    return make_response(returnPack)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)
  
def updatePrescriptionField(req):
  updatePack = req.json
  print(updatePack)
  if updatePack == None:
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)
  try:
    for pack in updatePack:
      patientTrialId = pack['patient_trial_id']
      updateFields = pack['updateFields']
      for key in updateFields.keys():
        sqlStmt = f"UPDATE prescription SET {key}='{updateFields[key]}' WHERE prescription_id=(SELECT get_prescription_id_for_patient('{patientTrialId}'))"
        executeQuery(sqlStmt)
    return make_response({'message': 'Successfully updated prescription fields.'}, 200)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)
