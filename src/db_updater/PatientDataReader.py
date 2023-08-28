from numpy import tri
import pandas as pd
import os
import math
import json
import re
import time
from typing import Dict, List
from datetime import date, datetime
from DVHParser import DVHParser
import psycopg2 as pg

class PatientDataReader:
    def __init__(self, clinicalDataPath: str, patientDataPath:str) -> None:
        self.data_path_root = clinicalDataPath
        self.patients_df = None
        self.fraction_df = None
        self.data_locations:Dict = None
        self.fractionDetailsFromFileSystem = []
        self.patientData:Dict = self._loadPatientData(patientDataPath)
        self._conn = None

    def _loadPatientData(self, patientDataPath:str) -> Dict:
        with open(patientDataPath, "r") as patientDataFile:
            patientData = json.load(patientDataFile)
        return patientData

    def readPatientDetailsFromSPARKDocs(self, trogFileName):
        """ Deprecated function """
        excelFilePath = os.path.join(self.data_path_root, "SPARK", 
                            "1 SPARK_Documentation", "TROG docsrc", trogFileName)

        participantData = pd.read_excel(excelFilePath, sheet_name="Participant")
        # print(participantData.head())

        parsedPatientData = []
        rowCounter = -1
        for participantRow in participantData.iterrows():
            rowCounter += 1
            if rowCounter < 2:
                continue

            if len(participantRow[1]) > 5:
                patientId = str(participantRow[1][2]).replace(" ", "") # Study No
                if len(patientId) == 0 or patientId != "nan":
                    patientAge = int(participantRow[1][5]) if not math.isnan(participantRow[1][5]) else 0
                    parsedPatientData.append({
                        "clinical_trial": "SPARK", # since this spreadsheet deals with only SPARK data
                        "test_centre": str(participantRow[1][1]),  # Site
                        "patient_trial_id": patientId,  
                        "age": patientAge,
                        "gender": 'M',  # since this is a prostate tumour trial
                        "tumour_site": "prostate",
                        "number_of_markers": 3  # hardcoded fro prostate tumour patients
                    })
        self.patients_df = pd.DataFrame(parsedPatientData)
        # print(self.patients_df)
        self.patients_df.to_csv("participant_data_from_trog.csv")

        kimData = pd.read_excel(excelFilePath, sheet_name="KIM")
        fractionData = []
        rowCounter = -1
        for kimDataRow in kimData.iterrows():
            rowCounter += 1
            if rowCounter < 1:
                continue
            
            if (rowCounter - 2)%5 == 0:
                if not pd.isna(kimDataRow[1][1]):
                    
                    for r in range(rowCounter - 2, rowCounter + 3):
                        if not math.isnan(kimData.iloc[r][3].year):
                            fractionDateStr = str(kimData.iloc[r][3].day) + '-' \
                                            + str(kimData.iloc[r][3].month) + '-' \
                                            + str(kimData.iloc[r][3].year)
                            kimResult = True if kimData.iloc[r][4] == "Yes" else False
                            numGatingEvents = str(int(kimData.iloc[r][6])) if not math.isnan(kimData.iloc[r][6]) else -1
                            fractionData.append({
                                "fraction_number": int(kimData.iloc[r][2]),
                                "test_centre": kimDataRow[1][0],
                                "patient_trial_id": str(int(kimDataRow[1][1])),
                                "fraction_date": fractionDateStr,
                                "kim_result": kimResult,
                                "num_gating_events": numGatingEvents
                            })
        self.fraction_df = pd.DataFrame(fractionData)
        # print(self.fraction_df.to_string()) 
        self.fraction_df.to_csv("participant_data_from_trog.csv", index=False)

    def readFractionAndImageDataLocations(self, locations_file):
        with open(locations_file) as data_paths_file:
            self.data_locations = json.loads(data_paths_file.read())

    def readFractionDetails(self, fractionDetailsFilePath:str):
        with open(fractionDetailsFilePath) as fractionDetailsFile:
            fractionDetails = json.loads(fractionDetailsFile.read())
        if "fractions" in fractionDetails:
            self.fractionDetailsFromFileSystem = fractionDetails["fractions"] 

    def mapTROGPatientIdToPatientSequence(self):
        """ Deprecated function """
        print("mapping patient sequence to TROG ID")
        patientSequenceToIdVotingMap = {}
        for fractionDetailsFromFS in self.fractionDetailsFromFileSystem:
            for index, row in self.fraction_df.iterrows():
                
                if row["test_centre"] == fractionDetailsFromFS["test_centre"]:
                    fractionDateFromFS = date.fromisoformat(fractionDetailsFromFS["fraction_date"])
                    fractionDateFromTROG = datetime.strptime(row["fraction_date"], "%d-%m-%Y").date()
                    if fractionDateFromTROG == fractionDateFromFS \
                            and row["fraction_number"] == fractionDetailsFromFS["fraction_number"]:
                        patientDetails = {
                            "patient_trial_id": row["patient_trial_id"],
                            "counter ": 0
                        }
                        patientSequence = str(fractionDetailsFromFS["patient_sequence"])
                        if patientSequence in patientSequenceToIdVotingMap:
                            if row["patient_trial_id"] in patientSequenceToIdVotingMap[patientSequence]:
                                patientSequenceToIdVotingMap[patientSequence][row["patient_trial_id"]] += 1
                            else:
                                patientSequenceToIdVotingMap[patientSequence][row["patient_trial_id"]] = 1
                        else:
                            patientSequenceToIdVotingMap[patientSequence] = {row["patient_trial_id"]:1}

                        print("matched", row["patient_trial_id"], 
                                f"({row['fraction_number']}) with",
                                fractionDetailsFromFS["patient_sequence"],
                                f"({fractionDetailsFromFS['fraction_number']})")
        print(patientSequenceToIdVotingMap)
        # calculate maximum votes for any matched patient id and let that be the winner
        patientSequenceMap = {}
        for patientSequence in patientSequenceToIdVotingMap:
            if len(patientSequenceToIdVotingMap[patientSequence]) < 2:
                patientSequenceMap[patientSequence] = next(iter(patientSequenceToIdVotingMap[patientSequence].keys()))
            else:
                highestVoted = max(patientSequenceToIdVotingMap[patientSequence].values())
                matches = [k for k,v in patientSequenceToIdVotingMap[patientSequence].items() if v == highestVoted]
                print(matches)
                assert len(matches) < 2, "more than one TROG patient id matches patient sequence"
                patientSequenceMap[patientSequence] = matches[0]

        print(patientSequenceMap)
        return patientSequenceMap

    def getTestCentres(self, trialName="SPARK") -> List:
        centreNames = []
        clinicalTrials:List = self.patientData["clinical_data"]
        for trial in clinicalTrials:
            if trial["clinical_trial"] == trialName:
                for centre in trial["centres"]:
                    centreNames.append(centre["centre"])
        return centreNames

    def getPatients(self, testCentreName:str, trialName:str="SPARK") -> List:
        clinicalTrials:List = self.patientData["clinical_data"]
        for trial in clinicalTrials:
            if trial["clinical_trial"] == trialName:
                for centre in trial["centres"]:
                    if centre["centre"] == testCentreName:
                        return centre["patients"]
        return []

    def getFileLocationsDataForPatient(self, testCentreName:str, 
                                            patientTrialId:str,
                                            trialName:str = "SPARK" ) -> Dict:
        clinicalTrials:List = self.patientData["clinical_data"]
        for trial in clinicalTrials:
            if trial["clinical_trial"] == trialName:
                for centre in trial["centres"]:
                    if centre["centre"] == testCentreName:
                        for patient in centre["patients"]:
                            if patient["patient_trial_id"] == patientTrialId:
                                return patient
        return None  # if the patient is not found

    def getFractionsFromPatientDetails(self, patientDetails: Dict,
                                            fractionNumber: int,) -> List[Dict]:
        fractions = []
        for fraction in patientDetails["fractions"]:
            if fraction["fraction_number"] == fractionNumber:
                fractions.append(fraction)
        return fractions

    def generateDataInsersionScripts(self) -> str:
        dbInsersionScript:str = ""
        assert self.patientData is not None and len(self.patientData) > 0, \
            "The patient data is not loaded, please run the Filesystem Scrubber"

        print("Creating SQL script:")
        for trialData in self.patientData["clinical_data"]:
            trial = trialData["clinical_trial"]
            print(f"Trial: {trial}")
            for testCentre in self.getTestCentres(trialName=trial):
                print(f"  Centre: {testCentre}")
                patients = self.getPatients(testCentreName=testCentre, trialName=trial)
                for patient in patients:
                    print(f"    Patient: {patient['patient_trial_id']}", end=" ", flush=True)
                    dbInsersionScript += self.generatePatientPopulationScript(patient, trial, testCentre)
                    dbInsersionScript += self.generatePrescriptionPopulationScript(patient)
                    dbInsersionScript += self.generateDosePopulationScript(patient["RT_DVH_original_path"], 
                                                                            level="prescription", 
                                                                            patientTrialId=patient["patient_trial_id"], 
                                                                            isTracked=False)
                    dbInsersionScript += self.generateDosePopulationScript(patient["RT_DVH_summed_no_track_path"], 
                                                                            level="prescription", 
                                                                            patientTrialId=patient["patient_trial_id"], 
                                                                            isTracked=False)
                    dbInsersionScript += self.generateDosePopulationScript(patient["RT_DVH_summed_track_path"], 
                                                                            level="prescription", 
                                                                            patientTrialId=patient["patient_trial_id"], 
                                                                            isTracked=True)
                    for fraction in patient["fractions"]:
                        print(f"{fraction['fraction_name']}", end=" ", flush=True)
                        dbInsersionScript += self.generateFractionPopulationScript(fraction, patient["patient_trial_id"])
                        dbInsersionScript += self.generateImagesPopulationScript(fraction, patient["patient_trial_id"])
                        dbInsersionScript += self.generateDosePopulationScript(fraction["DVH_track_path"], 
                                                                                level="fraction", 
                                                                                patientTrialId=patient["patient_trial_id"],
                                                                                isTracked=True,
                                                                                fractionName=fraction["fraction_name"])
                        dbInsersionScript += self.generateDosePopulationScript(fraction["DVH_no_track_path"], 
                                                                                level="fraction", 
                                                                                patientTrialId=patient["patient_trial_id"], 
                                                                                isTracked=False,
                                                                                fractionName=fraction["fraction_name"])
                    print(" ")

        return dbInsersionScript

    def generatePatientPopulationScript(self, patientData:Dict, 
                                            trial:str, testCentre:str) -> str:
        insertionScript = "INSERT INTO patient (age, gender," + \
                        "tumour_site, patient_trial_id, clinical_trial," + \
                        "test_centre, centre_patient_no, number_of_markers) " \
                        + "VALUES ( " \
                        + str(patientData["age"]) + ", " \
                        + "'" + patientData["gender"] + "', " \
                        + "'" + patientData["tumour_site"] + "', " \
                        + "'" + patientData["patient_trial_id"] + "', " \
                        + "'" + trial + "', " \
                        + "'" + testCentre + "', " \
                        + str(patientData["centre_patient_no"]) + ", " \
                        + patientData["number_of_markers"] + ");\n"

        return insertionScript

    def generatePrescriptionPopulationScript(self, patientData:Dict) -> str:
        mriPath = patientData["RT_MRI_path"] if "RT_MRI_path" in \
                                                    patientData else "N/A"
        centroidPath = patientData["centroid_path"] if "centroid_path" in \
                                                    patientData else "N/A"

        insertionScript = "INSERT INTO prescription (patient_id," + \
                        " LINAC_type, RT_plan_path, RT_CT_path," + \
                        " RT_structure_path, RT_dose_path, RT_DVH_original_path," \
                        + " RT_MRI_path, centroid_path) " \
                        + "SELECT get_patient_id('" \
                        + patientData["patient_trial_id"] + "')," \
                        + "'" + patientData["LINAC_type"] + "', " \
                        + "'" + patientData["RT_plan_path"] + "'," \
                        + "'" + patientData["RT_CT_path"] + "'," \
                        + "'" + patientData["RT_structure_path"] + "'," \
                        + "'" + patientData["RT_dose_path"] + "'," \
                        + "'" + patientData["RT_DVH_original_path"] + "'," \
                        + "'" + mriPath + "'," \
                        + "'" + centroidPath + "';\n"
        return insertionScript

    def generateFractionPopulationScript(self, fractionData:Dict, patientTrialId:str) -> str:
        mvsddValue = fractionData["mvsdd"] if "mvsdd" in fractionData else 0.0
        kvsddValue = fractionData["kvsdd"] if "kvsdd" in fractionData else 0.0

        insertionScript = "INSERT INTO fraction (prescription_id, " \
                        + "fraction_date, fraction_number, " \
                        + "num_gating_events, mvsdd, kvsdd, fraction_name) " \
                        + "SELECT get_prescription_id_for_patient('" \
                        +  patientTrialId + "'), " \
                        + "'" + fractionData["fraction_date"] + "', " \
                        + str(fractionData["fraction_number"]) + ", " \
                        + str(fractionData["num_gating_events"]) + ", " \
                        + str(mvsddValue) + ", " \
                        + str(kvsddValue) + ", " \
                        + "'" + fractionData["fraction_name"] + "';\n"
        return insertionScript

    def generateImagesPopulationScript(self, fractionData:Dict, patientTrialId:str) -> str:
        metricsPath = fractionData["metrics"]["path"] \
                        if "metrics" in fractionData else "N/A"
        metricsPath = metricsPath.replace("'", "''")

        traingulationPath = fractionData["triangulated_pos"]["path"] \
                        if "triangulated_pos" in fractionData else "N/A"
        traingulationPath = traingulationPath.replace("'", "''")
        
        kimLogsPath = fractionData["kim_logs"] \
                        if "kim_logs" in fractionData else "N/A"
        rpmFilesPath = fractionData["respiratory_files_path"] \
                        if "rpm_files_path" in fractionData else "N/A"

        insertionScript = "INSERT INTO images (fraction_id, " \
            + "kim_logs_path, KV_images_path, MV_images_path, " \
            + "metrics_path, triangulation_path, " \
            + "trajectory_logs_path, DVH_track_path, DVH_no_track_path, " \
            + "DICOM_track_plan_path, DICOM_no_track_plan_path, respiratory_files_path) " \
            + "SELECT get_fraction_id_for_patient ('" \
            + patientTrialId + "', " \
            + "'" + fractionData["fraction_name"] + "'), " \
            + "'" + kimLogsPath + "', " \
            + "'" + fractionData["KV_images"]["path"] + "', " \
            + "'" + fractionData["MV_images"]["path"] + "', " \
            + "'" + metricsPath + "', " \
            + "'" + traingulationPath + "', " \
            + "'" + fractionData["trajectory_logs"] + "', " \
            + "'" + fractionData["DVH_track_path"] + "', " \
            + "'" + fractionData["DVH_no_track_path"] + "', " \
            + "'" + fractionData["DICOM_track_plan_path"] + "', " \
            + "'" + fractionData["DICOM_no_track_plan_path"] + "', " \
            + "'" + rpmFilesPath + "';\n"
        
        return insertionScript

    def generateDosePopulationScript(self, dvhFilePath:str, level:str, 
                                            patientTrialId:str,
                                            isTracked:bool, 
                                            fractionName:int=0):
        # generic error in case this function is unable to construct the script
        # insertionScript = f"-- Failed to parse {dvhFilePath}\n"

        if not os.path.isfile(self.data_path_root + "/" + dvhFilePath):
            return f"-- DVH path not valid: {dvhFilePath}\n"

        parser = DVHParser(self.data_path_root + "/" + dvhFilePath)
        tryAgain = True
        trialAttempts = 3
        while tryAgain:
            try:
                dvh = parser.parse()
                tryAgain = False  # parsing successful in this attempt
            except FileNotFoundError as err:
                print("ERROR: DVH file not found:", err)
                tryAgain = False
                return f"-- File not found {dvhFilePath}\n"
            except OSError as err:
                print("ERROR: Could not read the file " \
                        + dvhFilePath + ": " + err.strerror)
                if trialAttempts > 1:
                    time.sleep(3)  # try again after a few seconds
                    trialAttempts -= 1
                    tryAgain = True
                else:
                    tryAgain = False
                    return "-- OS Error while parsing DVH file " + dvhFilePath \
                            + ": " + err.strerror + "\n"

        if dvh is None:
            return f"-- DVH file could not be parsed: {dvhFilePath}\n"
        
        # print(f"=============== {dvhFilePath} ==================")
        if level == "fraction":
            levelSpecificComponent = "SELECT get_fraction_id_for_patient ('" \
                                + patientTrialId + "', " \
                                + "'" + fractionName + "'), " \
                                + "'" + level + "', "
        elif level == "prescription":
            levelSpecificComponent = "SELECT get_prescription_id_for_patient('" \
                                +  patientTrialId + "'), " \
                                + "'" + level + "', "
        else:
            print("Only prescription and fraction levels are supported for DVH")
            return f"-- Only prescription and fraction levels are supported for DVH but the level supplied was {level}\n"

        insertionScript = ""
        for dvhStruct in dvh["structures"]:
            structureVolume = "0.0"
            doseCoverage = "0.0"
            minDose = "0.0"
            maxDose = "0.0"
            meanDose = "0.0"
            modalDose = "0.0"
            medianDose = "0.0"
            stdDev = "0.0"
            # print(f"---------- {dvhStruct['Structure']} --------------")
            for doseKey in dvhStruct.keys():
                # if doseKey != "dose values":
                #     print(doseKey, ":", dvhStruct[doseKey])
                if re.match("Volume [\S]*", doseKey):
                    structureVolume = dvhStruct[doseKey]
                if re.match("Dose Cover.[\S]*", doseKey):
                    doseCoverage = dvhStruct[doseKey]
                if re.match("Min Dose [\S]*", doseKey):
                    minDose = dvhStruct[doseKey]
                if re.match("Max Dose [\S]*", doseKey):
                    maxDose = dvhStruct[doseKey]
                if re.match("Mean Dose [\S]*", doseKey):
                    meanDose = dvhStruct[doseKey]
                if re.match("Modal Dose [\S]*", doseKey):
                    modalDose = dvhStruct[doseKey]
                if re.match("Median Dose [\S]*", doseKey):
                    medianDose = dvhStruct[doseKey]
                if re.match("STD [\S]*", doseKey):
                    stdDev = dvhStruct[doseKey]

            d95Value = parser.computeDoseForPercentOfStructureVolume(dvhStruct["Structure"], 95)
            # print("d95 (in Gy):", d95Value)
            d100Value = parser.computeDoseForPercentOfStructureVolume(dvhStruct["Structure"], 100)
            # print("d100 (in Gy):", d100Value)

            approvalStatus = "true" if dvhStruct["Approval Status"] == "Approved" else "false"

            insertionScript += "INSERT INTO dose (foreign_id, dose_level, " \
                            + "is_tracked, structure, plan, approved, " \
                            + "structure_volume, dose_coverage, min_dose, " \
                            + "max_dose, mean_dose, modal_dose, median_dose, " \
                            + "std_dev, d95, d100) " \
                            + levelSpecificComponent \
                            + "'" + str(isTracked) + "', " \
                            + "'" + dvhStruct["Structure"] + "', " \
                            + "'" + dvhStruct["Plan"] + "', " \
                            + approvalStatus + ", " \
                            + structureVolume + ", " \
                            + doseCoverage + ", " \
                            + str(minDose) + ", " \
                            + str(maxDose) + ", " \
                            + str(meanDose) + ", " \
                            + str(modalDose) + ", " \
                            + str(medianDose) + ", " \
                            + str(stdDev)  + ", " \
                            + str(d95Value) + ", " \
                            + str(d100Value) + ";\n"

        return insertionScript

    def initDBConnection(self, connectionParams:Dict) -> bool:
        """This function initialises the database connection and is required to
        be called only once. 
        
        It returns a boolean value indicating the result
        of the connection status.

        The connection parameters should be in the form of a dictionary 
        with the following structure:
        
        {
            "database": <name of the database instance>,
            "user": <user with ownership rights for the DB>,
            "password": <authenticaton password>,
            "host": <hostname/IP of the systemhosting the DB server>
        }
        """
        conn = self._getDBConnection(connectionParams, reconnect=True)
        return True if conn is not None else False

    def _getDBConnection(self, connectionParams:Dict={}, reconnect=False):
        """ A safer mechanism to get the database conneciton object instead of 
            directly accessing the _conn instance of this class. 
            The first time, the DB connection parameters should be passed to 
            this function as a dictionary. All the subsequent call can call 
            without any parameters to get the cached connection object. 

            If it is not possible to connect to the DB, this function would
            return a None type object.
        """
        if self._conn is None or reconnect:
            if "user" not in connectionParams:
                print("Database connection does not exist, please supply " \
                    "connection parameters for creating a new connection")
                return None
            
            try:
                self._conn = pg.connect(database=connectionParams["database"], 
                                            user=connectionParams["user"], 
                                            password=connectionParams["password"],
                                            host=connectionParams["host"])

                cur = self._conn.cursor()
                print("Connected to PostgreSQL version:", end=" ")
                cur.execute("SELECT version()")
                db_version = cur.fetchone()
                print(db_version)
                cur.close()
            except (Exception, pg.DatabaseError) as error:
                print(error)
                self._conn = None
        return self._conn

    def doesFractionExistinDatabase(self, fractionData:Dict, patientTrialId:str) -> bool:
        conn = self._getDBConnection()
        fractionFound = False
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM patient, prescription, fraction WHERE " \
                        + " fraction.prescription_id = prescription.prescription_id " \
                        + " AND prescription.patient_id = patient.id " \
                        + " AND patient.patient_trial_id = '" + patientTrialId + "' " \
                        + " AND fraction_number=" \
                        + str(fractionData["fraction_number"]) \
                        + " AND fraction_date='" \
                        + fractionData["fraction_date"] \
                        + "' AND fraction_name='" \
                        + fractionData["fraction_name"] \
                        + "';"
            cursor.execute(query)
            fractionRecords = cursor.fetchall()
            if len(fractionRecords) > 0:
                fractionFound = True
            
        except (Exception, pg.Error) as ex:
            print("exception caught while trying to find fractions in DB:", ex)
        finally:
            cursor.close()
        
        return fractionFound

    def insertDataIntoServer(self, trial, centre, patientTrialId="", patientNo=0):
        pass

    def generateDBPopulationScripts(self, scriptPath:str):
        """ Deprecated function """
        patientsInsertionScript:str = ""
        for patientIndex, row in self.patients_df.iterrows():
            patientDetails = self.getFileLocationsDataForPatient(
                                    testCentreName=row["test_centre"],
                                    patientTrialId=row["patient_trial_id"])
            if patientDetails is None:
                break
                      
            insertionScript = "INSERT INTO patient (age, gender," + \
                            "tumour_site, patient_trial_id, clinical_trial," + \
                            "test_centre, centre_patient_no, number_of_markers) " \
                            + "VALUES ( " \
                            + str(row["age"]) + ", " \
                            + "'" + row["gender"] + "', " \
                            + "'" + row["tumour_site"] + "', " \
                            + "'" + row["patient_trial_id"] + "', " \
                            + "'" + row["clinical_trial"] + "', " \
                            + "'" + row["test_centre"] + "', " \
                            + str(patientDetails["centre_patient_no"]) + ", " \
                            + "'" + str(row["number_of_markers"]) + "');\n"

            # print('Pat', end=' ')
            mriPath = patientDetails["RT_MRI_path"] if "RT_MRI_path" in \
                                                        patientDetails else ''

            insertionScript += "INSERT INTO prescription (patient_id, " + \
                            "LINAC_type, RT_plan_path, RT_CT_path," + \
                            "RT_structure_path, RT_dose_path, RT_MRI_path, " + \
                            "RT_DVH_original_path) " \
                            + "SELECT get_patient_id('" + row["patient_trial_id"] + "')," \
                            + "'TBD', " \
                            + "'" + patientDetails["RT_plan_path"] + "'," \
                            + "'" + patientDetails["RT_CT_path"] + "'," \
                            + "'" + patientDetails["RT_structure_path"] + "'," \
                            + "'" + patientDetails["RT_dose_path"] + "'," \
                            + "'" + mriPath + "'," \
                            + "'" + patientDetails["RT_DVH_original_path"] + "';\n" 
            # print('Pres', end=' ')

            currentPatientFractions = self.fraction_df[
                self.fraction_df["patient_trial_id"] == row["patient_trial_id"]]

            fractionCounter = 0
            for fractionIndex, fractionRow in currentPatientFractions.iterrows():
                fractionCounter += 1
                insertionScript += "INSERT INTO fraction (prescription_id, " \
                                + "fraction_date, fraction_number, " \
                                + "num_gating_events, kim_result) " \
                                + "SELECT get_prescription_id_for_patient('" \
                                +  row["patient_trial_id"] + "'), " \
                                + "'" + fractionRow["fraction_date"] + "', " \
                                + str(fractionCounter) + ", " \
                                + str(fractionRow["num_gating_events"]) + ", " \
                                + str(fractionRow["kim_result"]) + ";\n"
                # print('Fra', end=' ')
                fractionDetails = self.getFractionsFromPatientDetails(
                                                patientDetails, fractionCounter)
                for fractionDetail in fractionDetails:
                    metricsPath = fractionDetail["metrics"]["path"] \
                                    if "metrics" in fractionDetail else ''
                    metricsPath = metricsPath.replace("'", "''")

                    traingulationPath = fractionDetail["triangulated_pos"]["path"] \
                                    if "triangulated_pos" in fractionDetail else ''
                    traingulationPath = traingulationPath.replace("'", "''")
                    
                    kimLogsPath = fractionDetail["kim_logs"] if "kim_logs" in fractionDetail else ""

                    insertionScript += "INSERT INTO images (fraction_id, " \
                        + "kim_logs_path, KV_images_path, MV_images_path, " \
                        + "metrics_path, triangulation_path, " \
                        + "trajectory_logs_path, DVH_track_path, " \
                        + "DVH_no_track_path) " \
                        + "SELECT get_fraction_id_for_patient ('" \
                        + row["patient_trial_id"] + "', " \
                        + str(fractionCounter) + "), " \
                        + "'" + kimLogsPath + "', " \
                        + "'" + fractionDetail["KV_images"]["path"] + "', " \
                        + "'" + fractionDetail["MV_images"]["path"] + "', " \
                        + "'" + metricsPath + "', " \
                        + "'" + traingulationPath + "', " \
                        + "'" + fractionDetail["trajectory_logs"] + "', " \
                        + "'" + fractionDetail["DVH_track_path"] + "', " \
                        + "'" + fractionDetail["DVH_no_track_path"] + "', " \
                        + "'" + fractionDetail["DICOM_track_plan_path"] + "', " \
                        + "'" + fractionDetail["DICOM_no_track_plan_path"] + "';\n"

                    print('Img', end=' ')
            patientsInsertionScript += insertionScript
        with open(scriptPath, 'w') as fp:
            fp.write(patientsInsertionScript)
        

def generateDBInsersionScripts():
    with open("data/local_settings.json") as localSettingsFile:
        localsettings = json.load(localSettingsFile)
    fsRootpath = localsettings["root_filesystem_path"]    

    reader = PatientDataReader(fsRootpath, "scrubbed_patient_data.json")
    #reader = PatientDataReader("X:/2RESEARCH/1_ClinicalData", "scrubbed_patient_data.json")
    # reader.readPatientDetailsFromSPARKDocs("TROG 15.01_SPARK_Site_Tracker_2018 updated.xlsx")
    # reader.readFractionAndImageDataLocations("data/clinical_data_locations.json")
    # reader.generateDBPopulationScripts("dbInserts.sql")
    with open("dbInserts.sql", "w") as sqlFile:
        sqlFile.write(reader.generateDataInsersionScripts())
    

def mapTROGDataToFileSystemData():
    """ Deprecated function """
    reader = PatientDataReader("X:/2RESEARCH/1_ClinicalData")
    reader.readPatientDetailsFromSPARKDocs("TROG 15.01_SPARK_Site_Tracker_2018 updated.xlsx")
    reader.readFractionDetails("scrubbed_fraction_data.json")
    reader.mapTROGPatientIdToPatientSequence()

def insertDataToDBDirectly():
    with open("data/local_settings.json") as localSettingsFile:
        localsettings = json.load(localSettingsFile)
    fsRootpath = localsettings["root_filesystem_path"]    

    reader = PatientDataReader(fsRootpath, "scrubbed_patient_data.json")
    # the following lines are for testing and would be replaced
    if reader.initDBConnection({"database": "testdb", "user": "indrajit", "password": "indrajit", "host":"localhost"}):
        print(reader.doesFractionExistinDatabase({"fraction_number":1, "fraction_date":"2016-02-24", "fraction_name": "Fx01"}, "1501001"))

if __name__ == "__main__":
    generateDBInsersionScripts()
    # insertDataToDBDirectly()
    # mapTROGDataToFileSystemData()
    
