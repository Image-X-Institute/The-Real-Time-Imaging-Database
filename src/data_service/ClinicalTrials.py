from lib2to3.pgen2 import token
from werkzeug.datastructures import ImmutableMultiDict
import config
from dbconnector import DBConnector
import psycopg2 as pg
from typing import Dict, List, Tuple
import json
import datetime as dt
from AccessManager import accessManagerInstance, AccessType
from sys import stderr


class ClinicalTrials:
    def __init__(self) -> None:
        self.connector = DBConnector(config.DB_NAME, 
                                config.DB_USER, 
                                config.DB_PASSWORD,
                                config.DB_HOST)
        self.connector.connect()
        self.apiMapping = ClinicalTrials.getAPIFieldMapping()

    @staticmethod
    def getAPIFieldMapping():
        with open("resources/api_mapping.json", "r") as apiMappingFile:
            apiMapping = json.load(apiMappingFile)
        return apiMapping

    def getAllPatients(self) -> Dict[str, List]:
        patients_data = {"patients": []}
        try:
            cur = self.connector.getConnection().cursor()
            cur.execute("SELECT * FROM patient")
            if config.APP_DEBUG_MODE:
                print("number of patients returned:", cur.rowcount)            
            patients = cur.fetchall()
            cur.close()

            for patient in patients:
                data = {
                    "age" : patient[1],
                    # V2 Schema # "height": patient[2] if patient[2] is not None else 0,
                    # V2 Schema # "weight": patient[3] if patient[3] is not None else 0,
                    "gender": patient[2] if patient[2] is not None else "unknown",
                    "clinical_diagnosis": patient[3],
                    "tumour_site": patient[4],
                    "patient_trial_id": patient[5],
                    "clinical_trial": patient[6],
                    "test_centre": patient[7],
                    "num_markers": patient[8]
                    }
                patients_data["patients"].append(data)

        except(Exception, pg.DatabaseError) as error:
            print(error, sfile=stderr)

        return patients_data

    def _getAllowedDBRelations(self, 
                                dbRelations:List[Dict], 
                                sessionToken:str, 
                                accessType:AccessType) -> List[Dict]:
        acl = accessManagerInstance.getACLForToken(sessionToken, accessType)
        for relation in dbRelations:
            if "table" in relation and relation["table"] == "patient":
                relation["table"] = "(SELECT * FROM patient WHERE "
                for siteCounter in range(len(acl[0])):
                    if siteCounter == 0:
                        relation["table"] += "("
                    else:
                        relation["table"] += " OR "
                    relation["table"] += f" test_centre = \'{acl[0][siteCounter]}\' "
                    if siteCounter == len(acl[0]) - 1:
                        relation["table"] += ") "

                if len(acl[0]) > 0 and len(acl[1]) > 0:
                    relation["table"] += " AND "
                
                for trialCounter in range(len(acl[1])):
                    if trialCounter == 0:
                        relation["table"] += "("
                    else:
                        relation["table"] += " OR "
                    relation["table"] += f" clinical_trial = \'{acl[1][trialCounter]}\' "
                    if trialCounter == len(acl[1]) - 1:
                        relation["table"] += ") "

                relation["table"] += ") AS patient"
        return dbRelations

    def getEndpointData(self, endpoint:str, 
                            requestParams:Dict, 
                            requestHeaders:Dict) -> Dict[str, List]:
        if config.APP_DEBUG_MODE:
            print(f"Request Args: {requestParams}")
        
        if endpoint not in self.apiMapping:
            return {"error": "invalid endpoint"}
        objectFields = self.apiMapping[endpoint]["object_fields"]
        paramsOfInterest = self.apiMapping[endpoint]["query_params"]
        dbRelations = self.apiMapping[endpoint]["db_relations"]

        if config.VALIDATE_TOKEN:
            if "Token" in requestHeaders:
                sessionToken = requestHeaders["Token"]
            dbRelations = self._getAllowedDBRelations(dbRelations, 
                                                        sessionToken, 
                                                        AccessType.READ)
        endpointData = {endpoint: []}

        strQuery = "SELECT "
        firstfield = True
        for fieldMapping in objectFields:
            if firstfield:
                firstfield = False
            else:
                strQuery += ", "
            strQuery += fieldMapping["field"]["table"] + "." \
                        + fieldMapping["field"]["column"] + " as " \
                        + fieldMapping["property"]

        strQuery += " FROM " + dbRelations[0]["table"]

        if len(dbRelations) > 1:
            for tableCounter in range(1, len(dbRelations)):
                strQuery += ", "
                strQuery += dbRelations[tableCounter]["table"]
            
            strQuery += " WHERE "
            firstJoinCondition = True
            for tableCounter in range(1, len(dbRelations)):
                if not firstJoinCondition:
                    strQuery += " AND "
                else:
                    firstJoinCondition = False
                
                currentTable = dbRelations[tableCounter]  #["table"]
                firstMultiRelationCondition = True
                for joinedwith in currentTable["joined_with"]:
                    if not firstMultiRelationCondition:
                        strQuery += " AND "
                    else:
                        firstMultiRelationCondition = False
                    
                    strQuery += currentTable["table"] + "." + joinedwith["joined_using"] \
                                + " = " + joinedwith["table"] + "." \
                                + joinedwith["column"]

        firstParam = True
        for param in paramsOfInterest:
            if param in requestParams:
                if len(dbRelations) == 1 and firstParam:
                    strQuery += " WHERE "
                else:
                    strQuery += " AND "

                if firstParam:
                    firstParam = False

                strQuery += paramsOfInterest[param]["table"] + "." \
                            + paramsOfInterest[param]["column"] + " = " \
                            + "'" + requestParams[param] + "'"
        strQuery += ";\n"

        if config.APP_DEBUG_MODE:
            print("Executing Query:", strQuery)

        queriedData = {endpoint: []}
        try:
            cur = self.connector.getConnection().cursor()
            cur.execute(strQuery)
            if config.APP_DEBUG_MODE:
                print("number of rows returned:", cur.rowcount)
            rows = cur.fetchall()
            cur.close()

            for rowCounter in range(len(rows)):
                data = {}
                for columnCounter in range(len(objectFields)):
                    fieldValue = rows[rowCounter][columnCounter]
                    if objectFields[columnCounter]["type"] == "date" and fieldValue:
                        fieldValue = fieldValue.isoformat()
                    if fieldValue:
                        data[objectFields[columnCounter]["property"]] = fieldValue

                queriedData[endpoint].append(data)

        except(Exception, pg.DatabaseError) as error:
            print(error, file=stderr)

        # if config.APP_DEBUG_MODE:
        #     print(queriedData) 

        return queriedData

    def _validateAddResourceParams(self, params:Dict, reference:Dict) -> Tuple[bool, str]:
        for tableName in reference.keys():
            if tableName not in params:
                return False, f"Missing top level field {tableName} in submitted fields"
            
            for field in reference[tableName].keys():
                if reference[tableName][field]["required"]: 
                    if field not in params[tableName].keys():
                        return False, f"Missing {tableName}.{field['name']}"
        return True, "Valid"

    def _insertRows(self, params:Dict, reference:Dict) -> Tuple[bool, str]:
        patientUUID = ''
        for tableName in reference.keys():
            if tableName == "prescription":
                params["prescription"]["patient_id"] = patientUUID
                reference["prescription"]["patient_id"] = {"type": "str"}
            insertStmt = f"INSERT INTO {tableName} ("
            insertValues = " VALUES ("
            counter = -1
            for fieldName in params[tableName]:
                counter += 1
                seperator = '' if counter == 0 else ','
                encapsulator = "\'" \
                    if reference[tableName][fieldName]["type"] == "str" else ""
                insertStmt += f"{seperator} {fieldName}"
                insertValues += f"{seperator} " \
                            + f"{encapsulator}{params[tableName][fieldName]}{encapsulator}"
            insertValues += ")"
            insertStmt += f") {insertValues}"
            if config.APP_DEBUG_MODE:
                print(insertStmt)
            
            try:
                cur = self.connector.getConnection().cursor()
                cur.execute(insertStmt)
                if config.APP_DEBUG_MODE:
                    print("Cursor Description after insert:", cur.description)
                self.connector.getConnection().commit()
                cur.close()
            except(Exception, pg.DatabaseError) as error:
                print("Exception while trying insert:", error, file=stderr)
                return False, str(error)

            if tableName == 'patient':
                cur = self.connector.getConnection().cursor()
                cur.execute(f"SELECT id from patient WHERE patient_trial_id=\'{params['patient']['patient_trial_id']}\'")
                result = cur.fetchone()
                patientUUID = result[0]
                cur.close()

        return True, "Insert successful"

    def addPatient(self, patientDetails:Dict) -> Tuple[bool, str]:
        # The cient code calling this method should provide the field contents 
        # of the patient and prescription tables in the form of a JSON string, 
        # which would be loaded into a Python object here and inserted into the 
        # database to create a new instance of patient and prescription.
        with open("resources/add_resource_fields_map.json", 'r') as resourceFieldsMapFile:
            resourceFieldsMapping = json.load(resourceFieldsMapFile)
        requiredFields = resourceFieldsMapping["resources"]["patient"]
        result = self._validateAddResourceParams(patientDetails, requiredFields)
        if not result[0]:
            return result
        self._insertRows(patientDetails, requiredFields)
        return True, f"Added patient {patientDetails['patient']['patient_trial_id']}"

    def insertFractionIntoDB(self, fractionDetails:Dict)  -> Tuple[bool, str]:
        insertStmt = "INSERT INTO fraction (prescription_id, " \
                                + "fraction_date, fraction_number, " \
                                + "fraction_name) " \
                                + "SELECT get_prescription_id_for_patient('" \
                                +  fractionDetails["patient_trial_id"] + "'), " \
                                + "'" + fractionDetails["date"] + "', " \
                                + str(fractionDetails["number"]) + ", " \
                                + "'" + fractionDetails["name"] + "' " \
                                + "RETURNING fraction_id"
        if config.APP_DEBUG_MODE:
            print(insertStmt)
        
        try:
            cur = self.connector.getConnection().cursor()
            cur.execute(insertStmt)
            fractionUUID = cur.fetchone()[0]
            if config.APP_DEBUG_MODE:
                print("Cursor Description after insert:", cur.description, fractionUUID)
            self.connector.getConnection().commit()
            cur.close()
        except(Exception, pg.DatabaseError) as error:
            print("Exception while trying insert:", error, file=stderr)
            return False, str(error)

        insertStmt = "INSERT INTO images (fraction_id) " \
                    + "VALUES ('" \
                    + fractionUUID + "')"
        try:
            cur = self.connector.getConnection().cursor()
            cur.execute(insertStmt)
            if config.APP_DEBUG_MODE:
                print("Cursor Description after insert:", cur.description)
            self.connector.getConnection().commit()
            cur.close()
        except(Exception, pg.DatabaseError) as error:
            print("Exception while trying insert:", error, file=stderr)
            return False, str(error)
                    
        return True, f"Fraction {fractionDetails['name']} successfully inserted"

    def addFraction(self, fractionDetails:Dict) -> Tuple[bool, str]:
        # with open("resources/add_resource_fields_map.json", 'r') as resourceFieldsMapFile:
        #     resourceFieldsMapping = json.load(resourceFieldsMapFile)
        # requiredFields = resourceFieldsMapping["resources"]["fraction"]
        # result = self._validateAddResourceParams(fractionDetails, requiredFields)
        # if not result[0]:
        #     return result
        # self._insertRows(fractionDetails, requiredFields)
        return self.insertFractionIntoDB(fractionDetails)

    def getFractionLevelDoseValues(self, requestParams) -> Dict[str, List]:
        doseData = {"dose": []}

        strQueryFractionLevel = "SELECT test_centre, centre_patient_no, "\
                                + " patient_trial_id, fraction_number, " \
                                + " fraction_name, dose_level, is_tracked, " \
                                + " structure, approved, structure_volume, " \
                                + " dose_coverage, min_dose, max_dose, " \
                                + " mean_dose, modal_dose, median_dose, " \
                                + " std_dev " \
                                + " FROM patient, prescription, fraction, " \
                                + " dose " \
                                + " WHERE patient.id = prescription.patient_id " \
                                + " AND dose_level = 'fraction' " \
                                + " AND dose.foreign_id = fraction.fraction_id " \
                                + " AND prescription.prescription_id = fraction.prescription_id;"
        strQueryPrescriptionLevel = "SELECT test_centre, centre_patient_no, patient_trial_id, dose_level, is_tracked, structure, approved, structure_volume, dose_coverage, min_dose, max_dose, mean_dose, modal_dose, median_dose, std_dev FROM patient, prescription, dose WHERE patient.id = prescription.patient_id AND dose_level = 'prescription' AND dose.foreign_id = prescription.prescription_id;"

    def getPatients(self, requestParams) -> Dict[str, List]:
        patientsData = {"patients": []}
        
        strQuery = "SELECT "

        objectFields = self.apiMapping["patients"]["object_fields"]
        paramsOfInterest = self.apiMapping["patients"]["query_params"]

        firstfield = True
        for fieldMapping in objectFields:
            if firstfield:
                firstfield = False
            else:
                strQuery += ", "
            strQuery += fieldMapping["field"]["table"] + "." \
                        + fieldMapping["field"]["column"] + " as " \
                        + fieldMapping["property"]
        
        strQuery += " FROM patient WHERE patient.id IS NOT NULL "

        for param in paramsOfInterest:
            if param in requestParams:
                strQuery += " AND " + paramsOfInterest[param]["table"] + "." \
                            + paramsOfInterest[param]["column"] + " = " \
                            + "'" + requestParams[param] + "'"
        strQuery += ";\n"

        if config.APP_DEBUG_MODE:
            print("Executing Query:", strQuery)

        try:
            cur = self.connector.getConnection().cursor()
            cur.execute(strQuery)
            if config.APP_DEBUG_MODE:
                print("number of rows returned:", cur.rowcount)
            rows = cur.fetchall()
            cur.close()

            for rowCounter in range(len(rows)):
                data = {}
                print(rows[rowCounter])
                for columnCounter in range(len(objectFields)):
                    fieldValue = rows[rowCounter][columnCounter]
                    if objectFields[columnCounter]["type"] == "date":
                        fieldValue = fieldValue.isoformat()
                    data[objectFields[columnCounter]["property"]] = fieldValue

                patientsData["patients"].append(data)
        except(Exception, pg.DatabaseError) as error:
            print(error)

        if config.APP_DEBUG_MODE:
            print(patientsData)
        return patientsData

    def getFractionIdAndDate(self, patientTrialId:str, fractionNumber:int) -> str:
        strQuery = "SELECT fraction_id, fraction_date FROM fraction, patient, prescription " \
                    + "WHERE patient.patient_trial_id = '" + patientTrialId + "' " \
                    + "AND prescription.patient_id = patient.id " \
                    + "AND fraction.prescription_id = prescription.prescription_id " \
                    + "AND fraction.fraction_number = " + str(fractionNumber) + ";"
        if config.APP_DEBUG_MODE:
            print("Executing Query:", strQuery)

        try:
            cur = self.connector.getConnection().cursor()
            cur.execute(strQuery)
            if config.APP_DEBUG_MODE:
                print("number of rows returned:", cur.rowcount)
            rows = cur.fetchall()
            cur.close()

            if len(rows) == 0:
                return None
            return rows
        except(Exception, pg.DatabaseError) as error:
            print(error)

    def updateFractionName(self, fractionId, fractionName:str) -> Tuple[bool, str]:
        strQuery = "UPDATE fraction SET fraction_name = '" + fractionName + "' " \
                    + "WHERE fraction_id = '" + fractionId + "';"
        if config.APP_DEBUG_MODE:
            print("Executing Query:", strQuery)

        try:
            cur = self.connector.getConnection().cursor()
            cur.execute(strQuery)
            self.connector.getConnection().commit()
            cur.close()
            return True, f"Updated fraction name to {fractionName}"
        except(Exception, pg.DatabaseError) as error:
            print(error)
            return False, str(error)


    def getFractions(self, requestParams) -> Dict:
        """ Deprecated """
        objectFields = [
            {
                "property" : "patient_trial_id", 
                "field" : {
                    "table": "patient", 
                    "column": "patient_trial_id"
                },
                "type": "str"
            },
            {
                "property" : "test_centre",
                "field" : {
                    "table": "patient", 
                    "column": "test_centre"
                },
                "type": "str"
            },
            {
                "property" : "patient_no", 
                "field" : {
                    "table": "patient", 
                    "column": "centre_patient_no"
                },
                "type": "int"
            },
            {
                "property" : "fraction_no", 
                "field" : {
                    "table": "fraction", 
                    "column": "fraction_number"
                },
                "type": "str"
            },
            {
                "property" : "date", 
                "field" : {
                    "table": "fraction", 
                    "column": "fraction_date"
                },
                "type": "date"
            },
            {
                "property" : "gating_events", 
                "field" : {
                    "table": "fraction", 
                    "column": "num_gating_events"
                },
                "type": "int"
            },
            {
                "property" : "kim_logs", 
                "field" : {
                    "table": "images", 
                    "column": "kim_logs_path"
                },
                "type": "str"
            },
            {
                "property" : "kv_images", 
                "field" : {
                    "table": "images", 
                    "column": "KV_images_path"
                },
                "type": "str"
            },
            {
                "property" : "mv_images", 
                "field" : {
                    "table": "images", 
                    "column": "MV_images_path"
                },
                "type": "str"
            },
            {
                "property" : "metrics", 
                "field" : {
                    "table": "images", 
                    "column": "metrics_path"
                },
                "type": "str"
            },
            {
                "property" : "triangulation",
                "field" : {
                    "table": "images", 
                    "column": "triangulation_path"
                },
                "type": "str"
            },
            {
                "property" : "trajectory_logs",
                "field" : {
                    "table": "images", 
                    "column": "trajectory_logs_path"
                },
                "type": "str"
            }
        ]
        paramsOfInterest = {"centre": ("patient", "test_centre"), 
                            "patient": ("patient", "centre_patient_no"), 
                            "fraction": ("fraction", "fraction_number")}
        tablesToBeQueried = {
            "patient": None,
            "prescription": {"patient" : ("patient_id", "id")},
            "fraction": {"prescription" : ("prescription_id", "prescription_id")},
            "images": {"fraction" : ("fraction_id", "fraction_id")}
        }

        fractionsData = {"fractions": []}
        
        strQuery = "SELECT "

        firstfield = True
        for fieldMapping in objectFields:
            if firstfield:
                firstfield = False
            else:
                strQuery += ", "
            strQuery += fieldMapping["field"]["table"] + "." \
                        + fieldMapping["field"]["column"] + " as " \
                        + fieldMapping["property"]
        
        strQuery += " FROM patient, prescription, "\
                    "fraction, images "\
                    "WHERE prescription.patient_id = patient.id " \
                    "AND fraction.prescription_id = prescription.prescription_id " \
                    "AND fraction.fraction_id = images.fraction_id "

        for param in paramsOfInterest:
            if param in requestParams:
                strQuery += " AND " + paramsOfInterest[param][0] + "." \
                            + paramsOfInterest[param][1] + " = " \
                            + "'" + requestParams[param] + "'"
        strQuery += ";\n"

        if config.APP_DEBUG_MODE:
            print("Executing Query:", strQuery)

        try:
            cur = self.connector.getConnection().cursor()
            cur.execute(strQuery)
            print("number of rows returned:", cur.rowcount)
            rows = cur.fetchall()
            cur.close()

            for rowCounter in range(len(rows)):
                data = {}
                print(rows[rowCounter])
                for columnCounter in range(len(objectFields)):
                    fieldValue = rows[rowCounter][columnCounter]
                    if objectFields[columnCounter]["type"] == "date":
                        fieldValue = fieldValue.isoformat()
                    data[objectFields[columnCounter]["property"]] = fieldValue

                fractionsData["fractions"].append(data)
        except(Exception, pg.DatabaseError) as error:
            print(error)

        if config.APP_DEBUG_MODE:
            print(fractionsData)
        return fractionsData