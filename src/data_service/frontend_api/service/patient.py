from flask import make_response
from .util import executeQuery
import sys
import csv
import io

def getPatientIdList(req):
  trialName = req.args.get("trialName")
  siteName = req.args.get("siteName")
  sqlStmt = f"SELECT patient_trial_id FROM patient WHERE clinical_trial='{trialName}' AND test_centre='{siteName}'"
  fetchedRows = executeQuery(sqlStmt)
  if fetchedRows is None:
    return make_response("No patients found", 400)
  fetchedRows = {"patients": [row[0] for row in fetchedRows]}
  rsp = make_response(fetchedRows)
  return rsp

def getPatientInfo(req):
  try:
    patientId = req.args.get("patientId")
    sqlStmt = f"SELECT * FROM patient, prescription WHERE patient_trial_id='{patientId}' AND patient.id = prescription.patient_id"
    fetchedRows = executeQuery(sqlStmt, withDictCursor=True)[0]
    trial = fetchedRows["clinical_trial"]
    sqlStmt2 = f"SELECT trial_structure FROM trials WHERE trial_name='{trial}'"
    fetchedRows2 = executeQuery(sqlStmt2, authDB=True)
    trialStructure = fetchedRows2[0][0]['prescription']
    requiredFields = list(trialStructure.keys()) + ["age", "avg_treatment_time", "centre_patient_no", "clinical_diag", "clinical_trial", "gender", "linac_type","number_of_markers", "patient_note", "patient_trial_id", "tumour_site", "test_centre"]
    fetchedRows = {key: fetchedRows[key] for key in requiredFields}
    if fetchedRows is None:
      return make_response("No patient found", 400)
    rsp = make_response(fetchedRows)
    return rsp
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response("No patient found", 400)
  

def updatePatientInfo(req):
  patientId = req.args.get("patientId")
  changes = req.json
  patientTableFields = ["age", "gender", "clinical_diag", "tumour_site", "patient_trial_id", "clinical_trial","test_centre", "centre_patient_no", "number_of_markers", "avg_treatment_time", "kim_accuracy", "patient_note"]
  changeInPatientTable = {key: changes[key] for key in patientTableFields if key in changes}
  changeInPrescriptionTable = {key: changes[key] for key in changes if key not in patientTableFields}
  try:
    if changeInPatientTable:
      columnString = ', '.join([f"{key}='{changeInPatientTable[key]}'" for key in changeInPatientTable])
      patientUpdateStmt = f"UPDATE patient SET {columnString} WHERE patient_trial_id='{patientId}';"
      executeQuery(patientUpdateStmt)

    if changeInPrescriptionTable:
      columnString = ', '.join([f"{key}='{changeInPrescriptionTable[key]}'" for key in changeInPrescriptionTable])
      prescriptionUpdateStmt = f"UPDATE prescription SET {columnString} WHERE patient_id=(SELECT id FROM patient WHERE patient_trial_id='{patientId}');"
      executeQuery(prescriptionUpdateStmt)

    return make_response({"message": "Patient info updated successfully"}, 200)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": "Failed to update patient info"}, 400)
  
def getPatientTrialStats(req):
  try:
    sqlStmt = "SELECT clinical_trial, COUNT(*) FROM patient GROUP BY clinical_trial;"
    fetchedRows = executeQuery(sqlStmt)
    if fetchedRows is None:
      return make_response("No patients found", 400)
    fetchedRows = {row[0]: row[1] for row in fetchedRows}

    sqlStmt2 = "SELECT clinical_trial, COUNT(*), test_centre FROM patient GROUP BY clinical_trial, test_centre"
    fetchedRows2 = executeQuery(sqlStmt2)
    if fetchedRows2 is None:
      return make_response("No patients found", 400)
    
    resultPack = {}
    resultPack['centreInTrials'] = {}
    for row in fetchedRows2:
      if row[0] not in resultPack['centreInTrials'].keys():
        resultPack['centreInTrials'][row[0]] = {}
      resultPack['centreInTrials'][row[0]][row[2]] = row[1]
    resultPack['totalPatients'] = sum(fetchedRows.values())
    resultPack['totalTrials'] = len(fetchedRows.keys())
    resultPack['patientInTrials'] = fetchedRows
    rsp = make_response(resultPack)
    return rsp
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": "Failed to get patient trial stats"}, 400)
  

def _addPatientToDB(rawData):

  formNameToTableName = {
    "patient_trial_id(*)": "patient_trial_id",
    "clinical_trial(*)": "clinical_trial",
    "test_centre(*)": "test_centre",
    "centre_patient_no(*)": "centre_patient_no",
    "tumour_site(*)": "tumour_site",
    "linac_type(*)": "linac_type",
  }

  patientInfo = {}
  linacType = ''
  for itemName in rawData.keys():
    if itemName in formNameToTableName.keys():
      key = formNameToTableName[itemName]
    else:
      key = itemName
    if key == 'linac_type':
      linacType = rawData[itemName]
      continue
    if key == 'gender':
      if rawData['gender'] == 'Male':
        patientInfo['gender'] = 'M'
      elif rawData['gender'] == 'Female':
        patientInfo['gender'] = 'F'
      else:
        patientInfo['gender'] = 'O'
      continue
    if rawData[itemName]:
      patientInfo[key] = rawData[itemName]
  try:
    checkPatientStmt = f"SELECT * FROM patient WHERE patient_trial_id='{patientInfo['patient_trial_id']}';"
    fetchedRows = executeQuery(checkPatientStmt)
    if fetchedRows:
      return False, {"message":f"Patient already exists, patient_trial_id: {patientInfo['patient_trial_id']}"}

    sqlStmt = "INSERT INTO patient ("
    sqlStmt += ', '.join([key for key in patientInfo])
    sqlStmt += ") VALUES ("
    sqlStmt += ', '.join([f"'{patientInfo[key]}'" for key in patientInfo])
    sqlStmt += ");"
  except Exception as err:
    print(err, file=sys.stderr)
    return False, {"message": "Failed to add patient, The sell value is empty or invalid"}
  try:
    executeQuery(sqlStmt)
  except Exception as err:
    print(err, file=sys.stderr)
    return False, {"message": f"Failed to add patient, patient_trial_id: {patientInfo['patient_trial_id']}"}
  
  getPatientUUIDStmt = f"SELECT id FROM patient WHERE patient_trial_id='{patientInfo['patient_trial_id']}';"
  fetchedRows = executeQuery(getPatientUUIDStmt)
  patientUUID = fetchedRows[0][0]
  if not patientUUID:
    return False, {"message": f"Failed to add patient, patient_trial_id: {patientInfo['patient_trial_id']}"}
  sqlStmt2 = f"INSERT INTO prescription (patient_id, linac_type) VALUES ('{patientUUID}', '{linacType}');"
  try:
    executeQuery(sqlStmt2)
  except Exception as err:
    print(err, file=sys.stderr)
    return False, {"message": f"Failed to add patient, patient_trial_id: {patientInfo['patient_trial_id']}"}
  
  return True, {"message": "Patient added successfully"}

def addOnePatient(req):
  rawData = req.json
  status, rsp = _addPatientToDB(rawData)
  if status:
    return make_response(rsp, 200)
  else:
    return make_response(rsp, 400)
  
def addBulkPatient(req):
  rawData = req.json
  csvRawData = csv.reader(io.StringIO(rawData['patientList']))
  csvHeader = next(csvRawData)
  patientInfoList = []
  row = next(csvRawData)
  while row:
    patientInfoList.append({csvHeader[i]: row[i] for i in range(len(row))})
    try:
      row = next(csvRawData)
    except StopIteration:
      break
  resultList = []
  failedList = []
  for patientInfo in patientInfoList:
    patientId = patientInfo['patient_trial_id(*)']
    status, rsp = _addPatientToDB(patientInfo)
    if not status:
      failedList.append(patientId)
    else:
      resultList.append(patientId)
  if failedList and resultList:
    return make_response({"message": "Some patients failed to add", "failedPatients": failedList, "successPatients": resultList}, 200)
  elif resultList:
    return make_response({"message": "All patients added successfully", "successPatients": resultList}, 200)
  else:
    return make_response({"message": "All patients failed to add", "failedPatients": failedList}, 400)
  
def getPatientDetailList(req):
  trialName = req.args.get("trialName")
  sqlStmt = f"SELECT * FROM patient WHERE patient.clinical_trial='{trialName}'"
  fetchedRows = executeQuery(sqlStmt, withDictCursor=True)
  if fetchedRows is None:
    return make_response("No patients found", 400)
  
  exportPack = []
  for patient in fetchedRows:
    patientInfo = {
      "patient_trial_id": patient["patient_trial_id"],
      "clinical_trial": patient["clinical_trial"],
      "test_centre": patient["test_centre"],
      "centre_patient_no": patient["centre_patient_no"],
      "tumour_site": patient["tumour_site"]
    }
    exportPack.append(patientInfo)
  rsp = make_response({"patients": exportPack}, 200)
  return rsp

def deleteOnePatient(req):
  payload = req.json
  patientId = payload['patientId']
  message = ""
  sqlGetPrescriptionId = f"SELECT prescription_id FROM prescription WHERE patient_id=(SELECT id FROM patient WHERE patient_trial_id='{patientId}');"
  fetchedRows = executeQuery(sqlGetPrescriptionId)
  message = "Patient not found"
  if not fetchedRows:
    return make_response({"message": message}, 400)
  prescriptionId = fetchedRows[0][0]
  sqlGetFractionIdList = f"SELECT fraction_id FROM fraction WHERE prescription_id='{prescriptionId}';"
  fetchedRows = executeQuery(sqlGetFractionIdList)
  message = "error while deleting from images table"
  try:
    fractionIdList = [row[0] for row in fetchedRows]
    for fractionId in fractionIdList:
      sqlDeleteImage = f"DELETE FROM images WHERE fraction_id='{fractionId}';"
      executeQuery(sqlDeleteImage)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": message}, 400)
  
  message = "error while deleting from fraction table"
  try:
    sqlDeleteFraction = f"DELETE FROM fraction WHERE prescription_id='{prescriptionId}';"
    executeQuery(sqlDeleteFraction)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": message}, 400)
  
  message = "error while deleting from prescription table"
  try:
    sqlDeletePrescription = f"DELETE FROM prescription WHERE prescription_id='{prescriptionId}';"
    executeQuery(sqlDeletePrescription)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": message}, 400)
  
  message = "error while deleting from patient table"
  try:
    sqlDeletePatient = f"DELETE FROM patient WHERE patient_trial_id='{patientId}';"
    executeQuery(sqlDeletePatient)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": message}, 400)
  
  message = "Patient deleted successfully"
  return make_response({"message": message}, 200)