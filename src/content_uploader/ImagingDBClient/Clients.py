import requests
from tempfile import mkdtemp, mkstemp, NamedTemporaryFile
import os
import json
from typing import Dict, Tuple, NamedTuple
from .cachemgmt import FilesCacheManager

from requests.sessions import InvalidSchema


class Result(NamedTuple):
    success: bool
    message: str


class ImagingDBClient:
    RESPONSE_TYPE_LISTING = "listing"
    RESPONSE_TYPE_FILE = "file"
    RESPONSE_TYPE_ERR = "error"

    def __init__(self, baseUrl="http://localhost:8090", 
                downloadPath=None,
                token='',
                useLocalCaching=True) -> None:
        self.baseUrl = baseUrl
        if downloadPath is None:
            downloadPath = mkdtemp()
        self.downloadCachePath = downloadPath
        print("Using temporary cache path:", self.downloadCachePath)            
        self.authToken = token
        self.isAuthenticated = False
        self._sessionToken = ''
        self.useLocalCaching = useLocalCaching

    def __del__(self):
        self.clearCache()

    def getPatients(self) -> Dict:
        try:
            req = requests.get(self.baseUrl 
                            + "/patients",
                            headers={"Token": self._sessionToken})
        except (Exception, InvalidSchema) as ex:
            return {"status": self.RESPONSE_TYPE_ERR, "message":str(ex)}
        return req.json()

    def getPatientDetails(self, patientTrialId:str)->Dict:
        try:
            req = requests.get(self.baseUrl 
                            + "/patients?patient_trial_id=" + patientTrialId,
                            headers={"Token": self._sessionToken})
        except (Exception, InvalidSchema) as ex:
            return {"status": self.RESPONSE_TYPE_ERR, "message":str(ex)}
        return req.json()

    def getPrescriptionDetailsForPatient(self, patientTrialId:str)->Dict:
        try:
            req = requests.get(self.baseUrl 
                            + "/presciptions?patient_trial_id=" + patientTrialId,
                            headers={"Token": self._sessionToken})
        except (Exception, InvalidSchema) as ex:
            return {"status": self.RESPONSE_TYPE_ERR, "message":str(ex)}
        return req.json()

    def getFractionDetailsForPatient(self, patientTrialId:str)->Dict:
        try:
            req = requests.get(self.baseUrl 
                            + "/fractions?patient_trial_id=" + patientTrialId,
                            headers={"Token": self._sessionToken})
        except (Exception, InvalidSchema) as ex:
            return {"status": self.RESPONSE_TYPE_ERR, "message":str(ex)}
        return req.json()

    def makeAuthRequest(self, token=None, additionalParams:Dict[str, str]={}) -> bool:
        if token is not None and isinstance(token, str):
            self.authToken = token
        
        if additionalParams is None or len(additionalParams) == 0:
            additionalParams = {"LearnDBClient": "Python Client Library"}
        else:
            additionalParams["LearnDBClient"] = "Python Client Library"
        try:
            if self.authToken:
                r = requests.post(self.baseUrl + "/auth", 
                                data=additionalParams,
                                headers={"Token": self.authToken})
            else:
                r = requests.post(self.baseUrl + "/auth", 
                                data=additionalParams)

        except requests.exceptions.RequestException as ex:
            print(f"exception while trying to authenticate {ex}")
            return False
        except ValueError as verr:
            print(f"exception while trying to authenticate {verr}")
            return False

        try:
            responseData = r.json()
        except json.decoder.JSONDecodeError as jderr:
            print(f"Error interpreting the response into JSON: {jderr}")
            print(f"Actual response from the server: {r.content}", r)
            return False
        
        if "token" in responseData:
            self._sessionToken = responseData["token"]
        
        self.isAuthenticated = True if "token" in responseData else False
        return self.isAuthenticated

    def clearCache(self) -> None:
        # Note: This only clears the temporary folder where the downloaded
        # files are placed and not the local cache used to speed up downloads
        if not self.useLocalCaching:
            for filename in os.listdir(self.downloadCachePath):
                filePath = os.path.join(self.downloadCachePath, filename)
                if os.path.isfile(filePath):
                    os.unlink(filePath)

    def makeContentRequest(self, url:str) -> Tuple:
        if self.useLocalCaching:
            cacheMgr = FilesCacheManager(key=self.authToken[:12])
            if cacheMgr.lookup(url):
                content = cacheMgr.getFileContent(url)
                originalFilename = cacheMgr.getOriginalFilename(url)
                if originalFilename:
                    tf = open(os.path.join(self.downloadCachePath, originalFilename), 'wb')
                else:
                    tf = NamedTemporaryFile(dir=self.downloadCachePath, delete=False)
                tf.write(content)
                tf.close()
                return self.RESPONSE_TYPE_FILE, cacheMgr.getFileType(url), tf.name
        try:
            req = requests.get(url, headers={"Token": self._sessionToken})
        except (Exception, InvalidSchema) as ex:
            return self.RESPONSE_TYPE_ERR, "", {"message":str(ex)}

        if "Content-Disposition" in req.headers:
            contentDispComponents = req.headers["Content-Disposition"].split("filename=")
            if len(contentDispComponents) > 1:
                tempfilePath = os.path.join(self.downloadCachePath, 
                                            contentDispComponents[-1])
            else:
                tempFd, tempfilePath = mkstemp(dir=self.downloadCachePath)

            if self.useLocalCaching:
                cacheMgr = FilesCacheManager(key=self.authToken[:12])
                cacheMgr.cache(url, req.content, 
                                fileType=req.headers["Content-Type"],
                                originalFilename=contentDispComponents[-1])

            with open(tempfilePath, "wb") as tempFile:
                tempFile.write(req.content)
            return self.RESPONSE_TYPE_FILE, req.headers["Content-Type"], tempfilePath
        else:
            if req.headers["Content-Type"] == "application/json":
                content = req.json()
                if "status" in content and content["status"] == "available":
                    return self.RESPONSE_TYPE_LISTING, "application/json", content
                else:
                    return self.RESPONSE_TYPE_ERR, "application/json", content
        return self.RESPONSE_TYPE_ERR, "application/json", {"message": "Unexpected response recieved"}

    def acquireUploadContext(self) -> str:
        uploadContext:str = ""
        r = requests.post(self.baseUrl + "/upload/getUploadContext",
                        headers={"Token": self._sessionToken})
        try:
            responseData = r.json()
            if responseData["status"] == "success":
                uploadContext = responseData["context"]
        except json.decoder.JSONDecodeError as decodeErr:
            print ("Could not understand the server response:", r.text)
        return uploadContext

    def uploadContent(self, data, files=None, uploadOnlyMetadata=False) -> bool:
        data["upload_type"] = "metadata" if uploadOnlyMetadata else "files"
        if uploadOnlyMetadata:
            r = requests.post(self.baseUrl + "/upload/files", 
                            data=data, 
                            headers={"Token": self._sessionToken})
        else:
            if files is None:
                return False
            r = requests.post(self.baseUrl + "/upload/files", 
                            files=files, data=data, 
                            headers={"Enctype": "multipart/form-data", 
                                    "Token": self._sessionToken})
        try:
            responseData = r.json()
            return True if responseData["status"] == "success" else False
        except json.decoder.JSONDecodeError as decodeErr:
            print ("Could not understand the server response:", r.text)
            return False

    def addPatient(self, patientDetails:Dict) -> Result:
        try:
            req = requests.post(self.baseUrl + "/add-patient",
                            json=patientDetails,
                            headers={"Token": self._sessionToken,
                            "Content-Type": "application/json"})
        except (Exception, InvalidSchema) as ex:
            return Result(success=False, message=str(ex))

        if req.status_code == 200 or req.status_code == 201:
            return Result(success=True, message="Added patient successfully")
        return Result(success=False, message=f"data service retured {req.status_code}")
    
    def addFraction(self, fractionDetails:Dict) -> Result:
        # , site:str, centre:str
        try:
            req = requests.post(self.baseUrl + "/add-fraction",
                            json=fractionDetails,
                            headers={"Token": self._sessionToken,
                            "Content-Type": "application/json"})
        except (Exception, InvalidSchema) as ex:
            return Result(success=False, message=str(ex))

        if req.status_code == 200 or req.status_code == 201:
            return Result(success=True, message="Added fraction successfully")
        return Result(success=False, message=f"data service retured {req.status_code}")
