from flask import make_response
from .util import executeQuery
import sys
import csv
import io

def getPatientList(req):
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
  
def addOnePatient(req):
  rawData = req.json
  patientInfo = {}
  linacType = ''
  for key in rawData.keys():
    if key == 'linac_type':
      linacType = rawData[key]
      continue
    if key == 'gender':
      if rawData['gender'] == 'Male':
        patientInfo['gender'] = 'M'
      elif rawData['gender'] == 'Female':
        patientInfo['gender'] = 'F'
      else:
        patientInfo['gender'] = 'O'
      continue
    if rawData[key]:
      patientInfo[key] = rawData[key]

  checkPatientStmt = f"SELECT * FROM patient WHERE patient_trial_id='{patientInfo['patient_trial_id']}';"
  fetchedRows = executeQuery(checkPatientStmt)
  if fetchedRows:
    return make_response({"message": "Patient already exists"}, 400)

  sqlStmt = "INSERT INTO patient ("
  sqlStmt += ', '.join([key for key in patientInfo])
  sqlStmt += ") VALUES ("
  sqlStmt += ', '.join([f"'{patientInfo[key]}'" for key in patientInfo])
  sqlStmt += ");"
  try:
    executeQuery(sqlStmt)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": "Failed to add patient"}, 400)
  
  getPatientUUIDStmt = f"SELECT id FROM patient WHERE patient_trial_id='{patientInfo['patient_trial_id']}';"
  fetchedRows = executeQuery(getPatientUUIDStmt)
  patientUUID = fetchedRows[0][0]
  if not patientUUID:
    return make_response({"message": "Failed to add patient"}, 400)
  sqlStmt2 = f"INSERT INTO prescription (patient_id, linac_type) VALUES ('{patientUUID}', '{linacType}');"
  try:
    executeQuery(sqlStmt2)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": "Failed to add patient"}, 400)
  
  return make_response({"message": "Patient added successfully"}, 200)

  
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
  



  return make_response({"message": "Not implemented yet"}, 501)
  pass