import json
import os
from flask import make_response, send_from_directory, request
from werkzeug.utils import secure_filename
from typing import Dict, List
from datetime import datetime, time
from urllib import parse as urlutil
import pathlib
import mimetypes
import config
from pathlib import Path
from dbconnector import DBConnector
from flask_mail import Mail, Message
import random
import string

class ContentManager:
    def __init__(self) -> None:
        self.localRoot = config.DATA_FILESYSTEM_ROOT
        # self.connector = DBConnector(config.DB_NAME, 
        #                         config.DB_USER, 
        #                         config.DB_PASSWORD,
        #                         config.DB_HOST)
        # self.connector.connect()

    def setMailAgent(self, mail:Mail):
        self.mailAgent = mail
        # msg = Message("Test Message from database.", 
        #         sender=("Real-time Database System", "indrajit.ghosh@sydney.edu.au"),
        #         recipients=["indrajit.ghosh@sydney.edu.au"])
        # msg.body = "test message from the database system for notifications."
        # mail.send(msg)

    def _prepareDirectoryListing(self, path:str, baseUrl:str) -> Dict:
        if not os.path.isdir(self.localRoot + path):
            response = {
                "entity_name": path,
                "status": "unavailable",
                "message": "path is not a directory"
            }
            return response
        
        directoryListingInfo = {	
            "entity_name": path,
	        "type": "folder",
	        "listing_generated": datetime.now().isoformat(),
	        "status": "available",
            "contents": []
        }
        for dirpath, dirnames, filenames in os.walk(self.localRoot + path):
            for filename in filenames:
                fileStat = pathlib.Path(dirpath + os.sep + filename).stat()
                fileInfo = {
			        "entity_name": filename,
			        "type": "file",
			        "format": mimetypes.guess_type(filename)[0],
			        "full_path": baseUrl + urlutil.quote(path) + 
                                    '/' + urlutil.quote(filename),
			        "size": fileStat.st_size,
			        "c_time": datetime.fromtimestamp(fileStat.st_ctime).isoformat(),
                    "m_time": datetime.fromtimestamp(fileStat.st_mtime).isoformat(),
                    "a_time": datetime.fromtimestamp(fileStat.st_atime).isoformat()
		        }
                directoryListingInfo["contents"].append(fileInfo)

            for dirname in dirnames:
                dirStat = pathlib.Path(dirpath + os.sep + dirname).stat()
                dirInfo = {
			        "entity_name": dirname,
			        "type": "folder",
			        "full_path": baseUrl + urlutil.quote(path) + 
                                    '/' + urlutil.quote(dirname),
			        "c_time": datetime.fromtimestamp(dirStat.st_ctime).isoformat(),
                    "m_time": datetime.fromtimestamp(dirStat.st_mtime).isoformat(),
                    "a_time": datetime.fromtimestamp(dirStat.st_atime).isoformat()
		        }
                directoryListingInfo["contents"].append(dirInfo)

            break  # only list contents from the current level
        return directoryListingInfo

    def processRequest(self, path:str, baseUrl):
        print(f"content request arrived for {path}, {baseUrl}")
        if not os.path.exists(self.localRoot + path):
            print(f"{self.localRoot + path} does not exist")
            response = {
                "entity_name": path,
                "status": "unavailable",
                "message": "invalid path"
            }
            return make_response(response)

        if os.path.isdir(self.localRoot + path):
            listing = self._prepareDirectoryListing(path, baseUrl)
            return make_response(listing)
        
        pathComponents = path.split("/")
        filename = pathComponents[-1]
        lastSeparatorPos = path.rfind('/')
        directoryPath = self.localRoot + path[:lastSeparatorPos] \
                if lastSeparatorPos > 0 else self.localRoot
        return send_from_directory(directoryPath, filename, 
                                    as_attachment=True)

    # def _updateDatabaseWithFile(self, filePath: str, fileMetadata:Dict):
    #     try:
    #         conn = self.connector.getConnection() 
    #         cur = conn.cursor()
    #         # cur.execute("INSERT INTO token_details (token_subject, " \
    #         #             + "subject_email, audience, hashed_secret, reason) " \
    #         #             + "VALUES (%s, %s, %s, %s, %s);", 
    #         #             (inputData["subject_name"], 
    #         #             inputData["subject_email"],
    #         #             inputData["audience"],
    #         #             inputData["password_once"],
    #         #             inputData["notes"]))
    #         # conn.commit()

    #         # cur.execute("SELECT jwt_id FROM token_details WHERE " \
    #         #             + "token_subject = %s AND " \
    #         #             + "subject_email = %s AND " \
    #         #             + "audience = %s " \
    #         #             + "ORDER BY issued_at DESC;",
    #         #             (inputData["subject_name"],
    #         #             inputData["subject_email"],
    #         #             inputData["audience"]))
    #         # insertedTokenDetials = cur.fetchone()
    #         # cur.close()
    #     except (Exception, pg.DatabaseError) as error:
    #         print(error)

    def generateUploadId(self, size:int=8) -> str:
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(size))

    def acceptAndSaveFile(self, req:request):
        # print("Files:", req.files)
        # print("Form data:", req.form)
        # print("HTTP headers:", req.headers)
        
        # The data service can support either regular file uploads, in which 
        # case it copies the files to an appropriate location or it can support
        # just the upload of metadata, which can be used on files that do not 
        # need to be copied but just used from their existing location. This is
        # decided by the presence of the 'upload_type' field value.
        processFileUpload = True
        if "upload_type" in req.form.keys():
            if req.form["upload_type"] == "metadata":
                processFileUpload = False

        requiredFields = ["test_centre", "patient_trial_id", "level", 
                            "file_type", "fraction", "clinical_trial", 
                            "centre_patient_no", "upload_context"]
        metadata = {}

        for requiredField in requiredFields:
            if requiredField not in req.form.keys():
                returnMessage = {
                    "status": "error",
                    "message": f"Field {requiredField} missing in the submitted form"
                }
                print(returnMessage)
                return make_response(returnMessage)
            metadata[requiredField] = req.form[requiredField]

        uploadId:str = metadata["upload_context"]
        
        if os.path.isfile(config.UPLOAD_FOLDER + '/' + uploadId + '/upload_metadata.json'):
            with open(config.UPLOAD_FOLDER + '/' + uploadId + '/upload_metadata.json', 'r') \
                            as uploadMetaFile:
                uploadMetaData = json.load(uploadMetaFile)
        else:
            uploadMetaData = {
                "upload_id": uploadId,
                "clinical_trial": metadata["clinical_trial"],
                "test_centre": metadata["test_centre"],
                "patient_trial_id": metadata["patient_trial_id"],
                "upload_time": datetime.now().isoformat(),
                "upload_type": "files" if processFileUpload else "metadata",
                "processed": False,
                "accepted": False,
                "uploaded_by": "Default User",
                "upload_host": "127.0.0.1",
                "uploaded_files": []
            }

        if processFileUpload:
            if uploadMetaData["upload_type"] != "files":
                returnMessage = {
                    "status": "error",
                    "message": "upoad type inconsistent - files expected"
                }
                print(returnMessage)
                return make_response(returnMessage)

            if "Enctype" not in req.headers or \
                        req.headers["Enctype"] != "multipart/form-data":
                returnMessage = {
                    "status": "error",
                    "message": "Only multipart/form-data submissions are accepted"
                }
                print(returnMessage)
                return make_response(returnMessage)

            fileTypeToPathMappingPath = f"{config.DATA_FILESYSTEM_ROOT}/" \
                                        f"{metadata['clinical_trial']}/" \
                                        f"{metadata['test_centre']}/" \
                                        f"metadata/paths.json"
            if not os.path.isfile(fileTypeToPathMappingPath):
                fileTypeToPathMappingPath = "templates/upload_paths_template.json"
            
            with open(fileTypeToPathMappingPath, "r") as pathMappingFile:
                fileTypeToPathMapping = json.load(pathMappingFile)
            # print(fileTypeToPathMapping)

            filesSaved = []
            for fileFieldName in req.files.keys():
                uploadedFile = req.files[fileFieldName]
                filename = secure_filename(uploadedFile.filename)
                
                relativeFolderPath =  uploadId + \
                                fileTypeToPathMapping[metadata["file_type"]].format(
                                    clinical_trial=metadata['clinical_trial'],
                                    test_centre=metadata["test_centre"],
                                    patient_trial_id=metadata["patient_trial_id"],
                                    fraction_name=metadata["fraction"],
                                    centre_patient_no=int(metadata["centre_patient_no"])
                                )
                saveFolderPath = config.UPLOAD_FOLDER + '/' + relativeFolderPath
                relativePath = relativeFolderPath + filename
                filesSaved.append(relativePath)

            filePathAppended:bool = False
            for uploadedFileRecord in  uploadMetaData["uploaded_files"]:
                if uploadedFileRecord["file_type"] == metadata["file_type"]:
                    uploadedFileRecord["Files"].append(relativePath)
                    filePathAppended = True
                    break

            if not filePathAppended:
                uploadMetaData["uploaded_files"].append(
                    {
                        "file_type": metadata["file_type"],
                        "level": metadata["level"],
                        "fraction": metadata["fraction"],
                        "Files": [relativePath]
                    }
                )
            print(f"saving {filename} in {saveFolderPath}")
            Path(saveFolderPath).mkdir(parents=True, exist_ok=True)
            uploadedFile.save(os.path.join(saveFolderPath, filename))

            with open(config.UPLOAD_FOLDER + '/' + uploadId + '/summary.txt', 'a') \
                    as uploadSummaryFile:
                for savedFilePath in filesSaved:
                    uploadSummaryFile.write(savedFilePath + "\n")

        else:  # if not direct file upload, just metadata
            if "files" not in req.form.keys():
                returnMessage = {
                    "status": "error",
                    "message": "files paths not found in metadata only upload"
                }
                print(returnMessage)
                return make_response(returnMessage)

            Path(config.UPLOAD_FOLDER + '/' + uploadId).mkdir(parents=True, exist_ok=True)
            for filepath in json.loads(req.form["files"]):
                print(filepath)
                # bit of a repeated segement of code, possibly make it a lambda?
                filePathAppended:bool = False
                for uploadedFileRecord in uploadMetaData["uploaded_files"]:
                    if uploadedFileRecord["file_type"] == metadata["file_type"]:
                        uploadedFileRecord["Files"].append(filepath)
                        filePathAppended = True
                        break

                if not filePathAppended:
                    uploadMetaData["uploaded_files"].append(
                        {
                            "file_type": metadata["file_type"],
                            "level": metadata["level"],
                            "fraction": metadata["fraction"],
                            "Files": [filepath]
                        }
                    )

        with open(config.UPLOAD_FOLDER + '/' + uploadId + '/upload_metadata.json', 'w') \
                as uploadMetaFile:
            json.dump(uploadMetaData, uploadMetaFile, indent=4)

        returnMessage = make_response({"status": "success", "message": "file(s) accepted"})
        if not processFileUpload:
            returnMessage = make_response({"status": "success", "message": "file metadata accepted"})
        return returnMessage

    def uploadsSubmitted(self) -> List[Dict]:
        uploads = []
        for dirpath, dirnames, filenames in os.walk(config.UPLOAD_FOLDER):
            for dirname in dirnames:
                if dirname == 'metadata':
                    continue
                dirStat = pathlib.Path(dirpath + os.sep + dirname).stat()
                uploadInfo = {
                    "test_centre": "CMN",
                    "upload_id": dirname,
                    "upload_time": datetime.fromtimestamp(dirStat.st_ctime).isoformat(),
                    }
                uploads.append(uploadInfo)
            break  # only list contents from the current level
        return uploads

    def uploadDetails(self, uploadId:str) -> List[str]:
        filesUploaded = ["No Entries Found"]
        with open(config.UPLOAD_FOLDER + '/' + uploadId + '/summary.txt') as uploadSummaryFile:
            filesUploaded = [line for line in uploadSummaryFile.readlines()]
        return filesUploaded
