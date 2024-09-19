from flask import make_response
from .util import executeQuery
import sys
import config
import os
import re
import csv
import io

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
      missedPack['tumour_site'] = row['tumour_site']
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
          filePath = trialStructure[key]['path']
          formatedPath = filePath.format(clinical_trial=trialName, tumour_site=field['tumour_site'], test_centre=field['test_centre'], centre_patient_no=str(field['centre_patient_no']).zfill(2))
          pathWithFraction = formatedPath + f'Fx{field["fraction_number"]}'
          pathWithFractionName = pathWithFraction + '/' + field['fraction_name']
          if os.path.exists(rootPath + formatedPath + field['fraction_name']):
            pathWithFractionName = formatedPath + field['fraction_name']

          # The logic here is to check if the path with fraction name exists, if not, check if the path with fraction exists.
          if os.path.exists(rootPath + pathWithFractionName):
            pathWithFractionName = _checkImageFolderItems(rootPath, pathWithFractionName, key)
            if pathWithFractionName:
              patientPack['updateFields'][key] = pathWithFractionName
          # If the path with fraction name does not exist, we will check if the path with fraction exists.
          elif os.path.exists(rootPath + pathWithFraction):
            pathWithFraction = _checkImageFolderItems(rootPath, pathWithFraction, key)
            if pathWithFraction:
              patientPack['updateFields'][key] = pathWithFraction
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
