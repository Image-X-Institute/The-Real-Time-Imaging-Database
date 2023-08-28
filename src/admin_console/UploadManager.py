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
# from flask_mail import Mail, Message
import random
import string
from CustomTypes import UploadPacketType
from DatabaseAdapter import DatabaseAdapter


class UploadManager:
    def __init__(self) -> None:
        pass

    def findCurrentUploads(self, userId:str, uploadType=UploadPacketType.ANY) -> List[Dict]:
        dbAdapter = DatabaseAdapter()
        allowedTrialsAndSites = dbAdapter.getWritableTrialsAndSitesForUser(userId)
        uploads = []
        for dirpath, dirnames, filenames in os.walk(config.UPLOAD_FOLDER):
            for dirname in dirnames:
                if dirname == 'metadata':
                    continue
                uploadInfoFilePath = dirpath + "/" + dirname + \
                                    "/" + config.UPLOAD_METADATA_FILENAME
                if not os.path.isfile(uploadInfoFilePath):
                    continue

                with open(uploadInfoFilePath, "r") as uploadInfoFile:
                    uploadInfo = json.load(uploadInfoFile)

                if "clinical_trial" not in uploadInfo \
                    or uploadInfo["clinical_trial"] not in allowedTrialsAndSites:
                    continue

                uploadInfo["processed"] = False if "processed" not in uploadInfo \
                                                else uploadInfo["processed"]
                addUploadInfoToCurrentUploads = False
                if uploadType == UploadPacketType.ANY:
                     addUploadInfoToCurrentUploads = True
                elif uploadType == UploadPacketType.PROCESSED:
                    addUploadInfoToCurrentUploads = uploadInfo["processed"]
                elif uploadType == UploadPacketType.UNPROCESSED:
                    addUploadInfoToCurrentUploads = not uploadInfo["processed"]
                
                if addUploadInfoToCurrentUploads:
                    uploads.append(uploadInfo)
            break  # only list contents from the current level
        uploads = sorted(uploads, key=lambda x: x["upload_time"], reverse=True)
        return uploads

    def getUploadDetails(self, uploadId:str) -> Dict:
        uploadDetails = {}
        uploadDetailsPath = config.UPLOAD_FOLDER + '/' + uploadId + '/upload_metadata.json'
        if os.path.isfile(uploadDetailsPath):
            with open(uploadDetailsPath) as uploadDetailsFile:
                try:
                    uploadDetails = json.load(uploadDetailsFile)
                except:
                    print(f"Could not load uploadDetailsPath as JSON")
        return uploadDetails