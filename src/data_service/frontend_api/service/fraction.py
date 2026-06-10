from flask import make_response
from .util import executeQuery
from dbconnector import DBConnector
import sys
import config
import os
import re
import csv
import io
import datetime as dt
import psycopg2 as pg
import psycopg2.extras
from trial_storage import (
  build_extended_data,
  get_field_table,
  get_stored_field_value,
  get_trial_fields,
  is_jsonb_field,
  jsonb_insert_value,
  set_jsonb_fields,
  split_values_by_storage,
  split_values_by_storage_table,
)

fractionTableItemList = [
    "fraction_number",
    "fraction_name",
    "mvsdd",
    "kvsdd",
    "kv_pixel_size",
    "mv_pixel_size",
    "marker_length",
    "marker_width",
    "marker_type",
    "imaging_kv",
    "imaging_ms",
    "imaging_ma"
  ]

fractionTableNameDict = {
  "fractionNumber(*)": "fraction_number",
  "fractionName(*)": "fraction_name",
  "fractionNumber": "fraction_number",
  "fractionName": "fraction_name",
  "fractionDate": "fraction_date",
  "mvsdd": "mvsdd",
  "kvsdd": "kvsdd",
  "kvPixelSize": "kv_pixel_size",
  "mvPixelSize": "mv_pixel_size",
  "markerLength": "marker_length",
  "markerWidth": "marker_width",
  "markerType": "marker_type",
  "imagingKV": "imaging_kv",
  "imagingMS": "imaging_ms",
  "imagingMA": "imaging_ma"
}

fractionSyncCsvFieldDict = {
  "fractionNumber(*)": "fraction_number",
  "fractionName(*)": "fraction_name",
  "fractionNumber": "fraction_number",
  "fractionName": "fraction_name",
  "fractionDate": "fraction_date",
  "mvsdd": "mvsdd",
  "kvsdd": "kvsdd",
  "kvPixelSize": "kv_pixel_size",
  "mvPixelSize": "mv_pixel_size",
  "markerLength": "marker_length",
  "markerWidth": "marker_width",
  "markerType": "marker_type",
  "imagingKV": "imaging_kv",
  "imagingMS": "imaging_ms",
  "imagingMA": "imaging_ma"
}

fractionSyncPatientIdFields = ["patientId(*)", "patientId", "patient_trial_id"]
fractionSyncNumericColumns = {
  "mvsdd", "kvsdd", "kv_pixel_size", "mv_pixel_size",
  "marker_length", "marker_width", "imaging_kv", "imaging_ma", "imaging_ms"
}
fractionSyncIntegerColumns = {"fraction_number"}

def _getTrialFractionStructure(trialName):
  if not trialName:
    return {}
  rows = executeQuery(f"SELECT trial_structure FROM trials WHERE trial_name='{trialName}'", authDB=True)
  if not rows:
    return {}
  return rows[0][0].get("fraction", {})

def _getTrialFractionFields(trialName, storage=None):
  return get_trial_fields(
    {"fraction": _getTrialFractionStructure(trialName)},
    "fraction",
    storage=storage,
  )

def _getFractionJsonbFieldsByTable(trialStructure):
  fieldsByTable = {"fraction": [], "images": []}
  for fieldName in get_trial_fields({"fraction": trialStructure}, "fraction", storage="jsonb"):
    tableName = get_field_table(
      {"fraction": trialStructure},
      "fraction",
      fieldName,
      fraction_table_fields=fractionTableItemList,
    )
    fieldsByTable.setdefault(tableName, []).append(fieldName)
  return fieldsByTable


def getFractionDetailByPatientId(req):
  patientId = req.args.get("patientId")
  trial = req.args.get("trialName")
  sqlStmt = f"Select patient.*, prescription.*, fraction.*, images.*, fraction.extended_data AS fraction_extended_data, images.extended_data AS images_extended_data from patient, prescription, fraction, images where patient.id = prescription.patient_id and prescription.prescription_id=fraction.prescription_id and images.fraction_id=fraction.fraction_id and patient.patient_trial_id='{patientId}'"
  result = executeQuery(sqlStmt, withDictCursor=True)
  if result is None:
    return make_response("No fraction found", 400)

  trialStructure = executeQuery(f"SELECT trial_structure FROM trials WHERE trial_name='{trial}'", authDB=True)[0][0]['fraction']
  requiredFields = list(trialStructure.keys()) + fractionTableItemList
  result = [
    {
      key: get_stored_field_value(
        row,
        {"fraction": trialStructure},
        "fraction",
        key,
        fraction_table_fields=fractionTableItemList,
      ) if key in trialStructure else row.get(key.lower())
      for key in requiredFields
    }
    for row in result
  ]
  fractionPack = {}
  for row in result:
    if row["fraction_number"] not in fractionPack.keys():
      fractionPack[row["fraction_number"]] = []
    fractionPack[row["fraction_number"]].append(row)

  return make_response(fractionPack)

def getFractionListByPatientId(req):
  patientId = req.args.get("patientId")
  sqlStmt = f"Select fraction_id, fraction_name, fraction_number, fraction_date from patient, prescription, fraction where patient.id = prescription.patient_id and prescription.prescription_id=fraction.prescription_id and patient.patient_trial_id='{patientId}'"
  result = executeQuery(sqlStmt, withDictCursor=True)
  if result is None:
    return make_response("No fraction found", 400)
  return make_response({"fractionList": result}, 200)

def deleteFraction(req):
  fractionId = req.json["fractionId"]
  sqlStmt1 = f"DELETE FROM images WHERE fraction_id='{fractionId}';"
  sqlStmt2 = f"DELETE FROM fraction WHERE fraction_id='{fractionId}';"
  try:
    executeQuery(sqlStmt1)
    executeQuery(sqlStmt2)
    return make_response({"message": "Fraction deleted successfully"}, 200)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({"message": "Failed to delete fraction"}, 400)

def _getCsvPatientId(row):
  for fieldName in fractionSyncPatientIdFields:
    if fieldName in row and row[fieldName].strip():
      return row[fieldName].strip()
  return None

def _getCsvFractionName(row):
  for fieldName in ["fractionName(*)", "fractionName", "fraction_name"]:
    if fieldName in row and row[fieldName].strip():
      return row[fieldName].strip()
  return None

def _normaliseCsvValue(columnName, rawValue):
  if rawValue is None:
    return None

  value = rawValue.strip()
  if value == "":
    return None

  if columnName == "fraction_date":
    return dt.date.fromisoformat(value)

  if columnName in fractionSyncIntegerColumns:
    return int(float(value))

  if columnName in fractionSyncNumericColumns:
    return float(value)

  return value

def _normaliseDbValue(value):
  if isinstance(value, dt.datetime):
    return value.date()
  return value

def _jsonSafeValue(value):
  if isinstance(value, (dt.date, dt.datetime)):
    return value.isoformat()
  return value

def _valuesAreDifferent(dbValue, csvValue):
  dbValue = _normaliseDbValue(dbValue)
  if isinstance(dbValue, float) and isinstance(csvValue, float):
    return abs(dbValue - csvValue) > 1e-9
  return dbValue != csvValue

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

def _readFractionCsv(reader, dynamicFractionFields=None, clearEmptyFields=False):
  csvRecords = {}
  skippedRows = []
  requiredHeaders = ["patientId(*)", "fractionName(*)"]
  dynamicFractionFields = dynamicFractionFields or []

  if not reader.fieldnames:
    raise ValueError("CSV file is empty or missing a header row.")

  missingHeaders = [header for header in requiredHeaders if header not in reader.fieldnames]
  if missingHeaders:
    raise ValueError(f"CSV missing required columns: {', '.join(missingHeaders)}")

  for rowNumber, row in enumerate(reader, start=2):
    if not any(value and value.strip() for value in row.values()):
      continue

    patientId = _getCsvPatientId(row)
    fractionName = _getCsvFractionName(row)

    if not patientId or not fractionName:
      skippedRows.append({
        "rowNumber": rowNumber,
        "reason": "Missing patientId or fractionName"
      })
      continue

    key = (patientId, fractionName)
    if key in csvRecords:
      skippedRows.append({
        "rowNumber": rowNumber,
        "patientId": patientId,
        "fractionName": fractionName,
        "reason": "Duplicate patientId/fractionName in CSV"
      })
      continue

    dbValues = {}
    try:
      dynamicFractionFieldDict = dict(fractionSyncCsvFieldDict)
      for fieldName in dynamicFractionFields:
        dynamicFractionFieldDict[fieldName] = fieldName

      for csvColumn, dbColumn in dynamicFractionFieldDict.items():
        if csvColumn not in row:
          continue
        if row[csvColumn] is None or row[csvColumn].strip() == "":
          if clearEmptyFields:
            dbValues[dbColumn] = None
          continue
        dbValues[dbColumn] = _normaliseCsvValue(dbColumn, row[csvColumn])
    except ValueError as err:
      skippedRows.append({
        "rowNumber": rowNumber,
        "patientId": patientId,
        "fractionName": fractionName,
        "reason": f"Invalid value: {err}"
      })
      continue

    dbValues["fraction_name"] = fractionName
    csvRecords[key] = {
      "patientId": patientId,
      "fractionName": fractionName,
      "values": dbValues
    }

  return csvRecords, skippedRows

def _loadFractionCsv(filePath, dynamicFractionFields=None, clearEmptyFields=False):
  with open(filePath, newline='', encoding='utf-8-sig') as csvFile:
    return _readFractionCsv(
      csv.DictReader(csvFile),
      dynamicFractionFields,
      clearEmptyFields,
    )

def _loadFractionCsvContent(csvContent, dynamicFractionFields=None, clearEmptyFields=False):
  return _readFractionCsv(
    csv.DictReader(io.StringIO(csvContent)),
    dynamicFractionFields,
    clearEmptyFields,
  )

def _fetchExistingFractions(cur, patientIds, trialName=None):
  if not patientIds:
    return {}

  columns = sorted(set(fractionSyncCsvFieldDict.values()))
  query = f"""
    SELECT
      patient.patient_trial_id,
      fraction.fraction_id,
      fraction.extended_data AS fraction_extended_data,
      images.extended_data AS images_extended_data,
      {', '.join([f'fraction.{column}' for column in columns])}
    FROM patient
    JOIN prescription ON patient.id = prescription.patient_id
    JOIN fraction ON prescription.prescription_id = fraction.prescription_id
    LEFT JOIN images ON fraction.fraction_id = images.fraction_id
    WHERE patient.patient_trial_id = ANY(%s)
  """
  params = [patientIds]
  if trialName:
    query += " AND patient.clinical_trial = %s"
    params.append(trialName)

  cur.execute(query, params)
  rows = cur.fetchall()
  return {(row["patient_trial_id"], row["fraction_name"]): row for row in rows}

def _fetchPatientPrescriptions(cur, patientIds, trialName=None):
  if not patientIds:
    return {}

  query = """
    SELECT patient.patient_trial_id, prescription.prescription_id
    FROM patient
    JOIN prescription ON patient.id = prescription.patient_id
    WHERE patient.patient_trial_id = ANY(%s)
  """
  params = [patientIds]
  if trialName:
    query += " AND patient.clinical_trial = %s"
    params.append(trialName)

  cur.execute(query, params)
  return {row["patient_trial_id"]: row["prescription_id"] for row in cur.fetchall()}

def _insertFraction(cur, prescriptionId, values, trialStructure):
  columnValues, jsonbValuesByTable = split_values_by_storage_table(
    values,
    {"fraction": trialStructure},
    "fraction",
    fraction_table_fields=fractionTableItemList,
  )
  columns = [
    column for column in columnValues.keys()
    if column in fractionSyncCsvFieldDict.values()
  ]
  fractionJsonbValues = jsonbValuesByTable.get("fraction", {})
  imageJsonbValues = jsonbValuesByTable.get("images", {})
  if fractionJsonbValues:
    columnValues["extended_data"] = jsonb_insert_value(build_extended_data(fractionJsonbValues))
    columns.append("extended_data")
  placeholders = ', '.join(['%s'] * len(columns))
  query = f"""
    INSERT INTO fraction (prescription_id, {', '.join(columns)})
    VALUES (%s, {placeholders})
    RETURNING fraction_id
  """
  params = [prescriptionId] + [columnValues[column] for column in columns]
  cur.execute(query, params)
  fractionId = cur.fetchone()["fraction_id"]
  if imageJsonbValues:
    cur.execute(
      "INSERT INTO images (fraction_id, extended_data) VALUES (%s, %s)",
      (fractionId, jsonb_insert_value(build_extended_data(imageJsonbValues))),
    )
  else:
    cur.execute("INSERT INTO images (fraction_id) VALUES (%s)", (fractionId,))
  return fractionId

def _updateFraction(cur, fractionId, changedFields, trialStructure):
  columnFields, jsonbValuesByTable = split_values_by_storage_table(
    changedFields,
    {"fraction": trialStructure},
    "fraction",
    fraction_table_fields=fractionTableItemList,
  )
  if columnFields:
    setClause = ', '.join([f"{column} = %s" for column in columnFields.keys()])
    params = list(columnFields.values()) + [fractionId]
    cur.execute(f"UPDATE fraction SET {setClause} WHERE fraction_id = %s", params)
  set_jsonb_fields(cur, "fraction", "fraction_id", fractionId, jsonbValuesByTable.get("fraction", {}))
  imageJsonbFields = jsonbValuesByTable.get("images", {})
  if imageJsonbFields:
    _ensureImageRow(cur, fractionId)
    set_jsonb_fields(cur, "images", "fraction_id", fractionId, imageJsonbFields)

def _ensureImageRow(cur, fractionId):
  cur.execute("SELECT image_id FROM images WHERE fraction_id = %s LIMIT 1", (fractionId,))
  if cur.fetchone():
    return
  cur.execute("INSERT INTO images (fraction_id) VALUES (%s)", (fractionId,))

def _fetchFractionUpdateContext(cur, patientId, fractionName):
  cur.execute(
    """
    SELECT patient.clinical_trial, fraction.fraction_id
    FROM patient
    JOIN prescription ON patient.id = prescription.patient_id
    JOIN fraction ON prescription.prescription_id = fraction.prescription_id
    WHERE patient.patient_trial_id = %s
      AND fraction.fraction_name = %s
    """,
    (patientId, fractionName),
  )
  return cur.fetchone()

def _updateFractionOrImageField(cur, fractionId, trialStructure, key, value):
  if key in trialStructure and is_jsonb_field(
    {"fraction": trialStructure},
    "fraction",
    key,
  ):
    tableName = get_field_table(
      {"fraction": trialStructure},
      "fraction",
      key,
      fraction_table_fields=fractionTableItemList,
    )
    if tableName == "images":
      _ensureImageRow(cur, fractionId)
    set_jsonb_fields(cur, tableName, "fraction_id", fractionId, {key: value})
    return

  if key in fractionTableItemList:
    cur.execute(f"UPDATE fraction SET {key} = %s WHERE fraction_id = %s", (value, fractionId))
  else:
    _ensureImageRow(cur, fractionId)
    cur.execute(f"UPDATE images SET {key} = %s WHERE fraction_id = %s", (value, fractionId))

def _formatCsvOutputValue(value):
  if value is None:
    return ""
  if isinstance(value, (dt.date, dt.datetime)):
    return value.isoformat()
  return value

def exportFractionCsv(req):
  trialName = req.args.get("trialName")
  siteName = req.args.get("siteName")
  patientId = req.args.get("patientId")

  if not trialName:
    return make_response({"message": "trialName is required."}, 400)

  connector = None
  conn = None
  try:
    trialStructure = _getTrialFractionStructure(trialName)
    jsonbFieldsByTable = _getFractionJsonbFieldsByTable(trialStructure)
    jsonbFractionFields = jsonbFieldsByTable.get("fraction", []) + jsonbFieldsByTable.get("images", [])
    connector, conn = _connectToImagingDb()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = """
      SELECT
        patient.patient_trial_id,
        fraction.fraction_number,
        fraction.fraction_name,
        fraction.fraction_date,
        fraction.mvsdd,
        fraction.kvsdd,
        fraction.kv_pixel_size,
        fraction.mv_pixel_size,
        fraction.marker_length,
        fraction.marker_width,
        fraction.marker_type,
        fraction.imaging_kv,
        fraction.imaging_ma,
        fraction.imaging_ms,
        fraction.extended_data AS fraction_extended_data,
        images.extended_data AS images_extended_data
      FROM patient
      JOIN prescription ON patient.id = prescription.patient_id
      JOIN fraction ON prescription.prescription_id = fraction.prescription_id
      LEFT JOIN images ON fraction.fraction_id = images.fraction_id
      WHERE patient.clinical_trial = %s
    """
    params = [trialName]

    if siteName:
      query += " AND patient.test_centre = %s"
      params.append(siteName)

    if patientId:
      query += " AND patient.patient_trial_id = %s"
      params.append(patientId)

    query += " ORDER BY patient.patient_trial_id, fraction.fraction_number, fraction.fraction_name"
    cur.execute(query, params)
    rows = cur.fetchall()

    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')
    headers = [
      "patientId(*)", "fractionNumber(*)", "fractionName(*)", "fractionDate",
      "mvsdd", "kvsdd", "kvPixelSize", "mvPixelSize", "markerLength",
      "markerWidth", "markerType", "imagingKV", "imagingMA", "imagingMS"
    ] + jsonbFractionFields
    writer.writerow(headers)
    for row in rows:
      writer.writerow([
        _formatCsvOutputValue(row["patient_trial_id"]),
        _formatCsvOutputValue(row["fraction_number"]),
        _formatCsvOutputValue(row["fraction_name"]),
        _formatCsvOutputValue(row["fraction_date"]),
        _formatCsvOutputValue(row["mvsdd"]),
        _formatCsvOutputValue(row["kvsdd"]),
        _formatCsvOutputValue(row["kv_pixel_size"]),
        _formatCsvOutputValue(row["mv_pixel_size"]),
        _formatCsvOutputValue(row["marker_length"]),
        _formatCsvOutputValue(row["marker_width"]),
        _formatCsvOutputValue(row["marker_type"]),
        _formatCsvOutputValue(row["imaging_kv"]),
        _formatCsvOutputValue(row["imaging_ma"]),
        _formatCsvOutputValue(row["imaging_ms"]),
        *[
          _formatCsvOutputValue(
            get_stored_field_value(
              row,
              {"fraction": trialStructure},
              "fraction",
              field,
              fraction_table_fields=fractionTableItemList,
            )
          )
          for field in jsonbFractionFields
        ]
      ])

    cur.close()
    conn.close()
    connector.connection = None

    return make_response({
      "fractionCsv": output.getvalue(),
      "rowCount": len(rows),
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
    return make_response({"message": "Failed to export fraction CSV.", "error": str(err)}, 400)

def syncFractionCsv(req):
  payload = req.json
  if not payload or ("filePath" not in payload and "csvContent" not in payload):
    return make_response({"message": "filePath or csvContent is required."}, 400)

  filePath = payload.get("filePath")
  csvContent = payload.get("csvContent")
  fileName = payload.get("fileName")
  trialName = payload.get("trialName")
  dryRun = bool(payload.get("dryRun", False))
  deleteMissing = bool(payload.get("deleteMissing", False))
  clearEmptyFields = bool(payload.get("clearEmptyFields", False))

  if filePath and not os.path.isfile(filePath):
    return make_response({"message": f"CSV file not found: {filePath}"}, 400)

  try:
    trialStructure = _getTrialFractionStructure(trialName)
    dynamicFractionFields = get_trial_fields(
      {"fraction": trialStructure},
      "fraction",
      storage="jsonb",
    )
    if csvContent is not None:
      csvRecords, skippedRows = _loadFractionCsvContent(
        csvContent,
        dynamicFractionFields,
        clearEmptyFields,
      )
    else:
      csvRecords, skippedRows = _loadFractionCsv(
        filePath,
        dynamicFractionFields,
        clearEmptyFields,
      )
    patientIds = sorted({record["patientId"] for record in csvRecords.values()})

    connector, conn = _connectToImagingDb()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    existingFractions = _fetchExistingFractions(cur, patientIds, trialName)
    patientPrescriptions = _fetchPatientPrescriptions(cur, patientIds, trialName)

    inserted = []
    updated = []
    deleted = []
    missingPatients = []
    unchangedCount = 0

    for key, csvRecord in csvRecords.items():
      patientId, fractionName = key
      existingRow = existingFractions.get(key)

      if existingRow is None:
        prescriptionId = patientPrescriptions.get(patientId)
        if prescriptionId is None:
          missingPatients.append(patientId)
          continue

        if not dryRun:
          _insertFraction(cur, prescriptionId, csvRecord["values"], trialStructure)
        inserted.append({
          "patientId": patientId,
          "fractionName": fractionName,
          "fields": sorted(csvRecord["values"].keys())
        })
        continue

      changedFields = {}
      for columnName, csvValue in csvRecord["values"].items():
        if columnName not in existingRow and columnName not in dynamicFractionFields:
          continue
        existingValue = get_stored_field_value(
          existingRow,
          {"fraction": trialStructure},
          "fraction",
          columnName,
          fraction_table_fields=fractionTableItemList,
        )
        if _valuesAreDifferent(existingValue, csvValue):
          changedFields[columnName] = csvValue

      if changedFields:
        if not dryRun:
          _updateFraction(cur, existingRow["fraction_id"], changedFields, trialStructure)
        updated.append({
          "patientId": patientId,
          "fractionName": fractionName,
          "fields": {key: _jsonSafeValue(value) for key, value in changedFields.items()}
        })
      else:
        unchangedCount += 1

    if deleteMissing:
      csvKeys = set(csvRecords.keys())
      for key, existingRow in existingFractions.items():
        if key in csvKeys:
          continue
        if not dryRun:
          cur.execute("DELETE FROM images WHERE fraction_id = %s", (existingRow["fraction_id"],))
          cur.execute("DELETE FROM fraction WHERE fraction_id = %s", (existingRow["fraction_id"],))
        deleted.append({
          "patientId": key[0],
          "fractionName": key[1]
        })

    if dryRun:
      conn.rollback()
    else:
      conn.commit()
    cur.close()
    conn.close()
    connector.connection = None

    return make_response({
      "message": "Fraction CSV sync completed.",
      "dryRun": dryRun,
      "filePath": filePath,
      "fileName": fileName,
      "trialName": trialName,
      "deleteMissing": deleteMissing,
      "clearEmptyFields": clearEmptyFields,
      "totalCsvRows": len(csvRecords) + len(skippedRows),
      "validCsvRows": len(csvRecords),
      "insertedCount": len(inserted),
      "updatedCount": len(updated),
      "deletedCount": len(deleted),
      "unchangedCount": unchangedCount,
      "missingPatients": sorted(set(missingPatients)),
      "skippedRows": skippedRows,
      "inserted": inserted,
      "updated": updated,
      "deleted": deleted
    }, 200)
  except (Exception, pg.DatabaseError) as err:
    print(err, file=sys.stderr)
    try:
      conn.rollback()
      conn.close()
      connector.connection = None
    except:
      pass
    return make_response({"message": "Failed to sync fraction CSV.", "error": str(err)}, 400)

def updateFractionInfo(req):
  payload = req.json
  patientId = payload["patientId"]
  fractionName = payload["fractionName"]

  connector = None
  conn = None
  try:
    connector, conn = _connectToImagingDb()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    context = _fetchFractionUpdateContext(cur, patientId, fractionName)
    if not context:
      cur.close()
      conn.close()
      connector.connection = None
      return make_response({"message": "Failed to update patient info"}, 400)
    trialStructure = _getTrialFractionStructure(context["clinical_trial"])
    for key in payload:
      if key not in ['patientId', 'fractionName']:
        _updateFractionOrImageField(
          cur,
          context["fraction_id"],
          trialStructure,
          key,
          payload[key],
        )
    conn.commit()
    cur.close()
    conn.close()
    connector.connection = None
  except Exception as err:
    print(err, file=sys.stderr)
    try:
      if conn:
        conn.rollback()
        conn.close()
      if connector:
        connector.connection = None
    except:
      pass
    return make_response({"message": "Failed to update patient info"}, 400)
  
  return make_response({"message": "Fraction info updated successfully"}, 200)
  
def updateFractionField(req):
  updatePack = req.json
  if updatePack == None:
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)
  connector = None
  conn = None
  try:
    connector, conn = _connectToImagingDb()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    for update in updatePack:
      patientId = update["patient_trial_id"]
      fractionName = update["fraction_name"]
      context = _fetchFractionUpdateContext(cur, patientId, fractionName)
      if not context:
        continue
      trialStructure = _getTrialFractionStructure(context["clinical_trial"])
      for key in update["updateFields"]:
        _updateFractionOrImageField(
          cur,
          context["fraction_id"],
          trialStructure,
          key,
          update['updateFields'][key],
        )
    conn.commit()
    cur.close()
    conn.close()
    connector.connection = None
  except Exception as err:
    print(err, file=sys.stderr)
    try:
      if conn:
        conn.rollback()
        conn.close()
      if connector:
        connector.connection = None
    except:
      pass
    return make_response({"message": "Failed to update patient info"}, 400)

  return make_response({"message": "Fraction info updated successfully"}, 200)
  
def _getMissingFractionFieldCheck(req):
  try:
    trialName = req.args.get("trialName")
    sqlStmt = f"SELECT patient.*, prescription.*, fraction.*, images.*, fraction.extended_data AS fraction_extended_data, images.extended_data AS images_extended_data FROM patient JOIN prescription ON patient.id = prescription.patient_id JOIN fraction ON prescription.prescription_id=fraction.prescription_id LEFT JOIN images ON fraction.fraction_id=images.fraction_id WHERE clinical_trial='{trialName}'"
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
      missedPack['tumour_site'] = row['tumour_site']
      missedPack['missedFields'] = {}
      for key in requiredFields:
        if key in trialStructure:
          value = get_stored_field_value(
            row,
            {"fraction": trialStructure},
            "fraction",
            key,
            fraction_table_fields=fractionTableItemList,
          )
        else:
          value = row.get(key.lower())
        if value == None or value == "not found" or value == "":
          missedPack['missedFields'][key] = value
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

_FRACTION_PATH_PLACEHOLDER_RE = re.compile(r"\{([^}:]+)(?::[^}]+)?\}")
_CENTRE_PATIENT_NO_PLACEHOLDER_RE = re.compile(r"\{centre_patient_no(?::[^}]+)?\}")

def _normalizeFractionPath(path):
  if not path:
    return "/"
  normalized = path.replace("\\", "/")
  if not normalized.startswith("/"):
    normalized = "/" + normalized
  return normalized

def _pathHasFractionPlaceholder(filePath):
  placeholders = _FRACTION_PATH_PLACEHOLDER_RE.findall(filePath)
  return any(name in ("fraction_name", "fraction_number") for name in placeholders)

def _getCentrePatientNoInt(field):
  centrePatientNo = field.get("centre_patient_no")
  if centrePatientNo is not None and str(centrePatientNo).strip() != "":
    return int(centrePatientNo)
  return 0

def _getCentrePatientNoFormatVariants(centrePatientNoValue):
  variants = [
    str(centrePatientNoValue),
    str(centrePatientNoValue).zfill(2),
    str(centrePatientNoValue).zfill(3),
  ]
  seen = set()
  uniqueVariants = []
  for variant in variants:
    if variant not in seen:
      seen.add(variant)
      uniqueVariants.append(variant)
  return uniqueVariants

def _folderMatchesCentrePatientNo(folderName, centrePatientNoValue):
  if not folderName:
    return False

  normalizedFolderName = folderName.strip()
  upperFolderName = normalizedFolderName.upper()

  if upperFolderName.startswith("PAT"):
    suffix = normalizedFolderName[3:]
    if suffix.isdigit() and int(suffix) == centrePatientNoValue:
      return True

  patientPrefixMatch = re.match(r"^Patient\s*(\d+)$", normalizedFolderName, re.IGNORECASE)
  if patientPrefixMatch and int(patientPrefixMatch.group(1)) == centrePatientNoValue:
    return True

  patPrefixMatch = re.match(r"^Pat(\d+)$", normalizedFolderName, re.IGNORECASE)
  if patPrefixMatch and int(patPrefixMatch.group(1)) == centrePatientNoValue:
    return True

  if normalizedFolderName.isdigit() and int(normalizedFolderName) == centrePatientNoValue:
    return True

  return False

def _dedupeFractionPaths(paths):
  seen = set()
  uniquePaths = []
  for path in paths:
    normalizedPath = _normalizeFractionPath(path)
    if normalizedPath not in seen:
      seen.add(normalizedPath)
      uniquePaths.append(normalizedPath)
  return uniquePaths

def _pathUsesCentrePatientNo(filePath):
  return "{centre_patient_no" in filePath

def _discoverCentrePatientNoPathCandidates(filePath, kwargs, rootPath, centrePatientNoValue, field):
  if not rootPath:
    return []

  centrePatientMatch = _CENTRE_PATIENT_NO_PLACEHOLDER_RE.search(filePath)
  if not centrePatientMatch:
    return []

  prefix = filePath[:centrePatientMatch.start()]
  suffix = filePath[centrePatientMatch.end():]
  prefixPaths = _resolveFractionPathTemplate(prefix, kwargs, rootPath) if prefix else [""]
  discoveredPaths = []

  for prefixPath in prefixPaths:
    normalizedPrefix = _normalizeFractionPath(prefixPath) if prefixPath else ""
    parentRelativePath = os.path.dirname(normalizedPrefix.rstrip("/"))
    parentAbsolutePath = rootPath + parentRelativePath if parentRelativePath else rootPath

    if not os.path.isdir(parentAbsolutePath):
      continue

    for folderName in sorted(os.listdir(parentAbsolutePath)):
      if folderName.startswith("."):
        continue
      if not _folderMatchesCentrePatientNo(folderName, centrePatientNoValue):
        continue

      patientFolderPath = parentRelativePath.rstrip("/") + "/" + folderName
      discoveredPaths.extend(
        _buildFractionPathCandidatesWithKwargs(
          patientFolderPath + suffix,
          kwargs,
          field,
          rootPath,
          expandCentrePatientNo=False,
        )
      )

  return discoveredPaths

def _getFractionPathFormatKwargs(field, trialName):
  centrePatientNoValue = _getCentrePatientNoInt(field)

  fractionNumber = field.get("fraction_number")
  if fractionNumber is not None and str(fractionNumber).strip() != "":
    fractionNumberValue = int(fractionNumber)
  else:
    fractionNumberValue = 0

  kwargs = {
    "clinical_trial": trialName,
    "tumour_site": field.get("tumour_site", ""),
    "test_centre": field.get("test_centre", ""),
    "centre_patient_no": str(centrePatientNoValue).zfill(2),
    "fraction_name": field.get("fraction_name", ""),
    "fraction_number": fractionNumberValue,
    "patient_trial_id": field.get("patient_trial_id", ""),
  }

  for key, value in field.items():
    if value is None or key in kwargs:
      continue
    if isinstance(value, (str, int, float)):
      kwargs[key] = value

  return kwargs

def _formatFractionPathTemplate(filePath, kwargs):
  try:
    return filePath.format(**kwargs)
  except ValueError:
    kwargs = dict(kwargs)
    kwargs["centre_patient_no"] = int(kwargs["centre_patient_no"])
    return filePath.format(**kwargs)

def _resolveFractionPathTemplate(filePath, kwargs, rootPath=None):
  match = _FRACTION_PATH_PLACEHOLDER_RE.search(filePath)
  if not match:
    return [_normalizeFractionPath(filePath)]

  placeholderName = match.group(1)
  before = filePath[:match.start()]
  after = filePath[match.end():]

  if placeholderName in kwargs:
    resolvedValue = str(kwargs[placeholderName])
    return _resolveFractionPathTemplate(before + resolvedValue + after, kwargs, rootPath)

  prefixCandidates = _resolveFractionPathTemplate(before, kwargs, rootPath) if before else [""]
  expandedPaths = []
  for prefix in prefixCandidates:
    normalizedPrefix = _normalizeFractionPath(prefix) if prefix else ""
    if rootPath and normalizedPrefix:
      absolutePrefix = rootPath + normalizedPrefix
      if not os.path.isdir(absolutePrefix):
        continue
      childNames = sorted(
        entry for entry in os.listdir(absolutePrefix)
        if not entry.startswith(".")
      )
    elif rootPath:
      childNames = sorted(
        entry for entry in os.listdir(rootPath)
        if not entry.startswith(".")
      )
      normalizedPrefix = ""
    else:
      continue

    for childName in childNames:
      childPrefix = normalizedPrefix.rstrip("/") + "/" + childName
      expandedPaths.extend(
        _resolveFractionPathTemplate(childPrefix + after, kwargs, rootPath)
      )

  return expandedPaths

def _buildLegacyFractionPathCandidates(formatedPath, field):
  fractionName = field.get("fraction_name", "")
  fractionNumber = field.get("fraction_number")
  pathWithFraction = formatedPath + f"Fx{fractionNumber}"
  candidates = [
    pathWithFraction + "/" + fractionName,
    formatedPath + fractionName,
    pathWithFraction,
    formatedPath,
  ]
  seen = set()
  uniqueCandidates = []
  for candidate in candidates:
    normalizedCandidate = _normalizeFractionPath(candidate)
    if normalizedCandidate not in seen:
      seen.add(normalizedCandidate)
      uniqueCandidates.append(normalizedCandidate)
  return uniqueCandidates

def _buildFractionPathCandidatesWithKwargs(
  filePath,
  kwargs,
  field,
  rootPath=None,
  expandCentrePatientNo=True,
):
  if not _pathHasFractionPlaceholder(filePath):
    formatedPath = _formatFractionPathTemplate(filePath, kwargs)
    return _buildLegacyFractionPathCandidates(formatedPath, field)

  placeholders = _FRACTION_PATH_PLACEHOLDER_RE.findall(filePath)
  unknownPlaceholders = [name for name in placeholders if name not in kwargs]

  if not unknownPlaceholders:
    try:
      return [_normalizeFractionPath(_formatFractionPathTemplate(filePath, kwargs))]
    except KeyError:
      unknownPlaceholders = placeholders

  if unknownPlaceholders:
    return _resolveFractionPathTemplate(filePath, kwargs, rootPath)

  return [_normalizeFractionPath(_formatFractionPathTemplate(filePath, kwargs))]

def _buildFractionPathCandidates(filePath, field, trialName, rootPath=None):
  kwargs = _getFractionPathFormatKwargs(field, trialName)
  centrePatientNoValue = _getCentrePatientNoInt(field)

  if not _pathUsesCentrePatientNo(filePath):
    return _buildFractionPathCandidatesWithKwargs(
      filePath,
      kwargs,
      field,
      rootPath,
      expandCentrePatientNo=False,
    )

  candidates = []
  for centrePatientVariant in _getCentrePatientNoFormatVariants(centrePatientNoValue):
    variantKwargs = dict(kwargs)
    variantKwargs["centre_patient_no"] = centrePatientVariant
    candidates.extend(
      _buildFractionPathCandidatesWithKwargs(
        filePath,
        variantKwargs,
        field,
        rootPath,
        expandCentrePatientNo=False,
      )
    )

  candidates.extend(
    _discoverCentrePatientNoPathCandidates(
      filePath,
      kwargs,
      rootPath,
      centrePatientNoValue,
      field,
    )
  )

  return _dedupeFractionPaths(candidates)

def _resolveFractionFieldPath(rootPath, filePath, field, trialName, key):
  for candidatePath in _buildFractionPathCandidates(filePath, field, trialName, rootPath):
    if not os.path.exists(rootPath + candidatePath):
      continue
    resolvedPath = _checkImageFolderItems(rootPath, candidatePath, key)
    if resolvedPath:
      return resolvedPath
  return None

def _tryToFindImageFolder(rootPath, mainPath, case):
  # For many of the trials, the name of the KV folder could be different, so we need to check all the possible names. 
  # If the folder name is neither KIM-KV nor kV, we can't do anything, but return the path to fraction folder level. 

  possibleKVFolderNames = ['KIM-KV', 'KIM-kV', 'kV', 'KV', 'kv']
  possibleMVFolderNames = ['KIM-MV', 'MV', 'mv']
  possibleSurfaceFolderNames = ['surface', 'Surface', 'surface_imaging', 'Surface_Imaging', 'Surface_imaging', 'Surface Imaging', 'surface_images', 'Surface Images', 'surface_images', 'Surface_Images']
  possibleCBCTFolderNames = ['CBCT', 'cbct', 'CBCT_Images', 'CBCT Images', 'cbct_images', 'CBCT_images']
  possibleMRIFolderNames = ['MRI', 'mri_images', 'MRI_images', 'MRI_intra', 'MRI_Intra', 'mri_intra']
  possiblePETFolderNames = ['PET', 'pet_images', 'PET_images', 'PET_Intra', 'PET_intra', 'pet_intra']

  if case == "KV":
    for folderName in possibleKVFolderNames:
      if os.path.exists(rootPath + mainPath + '/' + folderName):
        return mainPath + '/' + folderName
  elif case == "MV":
    for folderName in possibleMVFolderNames:
      if os.path.exists(rootPath + mainPath + '/' + folderName):
        return mainPath + '/' + folderName
      
  elif case == "cbct":
    for folderName in possibleCBCTFolderNames:
      if os.path.exists(rootPath + mainPath + '/' + folderName):
        return mainPath + '/' + folderName
  elif case == "mri":
    for folderName in possibleMRIFolderNames:
      if os.path.exists(rootPath + mainPath + '/' + folderName):
        return mainPath + '/' + folderName
  elif case == "pet":
    for folderName in possiblePETFolderNames:
      if os.path.exists(rootPath + mainPath + '/' + folderName):
        return mainPath + '/' + folderName
  else:
    for folderName in possibleSurfaceFolderNames:
      if os.path.exists(rootPath + mainPath + '/' + folderName):
        return mainPath + '/' + folderName
      
  return mainPath

def _checkImageFolderItems(rootPath, pathWithFractionName, key):
  mri_pattern = r'mri_intra'
  cbct_pattern = r'cbct'
  kv_pattern = r'kv'
  mv_pattern = r'mv'
  surface_pattern = r'surface'
  pet_pattern = r'pet'

  # If the key is KV or MV, we need to check if the folder name is different from the expected one.
  if re.search(kv_pattern, key):
    # If the key is KV, we need to add the KV folder name to the path.
    pathWithFractionName = _tryToFindImageFolder(rootPath, pathWithFractionName, 'KV')
    # The function will return the path with KV folder name if it exists, otherwise, it will return the path with fraction name.
    # The below step is to check if the path contains KV, if it does, we will add it to the updateFields.
    if re.search(kv_pattern, pathWithFractionName, re.IGNORECASE):
      print(pathWithFractionName)
      return pathWithFractionName
  # The same logic as above, but for MV.
  elif re.search(mv_pattern, key):
    pathWithFractionName = _tryToFindImageFolder(rootPath, pathWithFractionName, 'MV')
    # The function will return the path with MV folder name if it exists, otherwise, it will return the path with fraction name.
    # The below step is to check if the path contains MV, if it does, we will add it to the updateFields.
    if re.search(mv_pattern, pathWithFractionName, re.IGNORECASE):
      return pathWithFractionName
  # The same logic as above, but for surface.
  elif re.search(surface_pattern, key):
    pathWithFractionName = _tryToFindImageFolder(rootPath, pathWithFractionName, 'surface')
    if re.search(surface_pattern, pathWithFractionName, re.IGNORECASE):
      return pathWithFractionName
  # The same logic as above, but for pet.
  elif re.search(pet_pattern, key):
    pathWithFractionName = _tryToFindImageFolder(rootPath, pathWithFractionName, 'pet')
    if re.search(pet_pattern, pathWithFractionName, re.IGNORECASE):
      return pathWithFractionName
  # The same logic as above, but for cbct.
  elif re.search(cbct_pattern, key):
    pathWithFractionName = _tryToFindImageFolder(rootPath, pathWithFractionName, 'cbct')
    if re.search(cbct_pattern, pathWithFractionName, re.IGNORECASE):
      return pathWithFractionName
  # The same logic as above, but for mri.
  elif re.search(mri_pattern, key):
    pathWithFractionName = _tryToFindImageFolder(rootPath, pathWithFractionName, 'mri')
    if re.search(mri_pattern, pathWithFractionName, re.IGNORECASE):
      return pathWithFractionName
  else:
    return pathWithFractionName
  
  return 0
  
def getUpdateFractionField(req):
  missingFields = _getMissingFractionFieldCheck(req)
  if missingFields == None:
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)
  try:
    rootDrivePath = req.args.get("rootDrivePath")
    rootPath = config.DATA_FILESYSTEM_ROOT_PREFIX + rootDrivePath
    if rootDrivePath and os.path.exists(rootPath):
      rootPath = rootPath
    else:
      rootPath = config.DATA_FILESYSTEM_ROOT
    trialName = req.args.get("trialName")
    sqlStmt2 = f"SELECT trial_structure FROM trials WHERE trial_name='{trialName}'"
    fetchedRows2 = executeQuery(sqlStmt2, authDB=True)
    trialStructure = fetchedRows2[0][0]['fraction']
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
          filePath = trialStructure[key].get('path', '')
          if not filePath:
            continue
          resolvedPath = _resolveFractionFieldPath(rootPath, filePath, field, trialName, key)
          if resolvedPath:
            patientPack['updateFields'][key] = resolvedPath
      if patientPack['updateFields']:
        returnPack.append(patientPack)
    return make_response(returnPack)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({'message': 'An error occurred while fetching missing fields.'}, 400)

def _addFractionToDB(rawData, patientId):
  formatedPack = {fractionTableNameDict[key]: rawData[key] for key in rawData if key in fractionTableNameDict and rawData[key]}
  fractionName = formatedPack["fraction_name"]
  
  # check if fraction name exists
  sqlStmt = f"SELECT get_fraction_id_for_patient ('{patientId}', '{fractionName}')"
  result = executeQuery(sqlStmt)
  if result:
    return False, {"message": f"Fraction name already exists, patient_trial_id: {patientId}, fraction_name: {fractionName}"}
  
  formatedPack = {fractionTableNameDict[key]: rawData[key] for key in rawData if key in fractionTableNameDict and rawData[key]}
  try:
    sqlStmt = "INSERT INTO fraction (prescription_id, "
    sqlStmt += ', '.join([key for key in formatedPack])
    sqlStmt += f") VALUES ((SELECT prescription_id FROM prescription WHERE patient_id=(SELECT id FROM patient WHERE patient_trial_id='{patientId}')),"
    sqlStmt += ', '.join([f"'{formatedPack[key]}'" for key in formatedPack])
    sqlStmt += ");"
    executeQuery(sqlStmt)
    fractionId = executeQuery(f"SELECT get_fraction_id_for_patient ('{patientId}', '{fractionName}');")[0][0]
    sqlStmt = f"INSERT INTO images (fraction_id) VALUES ('{fractionId}')"
    executeQuery(sqlStmt)    
    return True, {"message": "Fraction added successfully"}
  except Exception as err:
    print(err, file=sys.stderr)
    return False, {"message": f"Failed to add fraction, patient_trial_id: {patientId}, fraction_name: {fractionName}"}

def addNewFraction(req):
  payload = req.json
  patientId = payload["patientId"]
  status, rsp = _addFractionToDB(payload, patientId)
  if status:
    return make_response(rsp, 200)
  else:
    return make_response(rsp, 400)


def addBulkFraction(req):
  rawData = req.json
  csvRawData = csv.reader(io.StringIO(rawData['fractionList']))
  csvHeader = next(csvRawData)
  fractionInfoList = []
  row = next(csvRawData)
  while row:
    fractionInfoList.append({csvHeader[i]: row[i] for i in range(len(row))})
    try:
      row = next(csvRawData)
    except StopIteration:
      break
  resultList = []
  failedList = []
  for fractionInfo in fractionInfoList:
    patientId = fractionInfo['patientId(*)']

    status, rsp = _addFractionToDB(fractionInfo, patientId)
    if not status:
      failedList.append(patientId)
    else:
      resultList.append(patientId)
    
  if failedList and resultList:
    return make_response({"message": "Some fractions failed to add", "failedList": failedList, "successList": resultList}, 200)
  elif resultList:
    return make_response({"message": "Bulk fraction added successfully", "successList": resultList}, 200)
  else:
    return make_response({"message": "Failed to add any fraction", "failedList": failedList}, 400)

