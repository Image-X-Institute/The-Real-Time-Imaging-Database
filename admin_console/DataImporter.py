from genericpath import isdir
from typing import List, Tuple, Dict, Callable
import json
import os
import argparse
import config
from DatabaseAdapter import DatabaseAdapter
import sys
import shutil as sh
import re


class DataImporter:
    def __init__(self) -> None:
        self.metadata:Dict = None
        self.currentContextId:str = None
        self.fileInfo:Dict = None
        self.dbAdapter = DatabaseAdapter()
        self._initialiseStateVariables()

    def _initialiseStateVariables(self):
        self.dataIsValid = False
        self.conflictFree = True
        self.contentCopied = False

    def _initialiseFileInfo(self):
        uploadContextPath = config.UPLOAD_FOLDER + '/' + self.currentContextId
        metatdataPath = uploadContextPath + '/' + config.UPLOAD_METADATA_FILENAME
        with open(metatdataPath, 'r') as metadataFile:
            metadata = json.load(metadataFile)
        self.fileInfo = metadata["uploaded_files"][0]

    def _persistMetadata(self):
        uploadContextPath = config.UPLOAD_FOLDER + '/' + self.currentContextId
        metatdataPath = uploadContextPath + '/' + config.UPLOAD_METADATA_FILENAME
        with open(metatdataPath, 'w') as metadataFile:
            json.dump(self.metadata, metadataFile, indent=4)

    def setUploadContext(self, contextId:str):
        uploadContextPath = config.UPLOAD_FOLDER + '/' + contextId
        if not os.path.isdir(uploadContextPath):
            raise ValueError("No upload context matching the context ID found")
        if not os.path.exists(uploadContextPath + '/' + config.UPLOAD_METADATA_FILENAME):
            raise ValueError("Context ID does not seem to contain a valid upload")
        self.currentContextId = contextId
        self._initialiseStateVariables()
        self._initialiseFileInfo()

    def getUploadFileInfo(self) -> Dict:
        return self.fileInfo
    
    def verifyUploadPacket(self) -> Tuple[bool, str]:
        uploadContextPath = config.UPLOAD_FOLDER + '/' + self.currentContextId
        metatdataPath = uploadContextPath + '/' + config.UPLOAD_METADATA_FILENAME

        with open(metatdataPath, 'r') as metadataFile:
            self.metadata = json.load(metadataFile)

        if self.currentContextId != self.metadata["upload_id"]:
            message = "Upload metadata context does not match upload context"
            return False, message

        if self.metadata["clinical_trial"] not in self.dbAdapter.getClinicalTrialNames():
            message = "Clinical trail for uploaded data not registered"
            return False, message

        if self.metadata["test_centre"] not in self.dbAdapter.getSiteNames():
            message = "Treatment for uploaded data not registered"
            return False, message

        # verify patient trial ID
        # if self.metadata["upload_type"] == "files":
        for UploadDetails in self.metadata["uploaded_files"]:
            # if level is fraction, check if the fraction exists
            for filePath in UploadDetails["Files"]:
                if not os.path.exists(config.UPLOAD_FOLDER + '/' + filePath):
                    message = f"file {filePath} not found in {self.currentContextId} packet"
                    return False, message

        self.dataIsValid = True
        return self.dataIsValid, f"upload packet {self.currentContextId} verified"

    def checkForConflicts(self) -> Tuple[bool, Dict[str, str]]:
        self.ignoreConflicts()
        return True, {"message": "Conflict checking not implemented"}

    def ignoreConflicts(self):
        self.conflictFree = True

    def copyFilesIntoStorage(self, copyProgressCallback:Callable[[str], None]=None) -> Tuple[bool, str]:
        if not self.metadata or not self.dataIsValid:
            return False, "Please set an upload context and validate it before importing"

        if not self.conflictFree:
            return False, "There might be conflicts between existing and new files"
        
        if self.metadata["upload_type"] == "files":
            for UploadDetails in self.metadata["uploaded_files"]:
                for filePath in UploadDetails["Files"]:
                    srcPath = config.UPLOAD_FOLDER + '/' + filePath
                    destPath = config.DATA_FILESYSTEM_ROOT + '/' \
                                    + filePath[len(self.currentContextId):]
                    os.makedirs(os.path.dirname(destPath), exist_ok=True)
                    sh.copy2(srcPath, destPath)
                    if copyProgressCallback:
                        copyProgressCallback(filePath)
        self.contentCopied = True
        return self.contentCopied, "Copying successful"

    def insertMetadataIntoDatabase(self, dbProgressCallback:Callable[[str], None]=None) -> Tuple[bool, str]:
        if not self.metadata or not self.dataIsValid:
            return False, "Please set an upload context and validate it before importing"

        if not self.conflictFree:
            return False, "There might be conflicts between existing and new files"

        if not self.contentCopied and self.metadata["upload_type"] == "files":
            return False, "Please ensure that the uploaded files are copied first before inserting in DB"

        try:
            with open("filetype_db_mapping.json", 'r') as filetypeMappingFile:
                filetypeMapping = json.load(filetypeMappingFile)
        except FileNotFoundError as err:
            return False, "The filetype mapping JSON cannot be loaded"
        
        for UploadDetails in self.metadata["uploaded_files"]:
            if UploadDetails["file_type"] in filetypeMapping["mapping"].keys():
                paths = []
                multiValues = filetypeMapping["mapping"][UploadDetails["file_type"]]["multivalues"]
                granularity = filetypeMapping["mapping"][UploadDetails["file_type"]]["granularity"]
                if multiValues:
                    seperator = filetypeMapping["mapping"][UploadDetails["file_type"]]["delimiter"]
                for filePath in UploadDetails["Files"]:
                    parentPath, sep, fileName = filePath.rpartition('/')
                    if granularity == "folder":
                        if parentPath not in paths:
                            paths.append(parentPath)
                    else:
                        paths.append(filePath)
                    if not multiValues:
                        break
                fieldContent = ""
                if multiValues and len(paths) > 1:
                    for path in paths:
                        if fieldContent != "":
                            fieldContent += seperator
                        fieldContent += path[len(self.currentContextId):]
                else:
                    fieldContent += paths[0][len(self.currentContextId):]
                tableName = filetypeMapping["mapping"][UploadDetails["file_type"]]["table"]
                fieldName = filetypeMapping["mapping"][UploadDetails["file_type"]]["field"]
                insertStmt = f"UPDATE {tableName} SET {fieldName} = \'{fieldContent}\' "
                if tableName == "prescription":
                    insertStmt += "FROM patient " \
                                "WHERE patient.id=prescription.patient_id " \
                                + f"AND patient.patient_trial_id=\'{self.metadata['patient_trial_id']}\' " \
                                + f"AND patient.clinical_trial=\'{self.metadata['clinical_trial']}\' " \
                                + f"AND patient.test_centre=\'{self.metadata['test_centre']}\'"
                elif tableName == "images":
                    insertStmt += "FROM patient, prescription, fraction " \
                                + "WHERE patient.id=prescription.patient_id " \
                                + "AND prescription.prescription_id=fraction.prescription_id " \
                                + "AND images.fraction_id=fraction.fraction_id " \
                                + f"AND patient.patient_trial_id=\'{self.metadata['patient_trial_id']}\' " \
                                + f"AND patient.clinical_trial=\'{self.metadata['clinical_trial']}\' " \
                                + f"AND patient.test_centre=\'{self.metadata['test_centre']}\'"
                result = self.dbAdapter.executeUpdateOnImageDB(insertStmt)
                if not result.success:
                    return result.success, result.message
                elif dbProgressCallback:
                    dbProgressCallback(f"updated {tableName}.{fieldName} = {fieldContent}")
        self.markPacketAsImported()
        return True, "Success"    

    def rejectUploadPacket(self):
        self.clearUploadPacket()
        self.metadata["processed"] = True
        self.metadata["accepted"] = False
        self._persistMetadata()

    def clearUploadPacket(self):
        # remove everything except the metadata file if the upload is processed
        uploadContextPath = config.UPLOAD_FOLDER + '/' + self.currentContextId
        uploadedFolders = [uploadContextPath + '/' + f \
                            for f in os.listdir(uploadContextPath) \
                                if os.path.isdir(uploadContextPath + '/' + f)]
        for folderPath in uploadedFolders:
            sh.rmtree(folderPath)
        
    def markPacketAsImported(self):
        self.metadata["processed"] = True
        self.metadata["accepted"] = True
        self._persistMetadata()
        # self.clearUploadPacket()

    def insertFractionDataIntoDatabase(self) -> Tuple[bool, str]:
        if not self.fileInfo or not self.dataIsValid:
            return False, "Please set an upload context and validate it before importing"
        fractionIdAndName = self.dbAdapter.getFractionIdAndName(self.metadata["patient_trial_id"], self.fileInfo["fraction"])
        fractionNameList = [name[1] for name in fractionIdAndName]
        subFractionList = self.fileInfo['sub_fraction'][:]
        if self.fileInfo["sub_fraction"] != [""] and set(fractionNameList) != set(subFractionList):
            initFractionDetail = self.dbAdapter.getFractionIdAndDate(self.metadata["patient_trial_id"], self.fileInfo["fraction"])
            subFractionList = [x for x in self.fileInfo['sub_fraction'] if x !=""]
            firstSubFraction = subFractionList.pop(0)
            self.dbAdapter.updateFractionName(initFractionDetail[0], firstSubFraction)
            allUpdate = True
            for subFraction in subFractionList:
                fractionPack = {
                    "patient_trial_id": self.metadata["patient_trial_id"],
                    "number": self.fileInfo["fraction"],
                    "name": subFraction,
                    "date": str(initFractionDetail[1]),
                }
                result = self.dbAdapter.insertFractionIntoDB(fractionPack)
                if not result:
                    allUpdate = False
            return allUpdate, "Success"
        else:
            return True, "Success"
    
    def insertImagePathIntoDatabase(self) -> Tuple[bool, str]:
        if not self.fileInfo or not self.dataIsValid:
            return False, "Please set an upload context and validate it before importing"
        
        fractionDetailList = self.dbAdapter.getFractionIdAndName(self.metadata["patient_trial_id"], self.fileInfo["fraction"])
        if len(fractionDetailList) == 1:
            fractionId = fractionDetailList[0][0]
            KV_pattern = r"(?i)\bKV\b"
            MV_pattern = r"(?i)\bMV\b"
            for folderPath in self.fileInfo["folder_path"]:
                if re.search(KV_pattern, folderPath):
                    kvQueryStr = f"UPDATE images SET kv_images_path = \'{folderPath}\' WHERE fraction_id = \'{fractionId}\'"
                    self.dbAdapter.executeUpdateOnImageDB(kvQueryStr)
                elif re.search(MV_pattern, folderPath):
                    mvQueryStr = f"UPDATE images SET mv_images_path = \'{folderPath}\' WHERE fraction_id = \'{fractionId}\'"
                    self.dbAdapter.executeUpdateOnImageDB(mvQueryStr)
        if len(fractionDetailList) > 1:
            for fractionDetail in fractionDetailList:
                if fractionDetail[1]:
                    fractionId = fractionDetail[0]
                    fractionName = fractionDetail[1]
                    imagePathPack = self.fileInfo["image_path"][fractionName]
                    kvQueryStr = f"UPDATE images SET kv_images_path = \'{imagePathPack['KV']}\' WHERE fraction_id = \'{fractionId}\'"
                    mvQueryStr = f"UPDATE images SET mv_images_path = \'{imagePathPack['MV']}\' WHERE fraction_id = \'{fractionId}\'"
                    self.dbAdapter.executeUpdateOnImageDB(kvQueryStr)
                    self.dbAdapter.executeUpdateOnImageDB(mvQueryStr)
        self.markPacketAsImported()
        return True, "Success"

def prepareArgumentParser():
    argParser = argparse.ArgumentParser(description="data Importer Tool")

    argParser.add_argument("--context", dest="context", 
                            help="Upload Context ID to be imported",
                            type=str, required=True)

    argParser.add_argument("--verify", dest="verify", 
                            help="Only verify integrity of the upload packet",
                            action="store_true", default=False)

    argParser.add_argument("--copyfiles", dest="copy", 
                            help="Only copy the files without inserting into DB",
                            action="store_true", default=False)

    argParser.add_argument("--update-db", dest="updateDB", 
                            help="Process upload packet and update database",
                            action="store_true", default=False)

    return argParser


def main():
    argParser = prepareArgumentParser()
    args = argParser.parse_args()

    dataImporter = DataImporter()
    dataImporter.setUploadContext(args.context)

    if args.updateDB:
        args.copy = True
    if args.copy:
       args.verify = True

    if args.verify:
        status = dataImporter.verifyUploadPacket()
        if not status[0]:
            print(f"Verification Failed: {status[1]}")
        else:
            print(f"Success: {status[1]}")

    copyProgressIndicator = lambda path: print('.', end='')
    if args.copy:
        print("Copying files", end=":")
        status = dataImporter.copyFilesIntoStorage(copyProgressIndicator)
        if not status[0]:
            print(f" Copying Failed: {status[1]}")
        else:
            print(f" Success: {status[1]}")

    if args.updateDB:
        print("Updating Database", end=":")
        status = dataImporter.insertMetadataIntoDatabase(copyProgressIndicator)
        if not status[0]:
            print(f" Update Failed: {status[1]}")
        else:
            print(f" Success: {status[1]}")

if __name__ == "__main__":
    main()
