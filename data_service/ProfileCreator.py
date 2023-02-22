import pyminizip
import json
import hashlib
from typing import Dict, List
import argparse
import os
from tempfile import mkstemp


def createProfileFromJSONFile(filepath:str, password:str, profileName:str) -> str:
    with open(filepath, "r") as inputFile:
        inputData = json.load(inputFile)
    if "code" in inputData:
        del inputData["code"]
    parentDirPath = os.path.dirname(filepath)
    if inputData:    
        profileStr = json.dumps(inputData, sort_keys=True, indent=4)
        verificationCode = hashlib.sha256(profileStr.encode("utf-8")).hexdigest()
        inputData["code"] = verificationCode
        intermediateFilePath = parentDirPath + '/' + profileName + ".json"
        with open(intermediateFilePath, "w") as outputJSONFile:
            json.dump(inputData, outputJSONFile, indent=4)
        
        profilePath = parentDirPath + '/' + profileName + ".profile"
        pyminizip.compress(intermediateFilePath, None, 
                        profilePath, 
                        password, 0)
        os.remove(intermediateFilePath)
    return profilePath


def createProfileObject(instanceName:str, connections:List[Dict], defaultConnection:int=0) -> Dict:
    profileTemplate = { 
            "metadata": {
            "name": "Content Uploader Profile",
            "description": "This profile contains the site specific " \
                            "information required to connect and upload data",
            "version": "0.1.1"
        },
        "issuer": "LearnDB Access Management System",
        "instance_name": instanceName,
        "expires": "never",
        "code": "",
        "profiles": [],
        "default_profile": 0,
        "site_details": {
            "name": "",
            "fullname": "",
            "location": ""
        },
        "trial_details": [],
        "default_trial": 0        
    }

    profile = profileTemplate.copy()
    for connection in connections:
        profile["profiles"].append(connection)
    profile["default_profile"] = defaultConnection
    return profile


def saveProfileToJSON(profile:Dict, outputPath:str) -> str:
    if os.path.isdir(outputPath):
        fileDescriptor, fileName = mkstemp(suffix=".json", dir=outputPath)
    else:
        fileDescriptor, fileName = mkstemp(suffix=".json")
    print("temporary file name for profile JSON", fileName)
    with os.fdopen(fileDescriptor, 'w') as profileFile:
        json.dump(profile, profileFile, indent=4)
    return fileName


def createDirectConnectionProfile(hostname, 
                                baseUrl, 
                                token, 
                                password, 
                                importOnly=False) -> Dict:
    return {
        "name": f"Import without copying data to {hostname}" if importOnly else f"Upload to {hostname}",
        "connection_type": "IMPORT_ONLY" if importOnly else "DIRECT",
        "url": baseUrl,
        "token": token,
        "password": password
    }


def createProfile(profileName, hostname, instanceName, baseUrl, port, token, password, outputPath, develUse=True) -> str:
    connectionProfiles = []
    connectionProfiles.append(createDirectConnectionProfile(hostname, 
                                                            baseUrl, 
                                                            token, 
                                                            password, 
                                                            importOnly=False))
    connectionProfiles.append(createDirectConnectionProfile(hostname, 
                                                            baseUrl, 
                                                            token, 
                                                            password, 
                                                            importOnly=True))
    if develUse:
        connectionProfiles.append(createDirectConnectionProfile("localhost", 
                                                    f"http://localhost:{port}", 
                                                    token, 
                                                    password,
                                                    importOnly=False))
        connectionProfiles.append(createDirectConnectionProfile("localhost", 
                                                    f"http://localhost:{port}", 
                                                    token, 
                                                    password, 
                                                    importOnly=True))
    return createProfileFromJSONFile(
                saveProfileToJSON(createProfileObject(instanceName, connectionProfiles), outputPath),
                password, profileName)


def prepareArgumentParser():
    argParser = argparse.ArgumentParser(description="Create a profile from JSON")

    argParser.add_argument("-p", "--password", dest="password", 
                            help="The password used to encrypt the profile",
                            type=str, required=True)
    
    argParser.add_argument("-n", "--profile-name", dest="profileName", 
                            help="Name of the profile (output file)", 
                            type=str, required=True)

    argParser.add_argument("path", help="The input JSON file for creating the profile")

    return argParser


if __name__ == "__main__":
    argParser = prepareArgumentParser()
    args = argParser.parse_args()
    createProfileFromJSONFile(args.path, args.password, args.profileName)
