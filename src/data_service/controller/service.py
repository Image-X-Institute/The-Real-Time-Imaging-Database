from AccessManager import getSites, getTrials
from dbconnector import DBConnector
from flask import make_response
import config
import psycopg2 as pg
import psycopg2.extras
import sys

def _executeQuery(queryStmt:str, withDictCursor:bool=False, authDB=None):
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
      fetchedRows = [dict(zip(colName, row)) for row in fetchedRows][0]
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
    patientID = req.args.get("patientID")
    sqlStmt = f"SELECT * FROM patient, prescription WHERE patient_trial_id='{patientID}' AND patient.id = prescription.patient_id"
    fetchedRows = _executeQuery(sqlStmt, withDictCursor=True)
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
  patientID = req.args.get("patientID")
  changes = req.json
  patientTableFields = ["age", "gender", "clinical_diag", "tumour_site", "patient_trial_id", "clinical_trial","test_centre", "centre_patient_no", "number_of_markers", "avg_treatment_time", "kim_accuracy", "patient_note"]
  changeInPatientTable = {key: changes[key] for key in patientTableFields if key in changes}
  changeInPrescriptionTable = {key: changes[key] for key in changes if key not in patientTableFields}
  try:
    if changeInPatientTable:
      columnString = ', '.join([f"{key}='{changeInPatientTable[key]}'" for key in changeInPatientTable])
      patientUpdateStmt = f"UPDATE patient SET {columnString} WHERE patient_trial_id='{patientID}';"
      _executeQuery(patientUpdateStmt)

    if changeInPrescriptionTable:
      columnString = ', '.join([f"{key}='{changeInPrescriptionTable[key]}'" for key in changeInPrescriptionTable])
      prescriptionUpdateStmt = f"UPDATE prescription SET {columnString} WHERE patient_id=(SELECT id FROM patient WHERE patient_trial_id='{patientID}');"
      _executeQuery(prescriptionUpdateStmt)

    return make_response({"message": "Patient info updated successfully"}, 200)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": "Failed to update patient info"}, 400)
