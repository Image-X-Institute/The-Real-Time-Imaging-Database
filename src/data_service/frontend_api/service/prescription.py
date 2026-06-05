from flask import make_response
from .util import executeQuery
from dbconnector import DBConnector
import sys
import config
import os
import csv
import io
import datetime as dt
import psycopg2 as pg
import psycopg2.extras

prescriptionBaseCsvHeaders = [
  "patient_trial_id(*)",
  "clinical_trial(*)",
  "test_centre(*)",
  "centre_patient_no(*)",
  "age",
  "gender",
  "tumour_site(*)",
  "avg_treatment_time",
  "clinical_diag",
  "kim_accuracy",
  "linac_type(*)",
  "number_of_markers",
  "patient_note"
]

prescriptionPatientCsvFieldDict = {
  "patient_trial_id(*)": "patient_trial_id",
  "patient_trial_id": "patient_trial_id",
  "clinical_trial(*)": "clinical_trial",
  "clinical_trial": "clinical_trial",
  "test_centre(*)": "test_centre",
  "test_centre": "test_centre",
  "centre_patient_no(*)": "centre_patient_no",
  "centre_patient_no": "centre_patient_no",
  "age": "age",
  "gender": "gender",
  "tumour_site(*)": "tumour_site",
  "tumour_site": "tumour_site",
  "avg_treatment_time": "avg_treatment_time",
  "clinical_diag": "clinical_diag",
  "kim_accuracy": "kim_accuracy",
  "number_of_markers": "number_of_markers",
  "patient_note": "patient_note"
}

prescriptionTableColumns = {
  "linac_type",
  "rt_plan_pres",
  "rt_ct_pres",
  "rt_structure_pres",
  "rt_dose_pres",
  "rt_mri_pres",
  "planned_dvh_pres",
  "centroid_path",
  "centroid_pres",
  "planned_dicom_pres",
  "magik_visual",
  "magik_model",
  "marker_offsets",
  "cardiac_ct",
  "fused_ct",
  "test1"
}

prescriptionCsvFieldDict = {
  "linac_type(*)": "linac_type",
  "linac_type": "linac_type",
}
for prescriptionColumn in prescriptionTableColumns:
  prescriptionCsvFieldDict[prescriptionColumn] = prescriptionColumn

prescriptionRequiredCsvHeaders = [
  "patient_trial_id(*)",
  "clinical_trial(*)",
  "test_centre(*)",
  "centre_patient_no(*)",
  "tumour_site(*)"
]

prescriptionIntegerColumns = {"age", "centre_patient_no", "number_of_markers"}
prescriptionFloatColumns = {"kim_accuracy"}

def _connectToImagingDb():
  connector = DBConnector(config.DB_NAME,
                          config.DB_USER,
                          config.DB_PASSWORD,
                          config.DB_HOST,
                          config.DB_PORT)
  connector.connect()
  conn = connector.getConnection()
  if conn is None:
    raise RuntimeError("Could not connect to imaging database.")
  return connector, conn

def _jsonSafeValue(value):
  if isinstance(value, (dt.date, dt.datetime)):
    return value.isoformat()
  if isinstance(value, dt.timedelta):
    return str(value)
  return value

def _formatCsvOutputValue(value):
  if value is None:
    return ""
  if isinstance(value, (dt.date, dt.datetime)):
    return value.isoformat()
  if isinstance(value, dt.timedelta):
    return str(value)
  return value

def _normaliseGender(value):
  if value is None:
    return None
  normalisedValue = value.strip()
  if normalisedValue == "":
    return None
  if normalisedValue.lower() == "male":
    return "M"
  if normalisedValue.lower() == "female":
    return "F"
  if normalisedValue.lower() in ["other", "o"]:
    return "O"
  if normalisedValue.upper() in ["M", "F"]:
    return normalisedValue.upper()
  return "O"

def _normaliseCsvValue(columnName, rawValue):
  if rawValue is None:
    return None

  value = rawValue.strip()
  if value == "":
    return None

  if columnName == "gender":
    return _normaliseGender(value)

  if columnName in prescriptionIntegerColumns:
    return int(float(value))

  if columnName in prescriptionFloatColumns:
    return float(value)

  return value

def _valuesAreDifferent(dbValue, csvValue):
  if isinstance(dbValue, str):
    dbValue = dbValue.strip()
  if isinstance(csvValue, str):
    csvValue = csvValue.strip()
  if isinstance(dbValue, float) and isinstance(csvValue, float):
    return abs(dbValue - csvValue) > 1e-9
  return dbValue != csvValue

def _getTrialPrescriptionFields(trialName):
  if not trialName:
    return []

  try:
    rows = executeQuery(f"SELECT trial_structure FROM trials WHERE trial_name='{trialName}'", authDB=True)
    if not rows:
      return []
    prescriptionStructure = rows[0][0].get("prescription", {})
    return [field for field in prescriptionStructure.keys() if field in prescriptionTableColumns]
  except Exception as err:
    print(err, file=sys.stderr)
    return []

def _readPrescriptionCsv(reader, clearEmptyFields=False):
  records = {}
  skippedRows = []

  if not reader.fieldnames:
    raise ValueError("CSV file is empty or missing a header row.")

  missingHeaders = [header for header in prescriptionRequiredCsvHeaders if header not in reader.fieldnames]
  if missingHeaders:
    raise ValueError(f"CSV missing required columns: {', '.join(missingHeaders)}")

  for rowNumber, row in enumerate(reader, start=2):
    if not any(value and value.strip() for value in row.values()):
      continue

    patientId = (row.get("patient_trial_id(*)") or row.get("patient_trial_id") or "").strip()
    if not patientId:
      skippedRows.append({"rowNumber": rowNumber, "reason": "Missing patient_trial_id"})
      continue

    if patientId in records:
      skippedRows.append({
        "rowNumber": rowNumber,
        "patientId": patientId,
        "reason": "Duplicate patient_trial_id in CSV"
      })
      continue

    patientValues = {}
    prescriptionValues = {}
    try:
      for csvColumn, dbColumn in prescriptionPatientCsvFieldDict.items():
        if csvColumn not in row:
          continue
        if row[csvColumn] is None or row[csvColumn].strip() == "":
          if clearEmptyFields and csvColumn not in prescriptionRequiredCsvHeaders:
            patientValues[dbColumn] = None
          continue
        patientValues[dbColumn] = _normaliseCsvValue(dbColumn, row[csvColumn])

      for csvColumn, dbColumn in prescriptionCsvFieldDict.items():
        if csvColumn not in row:
          continue
        if row[csvColumn] is None or row[csvColumn].strip() == "":
          if clearEmptyFields and csvColumn != "linac_type(*)":
            prescriptionValues[dbColumn] = None
          continue
        prescriptionValues[dbColumn] = _normaliseCsvValue(dbColumn, row[csvColumn])
    except ValueError as err:
      skippedRows.append({
        "rowNumber": rowNumber,
        "patientId": patientId,
        "reason": f"Invalid value: {err}"
      })
      continue

    missingRequiredValues = []
    for csvColumn, dbColumn in prescriptionPatientCsvFieldDict.items():
      if csvColumn in prescriptionRequiredCsvHeaders and dbColumn not in patientValues:
        missingRequiredValues.append(csvColumn)
    if missingRequiredValues:
      skippedRows.append({
        "rowNumber": rowNumber,
        "patientId": patientId,
        "reason": f"Missing required values: {', '.join(missingRequiredValues)}"
      })
      continue

    records[patientId] = {
      "patientId": patientId,
      "patientValues": patientValues,
      "prescriptionValues": prescriptionValues
    }

  return records, skippedRows

def _loadPrescriptionCsvContent(csvContent, clearEmptyFields=False):
  return _readPrescriptionCsv(csv.DictReader(io.StringIO(csvContent)), clearEmptyFields)

def _loadPrescriptionCsv(filePath, clearEmptyFields=False):
  with open(filePath, newline='', encoding='utf-8-sig') as csvFile:
    return _readPrescriptionCsv(csv.DictReader(csvFile), clearEmptyFields)

def _fetchExistingPrescriptionRows(cur, trialName, siteName=None, patientId=None, patientIds=None):
  query = """
    SELECT
      patient.id,
      patient.age,
      patient.gender,
      patient.clinical_diag,
      patient.tumour_site,
      patient.patient_trial_id,
      patient.clinical_trial,
      patient.test_centre,
      patient.centre_patient_no,
      patient.number_of_markers,
      patient.avg_treatment_time,
      patient.kim_accuracy,
      patient.patient_note,
      prescription.prescription_id,
      prescription.linac_type,
      prescription.rt_plan_pres,
      prescription.rt_ct_pres,
      prescription.rt_structure_pres,
      prescription.rt_dose_pres,
      prescription.rt_mri_pres,
      prescription.planned_dvh_pres,
      prescription.centroid_path,
      prescription.centroid_pres,
      prescription.planned_dicom_pres,
      prescription.magik_visual,
      prescription.magik_model,
      prescription.marker_offsets,
      prescription.cardiac_ct,
      prescription.fused_ct,
      prescription.test1
    FROM patient
    LEFT JOIN prescription ON patient.id = prescription.patient_id
    WHERE patient.clinical_trial = %s
  """
  params = [trialName]

  if siteName:
    query += " AND patient.test_centre = %s"
    params.append(siteName)

  if patientId:
    query += " AND patient.patient_trial_id = %s"
    params.append(patientId)

  if patientIds is not None:
    if not patientIds:
      return {}
    query += " AND patient.patient_trial_id = ANY(%s)"
    params.append(patientIds)

  cur.execute(query, params)
  return {row["patient_trial_id"]: row for row in cur.fetchall()}

def _insertPatientAndPrescription(cur, patientValues, prescriptionValues):
  patientColumns = list(patientValues.keys())
  patientPlaceholders = ', '.join(['%s'] * len(patientColumns))
  cur.execute(
    f"INSERT INTO patient ({', '.join(patientColumns)}) VALUES ({patientPlaceholders}) RETURNING id",
    [patientValues[column] for column in patientColumns]
  )
  patientUuid = cur.fetchone()["id"]

  prescriptionValues = dict(prescriptionValues)
  prescriptionValues["patient_id"] = patientUuid
  prescriptionColumns = list(prescriptionValues.keys())
  prescriptionPlaceholders = ', '.join(['%s'] * len(prescriptionColumns))
  cur.execute(
    f"INSERT INTO prescription ({', '.join(prescriptionColumns)}) VALUES ({prescriptionPlaceholders}) RETURNING prescription_id",
    [prescriptionValues[column] for column in prescriptionColumns]
  )
  return patientUuid

def _insertPrescription(cur, patientUuid, prescriptionValues):
  prescriptionValues = dict(prescriptionValues)
  prescriptionValues["patient_id"] = patientUuid
  prescriptionColumns = list(prescriptionValues.keys())
  prescriptionPlaceholders = ', '.join(['%s'] * len(prescriptionColumns))
  cur.execute(
    f"INSERT INTO prescription ({', '.join(prescriptionColumns)}) VALUES ({prescriptionPlaceholders}) RETURNING prescription_id",
    [prescriptionValues[column] for column in prescriptionColumns]
  )
  return cur.fetchone()["prescription_id"]

def _updateTable(cur, tableName, idColumn, idValue, changedFields):
  if not changedFields:
    return
  setClause = ', '.join([f"{column} = %s" for column in changedFields.keys()])
  params = list(changedFields.values()) + [idValue]
  cur.execute(f"UPDATE {tableName} SET {setClause} WHERE {idColumn} = %s", params)

def _deletePatientsWithRelations(cur, patientUuids):
  if not patientUuids:
    return
  cur.execute("""
    DELETE FROM images
    WHERE fraction_id IN (
      SELECT fraction.fraction_id
      FROM fraction
      JOIN prescription ON fraction.prescription_id = prescription.prescription_id
      WHERE prescription.patient_id = ANY(%s)
    )
  """, (patientUuids,))
  cur.execute("""
    DELETE FROM fraction
    WHERE prescription_id IN (
      SELECT prescription_id FROM prescription WHERE patient_id = ANY(%s)
    )
  """, (patientUuids,))
  cur.execute("DELETE FROM prescription WHERE patient_id = ANY(%s)", (patientUuids,))
  cur.execute("DELETE FROM patient WHERE id = ANY(%s)", (patientUuids,))

def exportPrescriptionCsv(req):
  trialName = req.args.get("trialName")
  siteName = req.args.get("siteName")
  patientId = req.args.get("patientId")

  if not trialName:
    return make_response({"message": "trialName is required."}, 400)

  connector = None
  conn = None
  try:
    extraPrescriptionFields = _getTrialPrescriptionFields(trialName)
    headers = prescriptionBaseCsvHeaders + [
      field for field in extraPrescriptionFields if field not in ["linac_type"]
    ]

    connector, conn = _connectToImagingDb()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    rows = _fetchExistingPrescriptionRows(cur, trialName, siteName, patientId).values()

    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(headers)
    for row in rows:
      writer.writerow([
        _formatCsvOutputValue(row["patient_trial_id"]),
        _formatCsvOutputValue(row["clinical_trial"]),
        _formatCsvOutputValue(row["test_centre"]),
        _formatCsvOutputValue(row["centre_patient_no"]),
        _formatCsvOutputValue(row["age"]),
        _formatCsvOutputValue(row["gender"]),
        _formatCsvOutputValue(row["tumour_site"]),
        _formatCsvOutputValue(row["avg_treatment_time"]),
        _formatCsvOutputValue(row["clinical_diag"]),
        _formatCsvOutputValue(row["kim_accuracy"]),
        _formatCsvOutputValue(row["linac_type"]),
        _formatCsvOutputValue(row["number_of_markers"]),
        _formatCsvOutputValue(row["patient_note"]),
        *[_formatCsvOutputValue(row[field]) for field in headers[len(prescriptionBaseCsvHeaders):]]
      ])

    rowCount = len(rows)
    cur.close()
    conn.close()
    connector.connection = None
    return make_response({
      "prescriptionCsv": output.getvalue(),
      "rowCount": rowCount,
      "trialName": trialName,
      "siteName": siteName,
      "patientId": patientId
    }, 200)
  except (Exception, pg.DatabaseError) as err:
    print(err, file=sys.stderr)
    try:
      if conn:
        conn.close()
      if connector:
        connector.connection = None
    except:
      pass
    return make_response({"message": "Failed to export prescription CSV.", "error": str(err)}, 400)

def syncPrescriptionCsv(req):
  payload = req.json
  if not payload or ("filePath" not in payload and "csvContent" not in payload):
    return make_response({"message": "filePath or csvContent is required."}, 400)

  filePath = payload.get("filePath")
  csvContent = payload.get("csvContent")
  fileName = payload.get("fileName")
  trialName = payload.get("trialName")
  siteName = payload.get("siteName")
  patientId = payload.get("patientId")
  dryRun = bool(payload.get("dryRun", False))
  deleteMissing = bool(payload.get("deleteMissing", False))
  clearEmptyFields = bool(payload.get("clearEmptyFields", False))

  if not trialName:
    return make_response({"message": "trialName is required."}, 400)
  if filePath and not os.path.isfile(filePath):
    return make_response({"message": f"CSV file not found: {filePath}"}, 400)

  connector = None
  conn = None
  try:
    if csvContent is not None:
      records, skippedRows = _loadPrescriptionCsvContent(csvContent, clearEmptyFields)
    else:
      records, skippedRows = _loadPrescriptionCsv(filePath, clearEmptyFields)

    connector, conn = _connectToImagingDb()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    existingRows = _fetchExistingPrescriptionRows(cur, trialName, siteName, patientId)

    inserted = []
    updated = []
    deleted = []
    skippedRows = list(skippedRows)
    unchangedCount = 0

    for recordPatientId, record in records.items():
      patientValues = record["patientValues"]
      prescriptionValues = record["prescriptionValues"]

      if patientValues.get("clinical_trial") != trialName:
        skippedRows.append({
          "patientId": recordPatientId,
          "reason": f"CSV clinical_trial does not match selected trialName {trialName}"
        })
        continue
      if siteName and patientValues.get("test_centre") != siteName:
        skippedRows.append({
          "patientId": recordPatientId,
          "reason": f"CSV test_centre does not match selected siteName {siteName}"
        })
        continue
      if patientId and recordPatientId != patientId:
        skippedRows.append({
          "patientId": recordPatientId,
          "reason": f"CSV patient ID does not match selected patientId {patientId}"
        })
        continue

      existingRow = existingRows.get(recordPatientId)
      if existingRow is None:
        if not dryRun:
          _insertPatientAndPrescription(cur, patientValues, prescriptionValues)
        inserted.append({
          "patientId": recordPatientId,
          "patientFields": sorted(patientValues.keys()),
          "prescriptionFields": sorted(prescriptionValues.keys())
        })
        continue

      changedPatientFields = {}
      for column, csvValue in patientValues.items():
        if column == "patient_trial_id":
          continue
        if _valuesAreDifferent(existingRow[column], csvValue):
          changedPatientFields[column] = csvValue

      changedPrescriptionFields = {}
      for column, csvValue in prescriptionValues.items():
        if _valuesAreDifferent(existingRow[column], csvValue):
          changedPrescriptionFields[column] = csvValue

      if changedPatientFields or changedPrescriptionFields:
        if not dryRun:
          _updateTable(cur, "patient", "id", existingRow["id"], changedPatientFields)
          if existingRow["prescription_id"]:
            _updateTable(cur, "prescription", "prescription_id", existingRow["prescription_id"], changedPrescriptionFields)
          else:
            _insertPrescription(cur, existingRow["id"], prescriptionValues)
        updated.append({
          "patientId": recordPatientId,
          "patientFields": {key: _jsonSafeValue(value) for key, value in changedPatientFields.items()},
          "prescriptionFields": {key: _jsonSafeValue(value) for key, value in changedPrescriptionFields.items()}
        })
      else:
        unchangedCount += 1

    if deleteMissing:
      csvPatientIds = set(records.keys())
      patientUuidsToDelete = []
      for existingPatientId, existingRow in existingRows.items():
        if existingPatientId in csvPatientIds:
          continue
        patientUuidsToDelete.append(existingRow["id"])
        deleted.append({"patientId": existingPatientId})
      if patientUuidsToDelete and not dryRun:
        _deletePatientsWithRelations(cur, patientUuidsToDelete)

    if dryRun:
      conn.rollback()
    else:
      conn.commit()
    cur.close()
    conn.close()
    connector.connection = None

    return make_response({
      "message": "Prescription CSV sync completed.",
      "dryRun": dryRun,
      "filePath": filePath,
      "fileName": fileName,
      "trialName": trialName,
      "siteName": siteName,
      "patientId": patientId,
      "deleteMissing": deleteMissing,
      "clearEmptyFields": clearEmptyFields,
      "validCsvRows": len(records),
      "insertedCount": len(inserted),
      "updatedCount": len(updated),
      "deletedCount": len(deleted),
      "unchangedCount": unchangedCount,
      "skippedRows": skippedRows,
      "inserted": inserted,
      "updated": updated,
      "deleted": deleted
    }, 200)
  except (Exception, pg.DatabaseError) as err:
    print(err, file=sys.stderr)
    try:
      if conn:
        conn.rollback()
        conn.close()
      if connector:
        connector.connection = None
    except:
      pass
    return make_response({"message": "Failed to sync prescription CSV.", "error": str(err)}, 400)

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
      missedPack['tumour_site'] = row['tumour_site']
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
    rootDrivePath = req.args.get("rootDrivePath")
    rootPath = config.DATA_FILESYSTEM_ROOT_PREFIX + rootDrivePath
    if rootDrivePath and os.path.exists(rootPath):
      rootPath = rootPath
    else:
      rootPath = config.DATA_FILESYSTEM_ROOT
    sqlStmt2 = f"SELECT trial_structure FROM trials WHERE trial_name='{trialName}'"
    fetchedRows2 = executeQuery(sqlStmt2, authDB=True)
    trialStructure = fetchedRows2[0][0]['prescription']
    returnPack = []
    for field in missingFields:
      patientPack = {
        "patient_trial_id": field['patient_trial_id'],
        "updateFields": {}
      }
      for key in field['missedFields']:
        if key in trialStructure.keys():
          filePath = trialStructure[key]['path']
          formatedPath = filePath.format(clinical_trial=trialName, tumour_site=field['tumour_site'], test_centre=field['test_centre'], centre_patient_no=str(field['centre_patient_no']).zfill(2))
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
