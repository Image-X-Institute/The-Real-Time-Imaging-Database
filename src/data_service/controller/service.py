from AccessManager import getSites, getTrials
from dbconnector import DBConnector
from flask import make_response
import config
import psycopg2 as pg
import psycopg2.extras
import sys

def _executeQuery(queryStmt:str, withDictCursor:bool=False, authDB=False):
  if authDB:
    connector = DBConnector(config.AUTH_DB_NAME, 
                            config.AUTH_DB_USER, 
                            config.AUTH_DB_PASSWORD,
                            config.AUTH_DB_HOST)
  else:
    connector = DBConnector(config.DB_NAME, 
                            config.DB_USER, 
                            config.DB_PASSWORD,
                            config.DB_HOST)
  connector.connect()
  conn = connector.getConnection()

  fetchedRows = None
  try:
    if withDictCursor:
      cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
      cur.execute(queryStmt)
      fetchedRows = cur.fetchall()
      colName = [desc[0] for desc in cur.description]
      fetchedRows = [dict(zip(colName, row)) for row in fetchedRows]
    else:
      cur = conn.cursor()
      cur.execute(queryStmt)
      conn.commit()
      fetchedRows = cur.fetchall()
    cur.close()
  except (Exception, pg.DatabaseError) as err:
    print(err, file=sys.stderr)
  return fetchedRows

def getTrialList(req):
  trials = getTrials()
  trials = {"trials": [trial.name for trial in trials]}
  rsp = make_response(trials)
  return rsp

def getCenterList(req):
  sites = getSites()
  sites = {"sites": [site.name for site in sites]}
  rsp = make_response(sites)
  return rsp

def getPatientList(req):
  trialName = req.args.get("trialName")
  siteName = req.args.get("siteName")
  sqlStmt = f"SELECT patient_trial_id FROM patient WHERE clinical_trial='{trialName}' AND test_centre='{siteName}'"
  fetchedRows = _executeQuery(sqlStmt)
  if fetchedRows is None:
    return make_response("No patients found", 400)
  fetchedRows = {"patients": [row[0] for row in fetchedRows]}
  rsp = make_response(fetchedRows)
  return rsp

def getPatientInfo(req):
  try:
    patientId = req.args.get("patientId")
    sqlStmt = f"SELECT * FROM patient, prescription WHERE patient_trial_id='{patientId}' AND patient.id = prescription.patient_id"
    fetchedRows = _executeQuery(sqlStmt, withDictCursor=True)[0]
    trial = fetchedRows["clinical_trial"]
    sqlStmt2 = f"SELECT trial_structure FROM trials WHERE trial_name='{trial}'"
    fetchedRows2 = _executeQuery(sqlStmt2, authDB=True)
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
      _executeQuery(patientUpdateStmt)

    if changeInPrescriptionTable:
      columnString = ', '.join([f"{key}='{changeInPrescriptionTable[key]}'" for key in changeInPrescriptionTable])
      prescriptionUpdateStmt = f"UPDATE prescription SET {columnString} WHERE patient_id=(SELECT id FROM patient WHERE patient_trial_id='{patientId}');"
      _executeQuery(prescriptionUpdateStmt)

    return make_response({"message": "Patient info updated successfully"}, 200)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": "Failed to update patient info"}, 400)


def getFractionDetialByPatientId(req):
  patientId = req.args.get("patientId")
  trial = req.args.get("trialName")
  sqlStmt = f"Select * from patient, prescription, fraction, images where patient.id = prescription.patient_id and prescription.prescription_id=fraction.prescription_id and images.fraction_id=fraction.fraction_id and patient.patient_trial_id='{patientId}'"
  result = _executeQuery(sqlStmt, withDictCursor=True)
  if result is None:
    return make_response("No fraction found", 400)

  trialStructure = _executeQuery(f"SELECT trial_structure FROM trials WHERE trial_name='{trial}'", authDB=True)[0][0]['fraction']
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
    _executeQuery(sqlStmt)
    return make_response({"message": "Fraction info updated successfully"}, 200)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": "Failed to update patient info"}, 400)

def getPatientTrialStats(req):
  try:
    sqlStmt = "SELECT clinical_trial, COUNT(*) FROM patient GROUP BY clinical_trial;"
    fetchedRows = _executeQuery(sqlStmt)
    if fetchedRows is None:
      return make_response("No patients found", 400)
    fetchedRows = {row[0]: row[1] for row in fetchedRows}

    sqlStmt2 = "SELECT clinical_trial, COUNT(*), test_centre FROM patient GROUP BY clinical_trial, test_centre"
    fetchedRows2 = _executeQuery(sqlStmt2)
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

def getMissingPrescriptionFieldCheck(req):
  try:
    trialName = req.args.get("trialName")
    sqlStmt = f"SELECT * FROM patient, prescription WHERE clinical_trial='{trialName}' AND patient.id = prescription.patient_id"
    fetchedRows = _executeQuery(sqlStmt, withDictCursor=True)
    sqlStmt2 = f"SELECT trial_structure FROM trials WHERE trial_name='{trialName}'"
    fetchedRows2 = _executeQuery(sqlStmt2, authDB=True)
    trialStructure = fetchedRows2[0][0]['prescription']
    requiredFields = list(trialStructure.keys()) + ["age", "avg_treatment_time", "centre_patient_no", "clinical_diag", "clinical_trial", "gender", "linac_type","number_of_markers", "patient_note", "patient_trial_id", "tumour_site", "test_centre"]
    missingFields = []
    for row in fetchedRows:
      missedPack = {}
      missedPack['patient_trial_id'] = row['patient_trial_id']
      missedPack['clinical_trial'] = row['clinical_trial']
      missedPack['test_centre'] = row['test_centre']
      missedPack['missedFields'] = {key: row[key] for key in requiredFields if row[key] == None or row[key] == "not found" or row[key] == ""}
      missingFields.append(missedPack)
    return make_response(missingFields)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": "Failed to get missing field check"}, 400)

def getMissingFractionFieldCheck(req):
  try:
    trialName = req.args.get("trialName")
    sqlStmt = f"SELECT * FROM patient, prescription, fraction, images WHERE clinical_trial='{trialName}' AND patient.id = prescription.patient_id AND prescription.prescription_id=fraction.prescription_id and fraction.fraction_id=images.fraction_id"
    fetchedRows = _executeQuery(sqlStmt, withDictCursor=True)
    sqlStmt2 = f"SELECT trial_structure FROM trials WHERE trial_name='{trialName}'"
    fetchedRows2 = _executeQuery(sqlStmt2, authDB=True)
    trialStructure = fetchedRows2[0][0]['fraction']
    requiredFields = list(trialStructure.keys()) + ["fraction_number","fraction_name"]
    missingFields = []
    for row in fetchedRows:
      missedPack = {}
      missedPack['patient_trial_id'] = row['patient_trial_id']
      missedPack['clinical_trial'] = row['clinical_trial']
      missedPack['test_centre'] = row['test_centre']
      missedPack['fraction_number'] = row['fraction_number']
      missedPack['fraction_name'] = row['fraction_name']
      missedPack['missedFields'] = {key: row[key.lower()] for key in requiredFields if row[key.lower()] == None or row[key.lower()] == "not found" or row[key.lower()] == ""}
      missingFields.append(missedPack)
    reorganisedFields = {}
    for row in missingFields:
      if row['test_centre'] not in reorganisedFields.keys():
        reorganisedFields[row['test_centre']] = {}
      if row['patient_trial_id'] not in reorganisedFields[row['test_centre']].keys():
        reorganisedFields[row['test_centre']][row['patient_trial_id']] = {}
      if row['fraction_number'] not in reorganisedFields[row['test_centre']][row['patient_trial_id']].keys():
        reorganisedFields[row['test_centre']][row['patient_trial_id']][row['fraction_number']] = {}
      reorganisedFields[row['test_centre']][row['patient_trial_id']][row['fraction_number']][row['fraction_name']] = row['missedFields']
    return make_response(reorganisedFields)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": "Failed to get missing field check"}, 400)