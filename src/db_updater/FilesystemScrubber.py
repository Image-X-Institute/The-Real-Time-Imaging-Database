import os
from typing import Tuple, Dict, List
import json
import re
import platform
import datetime as dt
import operator
import time


def getFilenameFromPath(filepath: str) -> str:
    pathComponents = filepath.split('/')
    return pathComponents[-1]


def getActualFilePath(templateFilePath: str, basePath:str, numRetries:int=3) -> str:

    retryCounter = numRetries
    while (retryCounter > 0):
        try:
            return processSearchPath(templateFilePath, basePath)
        except OSError as err:
            print(err, "trying again ...")
            time.sleep(0.5) # sleep for half a second before retrying again
            retryCounter -= 1
    return None


def processSearchPath(pathPattern:str, rootSearchPath:str) -> str:
    # print("processSearchPath() called with pathPattern=", pathPattern, "rootSearchPath=", rootSearchPath)
    pathOptions = pathPattern.split(';')
    for path in pathOptions:
        if "::containing" in path:
            path, containedFilePattern = path.split("::containing")
            containedFilePattern = containedFilePattern.strip()
        else:
            containedFilePattern = ""

        includeAllMatchingFiles = False
        if "::all_matching" in path:
            path, directive = path.split("::all_matching")
            path = path.strip()  # in case there is a space before ::
            includeAllMatchingFiles = True
        
        matchedPath, matchedFullPath = findMatchingFileOrFolder(path, 
                                                        rootSearchPath, 
                                                        includeAllMatchingFiles)
        if matchedPath == "not found":
            # print("findMatchingFileOrFolder() returned not found")
            continue
        else:
            pass
            # print("findMatchingFileOrFolder() returned", matchedPath, matchedFullPath)
        
        if len(containedFilePattern) > 0:
            filepath,_ = findMatchingFileOrFolder(containedFilePattern, 
                                                    matchedFullPath)
            if filepath == "not found":
                # print("findMatchingFileOrFolder() returned not found")
                matchedPath = filepath
            else:
                pass
                # print("findMatchingFileOrFolder() returned filepath=", filepath)
        
        if matchedPath != "not found":  # return the first matching path
            return matchedPath
            
    return matchedPath


def findMatchingFileOrFolder(pathPattern:str, 
                            rootSearchPath:str, 
                            includeAllMatchingFiles:bool=False) -> Tuple[str, str]:
    # print("findMatchingFileOrFolder() called with pathPattern=", pathPattern, "rootSearchPath=", rootSearchPath)
    assert os.path.isdir(rootSearchPath), f"Could not locate {rootSearchPath}"

    matchingPath:str = ""
    processedPath:str = rootSearchPath
    allMatchingFiles:List[str] = []

    pathComponents:List[str] = pathPattern.split("/")
    for index, component in enumerate(pathComponents):
        foundMatchingComponent = False
        for entity in os.listdir(processedPath):
            # print(f"trying to match {component} with {entity}")
            if re.match(component, entity, flags=re.IGNORECASE):
                # print(f"found expression {component} to match file/folder: {entity}")
                tentativePath = os.path.join(processedPath, entity)
                if index < (len(pathComponents) - 1) \
                    and not os.path.isdir(tentativePath):
                    continue  # found a file with the name that it expects a folder to have
                processedPath = tentativePath
                foundMatchingComponent = True
                if includeAllMatchingFiles and index == len(pathComponents) - 1:
                    allMatchingFiles.append(matchingPath + "/" + entity)
                else:
                    matchingPath = matchingPath + "/" + entity
                    break  # Just use the first matching file

        if not foundMatchingComponent:
            matchingPath = "not found"
            break
        elif includeAllMatchingFiles:
            for matchedFile in allMatchingFiles:
                matchingPath += matchedFile + ";"
    
    return matchingPath, processedPath


def _getActualFilePath(templateFilePath: str, basePath:str) -> str:
    """ Deprecated """
    pathOptions = templateFilePath.split('|')
    for path in pathOptions:
        if "::containing" in path:
            matchContainedFiles = True
            path, containedFilePattern = path.split("::containing")
            path = path.strip()
            containedFilePattern = containedFilePattern.strip()
        else:
            matchContainedFiles = False
            
        # print("path being searched: " + path)
        if os.path.isdir(basePath + path):
            if not matchContainedFiles:
                # print(" Exact directory path match")
                return path

        if os.path.isfile(basePath + path):
            # print(" Exact file path match")
            return path
        
        if matchContainedFiles:
             # in this case case, this function should return a folder not a file
            containingFolder = path
        else:
            containingFolder = os.path.dirname(path)

        fullPathOfContainingFolder = basePath + containingFolder
        if os.path.isdir(fullPathOfContainingFolder):
            allFilesInContainingFolder = \
                [containingFolder + '/' + f for f in os.listdir(fullPathOfContainingFolder)] 

            # print("found", len(allFilesInContainingFolder), "files in the folder", fullPathOfContainingFolder)
            for fileInPath in allFilesInContainingFolder:
                if matchContainedFiles:
                    regularExpression = path + '/' + containedFilePattern
                else:
                    regularExpression = path
                
                # print(f"trying to match {fileInPath} with the expression {regularExpression}")
                if re.match(regularExpression, fileInPath, re.IGNORECASE) is not None:
                    if matchContainedFiles:
                        # print("found folder match with containing files", fileInPath)
                        return path
                    else:
                        # print("found match", fileInPath)
                        return fileInPath
        else:
            print(fullPathOfContainingFolder, "is not a directory?")

    print("  ** could not find any matching folder or file for " + templateFilePath)
    return None  # no matching path found


def findAndOrganisePatientData(templateFilePath: str, patientSeqRange: Tuple[int, int]) -> Dict:
    """ Deprecated """
    templateStruct = {}
    basePath = "X:/2RESEARCH/1_ClinicalData/"
    with open(templateFilePath) as templateFile:
        templateStruct = json.loads(templateFile.read())

    allPatients = []
    for patientSeq in range(patientSeqRange[0], patientSeqRange[1] + 1):
        patientObject = {"centre_patient_no": 0, "fractions": []}
        for topLevelKey in templateStruct:
            print("[" + topLevelKey + "]")
            if isinstance(templateStruct[topLevelKey], str):
                substituedValue = templateStruct[topLevelKey].format(patient_seq=patientSeq)
                if topLevelKey == "patient_trial_id":
                    patientObject[topLevelKey] = substituedValue
                else:
                    actualValue = getActualFilePath(substituedValue, basePath)
                    if actualValue is None:
                        # patientObject[topLevelKey] = "**" + substituedValue
                        patientObject[topLevelKey] = "not found"
                    else:
                        patientObject[topLevelKey] = actualValue

            elif topLevelKey == "fractions":
                for currentFraction in templateStruct[topLevelKey]:
                    fractionObject = {}
                    for fractionLevelKey in currentFraction:
                        print("Processing [fractions][" + fractionLevelKey + "]")
                        if isinstance(currentFraction[fractionLevelKey], str):
                            fractionValue = currentFraction[fractionLevelKey]
                            substituedValue = fractionValue.format(patient_seq=patientSeq)
                            print("Substituted value:", substituedValue)
                            actualValue = getActualFilePath(substituedValue, basePath)
                            if actualValue is None:
                                #fractionObject[fractionLevelKey] = "**" + substituedValue
                                fractionObject[fractionLevelKey] = "not found"
                            else:
                                fractionObject[fractionLevelKey] = actualValue

                        elif isinstance(currentFraction[fractionLevelKey], dict):
                            fractionValue = currentFraction[fractionLevelKey]["path"]
                            fractionObject[fractionLevelKey] = currentFraction[fractionLevelKey]
                            substituedValue = fractionValue.format(patient_seq=patientSeq)
                            actualValue = getActualFilePath(substituedValue, basePath)
                            if actualValue is None:
                                # fractionObject[fractionLevelKey]["path"] = "**" + substituedValue
                                fractionObject[fractionLevelKey]["path"] = "not found"
                            else:
                                fractionObject[fractionLevelKey]["path"] = actualValue

                        else:
                            fractionObject[fractionLevelKey] = currentFraction[fractionLevelKey]
                            print("    directly assigned")
                    patientObject["fractions"].append(fractionObject)

            else:
                if topLevelKey == "centre_patient_no":
                    patientObject[topLevelKey] = patientSeq
                else:
                    patientObject[topLevelKey] = templateStruct[topLevelKey]
        allPatients.append(patientObject)

    return allPatients


def findMajorityVote(itemList:List):
    itemCounts = dict()
    for dateEntry in itemList:
        if dateEntry in itemCounts:
            itemCounts[dateEntry] += 1
        else:
            itemCounts[dateEntry] = 1

    return max(itemCounts.items(), key=operator.itemgetter(1))[0]


def findFractionDetailsFromFiles(testCentre: str,
                                clinicalTrialName: str,
                                fsRootPath: str,
                                imagesFolderName:str="Patient Images",
                                patientDirpattern:str="Patient*") -> List[Dict]:
    numberOfFilesToCheck = 10
    allFractionDetails = []

    imagesBasePath = os.path.join(fsRootPath, clinicalTrialName, 
                                    testCentre, imagesFolderName)
    # print("Iterating over: " + imagesBasePath)
    for patientDir in os.listdir(path=imagesBasePath):
        patientDirFullpath = os.path.join(imagesBasePath, patientDir)
        if os.path.isdir(patientDirFullpath) and \
                    re.match(patientDirpattern, patientDir):
            # print(patientDir)
            numbers = re.findall(r"\d+", patientDir)
            patientSequence = numbers[0] if len(numbers) > 0 else 0

            for fractionDir in os.listdir(patientDirFullpath):
                fractionDirFullpath = os.path.join(patientDirFullpath, 
                                                    fractionDir)
                if os.path.isdir(fractionDirFullpath):
                    for fractionsSubDir in os.listdir(fractionDirFullpath):
                        fractionsSubDirFullPath = os.path.join(fractionDir, 
                                                        fractionDirFullpath)

                        if os.path.isdir(fractionsSubDirFullPath) and \
                                        (fractionsSubDir == "KIM-MV" or fractionsSubDir == "MV"):

                            fractionDetails = dict()
                            numbers = re.findall(r"\d+", fractionDir)
                            fractionNumber = numbers[0] if len(numbers) > 0 else 0
                            fractionDetails["fraction_number"] = int(fractionNumber)
                            fractionDetails["test_centre"] = testCentre            
                            fractionDetails["patient_sequence"] = int(patientSequence)
                            fractionDetails["fraction_name"] = fractionDir
                            
                            mvDirFullpath = os.path.join(fractionsSubDirFullPath, 
                                                        fractionsSubDir)
                            fileDates = []
                            fileCounter = -1
                            for mvImgFile in os.listdir(mvDirFullpath):
                                if os.path.isdir(mvImgFile):
                                    continue
                                mvImagefileFullPath = os.path.join(mvDirFullpath, 
                                                                    mvImgFile)
                                fileCounter += 1
                                if fileCounter >= numberOfFilesToCheck:
                                    break
                                if platform.system() == "Windows":
                                    fileDate = dt.datetime.fromtimestamp(
                                                    os.path.getmtime(
                                                        mvImagefileFullPath)).date()
                                    fileDates.append(fileDate)
                                    
                            mvImagesDate = findMajorityVote(fileDates)
                            # print(len(fileDates), mvImagesDate)
                            fractionDetails["fraction_date"] = mvImagesDate.isoformat()
                            #fractionDetails["num_gating_events"] = 0
                            print(fractionDetails)
                            allFractionDetails.append(fractionDetails)
    return allFractionDetails


def getNumberofGatingEvents(fsRootPath: str,
                            clinicalTrialName: str,
                            testCentre: str,
                            measuredMotionFolder:str,
                            patientSequence:int,
                            fractionName:str) -> int:
    basePath = os.path.join(fsRootPath, clinicalTrialName, testCentre)
    motionDirFullPath = os.path.join(basePath, measuredMotionFolder)
    patientFolderPattern = "[a-z,-,_]*PAT" + str(patientSequence).zfill(2) + "[a-z,-,_, ,]*"
    fractionFolderPattern = "[a-z,0-9,-,_]*" + fractionName
    numGatingEvents = -2
    for patientDir in os.listdir(path=motionDirFullPath):
        if re.match(patientFolderPattern, patientDir, re.IGNORECASE):
            print(patientDir, "matched")
            patientDirFullPath = os.path.join(motionDirFullPath, patientDir)
            for fractionDir in os.listdir(path=patientDirFullPath):
                if re.match(fractionFolderPattern, fractionDir, re.IGNORECASE):
                    print(" " + fractionDir, "matched")
                    fractionDirFullPath = os.path.join(patientDirFullPath, fractionDir)
                    for fractionFile in os.listdir(path=fractionDirFullPath):
                        if re.match("MarkerLocationsGA[_,a-z,0-9]*.txt", fractionFile, re.IGNORECASE):
                            print("    " + fractionFile, "matched")
                            numGatingEvents += 1
    return numGatingEvents


def getPatientDataTemplate(trialName:str, centreName: str) -> Dict:
    template = {}
    try:
        templateFilePath = "data/templates/" + trialName + "_" + centreName \
                            + "_data_template.json"
        with open(templateFilePath, "r") as templateFile:
            template = json.load(templateFile)
    except FileNotFoundError as fnfErr:
        advice = f"Please create a template file in {templateFilePath}"
        print(f"WARN: Skipping centre {centreName} for {trialName} trial since \
             no template file found. {advice}")
    return template


class FilesystemScrubber:
    def __init__(self, patientsMetaDataPath:str) -> None:
        self.patientsMetaData = self._loadPatientsMetaData(patientsMetaDataPath)
        self.fsRootpath = ""
        self._load_local_settings()
        assert os.path.isdir(self.fsRootpath), "the root folder path is invalid"        

    def _loadPatientsMetaData(self, patientMetaDataPath:str) -> Dict:
        with open(patientMetaDataPath, "r") as patientDataFile:
            patientData = json.load(patientDataFile)
        return patientData

    def _getFractionsForPatient(self, fractionDetails: Dict, 
                                        testCentre:str, 
                                        patientSequence: int) -> List:
        fractions = []
        for frac in fractionDetails["fractions"]:
            if frac["test_centre"] == testCentre and \
                        frac["patient_sequence"] == patientSequence:
                fractions.append(frac)
        return fractions

    def _load_local_settings(self):
        settingsFilePath = "data/local_settings.json"
        try:
            with open(settingsFilePath) as localSettingsFile:
                localsettings = json.load(localSettingsFile)
            self.fsRootpath = localsettings["root_filesystem_path"]
        except FileNotFoundError as fnfErr:
            print(f"ERROR: Please create a {settingsFilePath} file")
            raise fnfErr

    def _findAndCacheFractionDetails(self, centreName:str, trialName:str) -> Dict:
        fractionDetails = findFractionDetailsFromFiles(centreName, 
                                        trialName, self.fsRootpath)
        for fractionDetail in fractionDetails:
            fractionDetail["num_gating_events"] = getNumberofGatingEvents(
                        fsRootPath=self.fsRootpath,
                        clinicalTrialName=trialName,
                        testCentre=centreName,
                        measuredMotionFolder="Patient Measured Motion",
                        patientSequence=fractionDetail["patient_sequence"],
                        fractionName=fractionDetail["fraction_name"])
            print(fractionDetail)

        fractionDetails = {"fractions" : fractionDetails}
        # save a local cached copy of the fractions data
        with open(f"{trialName}_{centreName}_scrubbed_fraction_data.json", mode="w") as outputFile:
            json.dump(fractionDetails,
                        outputFile, indent=4, sort_keys=False)
        return fractionDetails

    def _mergeWithReferencePatientData(self, patientDataFromFS: Dict) -> Dict:
        referenceData = {}
        with open("data/reference_patient_data.json", "r") as referenceDataFile:
            referenceData = json.load(referenceDataFile)

        for referenceTrial in referenceData["clinical_data"]:
            processedTrials = []
            for trial in patientDataFromFS["clinical_data"]:
                if referenceTrial["clinical_trial"] == trial["clinical_trial"]:
                    processedTrials.append(trial["clinical_trial"])
                    for referenceCentre in referenceTrial["centres"]:
                        processedCentres = []
                        for centre in trial["centres"]:
                            if referenceCentre["centre"] == centre["centre"]:
                                processedCentres.append(centre["centre"])
                                for referencePatient in referenceCentre["patients"]:
                                    for patient in centre["patients"]:
                                        if referencePatient["patient_trial_id"] == patient["patient_trial_id"]:
                                            for referenceFraction in referencePatient["fractions"]:
                                                for fraction in patient["fractions"]:
                                                    if referenceFraction["fraction_name"] == fraction["fraction_name"]:
                                                        for fractionKey in fraction.keys():
                                                            if isinstance(fraction[fractionKey], dict):
                                                                if fraction[fractionKey]["path"] == "not found":
                                                                    # check if this key exists in the checked in data
                                                                    # if it is a newly added key then it would not be 
                                                                    # present in the refreence data.
                                                                    if fractionKey in referenceFraction and "path" in referenceFraction[fractionKey]:
                                                                        fraction[fractionKey]["path"] = referenceFraction[fractionKey]["path"]
                                                            elif fraction[fractionKey] == "not found":
                                                                if fractionKey in referenceFraction:
                                                                    fraction[fractionKey] = referenceFraction[fractionKey]
                                            for patientKey in patient.keys():
                                                if isinstance(patientKey, str) and patient[patientKey] == "not found":
                                                    if patientKey in referencePatient:
                                                        patient[patientKey] = referencePatient[patientKey]
                        if referenceCentre["centre"] not in processedCentres:
                            trial["centres"].append(referenceCentre.copy())
            if referenceTrial["clinical_trial"] not in processedTrials:
                patientDataFromFS["clinical_data"].append(referenceTrial)

        return patientDataFromFS


    def generatePatientDataFromFileSystem(self, srubbedDataFilePath:str):
        organisedData:Dict = {"clinical_data": []}
        for trialDetails in self.patientsMetaData["clinical_data"]:
            trialName = trialDetails["clinical_trial"]
            print(f"\nCollecting data for {trialName}", end=" ", flush=True)
            finalTrialStructrue = {"clinical_trial": trialName, "centres": []}
            for centreDetails in trialDetails["centres"]:
                centreName = centreDetails["centre"]

                try:
                    with open(f"data/{trialName}_{centreName}_scrubbed_fraction_data.json", mode="r") as fractionFile:
                        fractionDetails = json.load(fractionFile)
                except FileNotFoundError as fnfErr:
                    print("Could not find cached fraction details file, creating it from filesystem")
                    fractionDetails = self._findAndCacheFractionDetails(centreName, trialName)

                centreObject = {"centre": centreName, "patients": []}
                patientDataTemplate = getPatientDataTemplate(trialName, centreName)
                print(f"\n  centre {centreName}", end=" ", flush=True)
                if len(patientDataTemplate) == 0:
                    continue
                for patientDetails in centreDetails["patients"]:
                    patientObject = {"centre_patient_no": 0, "fractions": []}
                    print(f"\n    Processing patient {patientDetails['patient_trial_id']}", end=": ", flush=True)
                    for topLevelKey in patientDataTemplate.keys():
                        # print("[" + topLevelKey + "]")
                        if isinstance(patientDataTemplate[topLevelKey], str):
                            substituedValue = patientDataTemplate[topLevelKey].format(
                                                patient_trial_id=patientDetails["patient_trial_id"], 
                                                centre_patient_no=patientDetails["centre_patient_no"], 
                                                age=patientDetails["age"], 
                                                gender=patientDetails["gender"],
                                                tumour_site=patientDetails["tumour_site"],
                                                number_of_markers=patientDetails["number_of_markers"],
                                                LINAC_type=patientDetails["LINAC_type"])

                            if "path" in topLevelKey:
                                actualValue = getActualFilePath(substituedValue, self.fsRootpath)
                                if actualValue is None:
                                    patientObject[topLevelKey] = "not found"
                                else:
                                    patientObject[topLevelKey] = actualValue
                            else:
                                if topLevelKey == "centre_patient_no":
                                    patientObject[topLevelKey] = int(substituedValue)
                                else:
                                    patientObject[topLevelKey] = substituedValue

                        elif topLevelKey == "fractions":
                            scrubbedFractionData = self._getFractionsForPatient(fractionDetails, centreName, 
                                                            patientDetails["centre_patient_no"])
                                                    
                            for fraction in scrubbedFractionData:
                                print(f"{fraction['fraction_name']}", end=" ", flush=True)
                                for fractionTemplate in patientDataTemplate[topLevelKey]:
                                    fractionObject = fractionTemplate.copy()
                                    for fractionLevelKey in fractionObject.keys():
                                        # print("centre_patient_no:", patientDetails["centre_patient_no"])
                                        # print("Processing [fractions][" + fractionLevelKey + "]")
                                        fractionValue = fractionObject[fractionLevelKey]

                                        if isinstance(fractionValue, str):
                                            substituedValue = fractionValue.format(
                                                    patient_trial_id=patientDetails["patient_trial_id"], 
                                                    centre_patient_no=patientDetails["centre_patient_no"],
                                                    fraction_number=fraction["fraction_number"],
                                                    fraction_name=fraction["fraction_name"],
                                                    fraction_date=fraction["fraction_date"],
                                                    mvsdd=fraction["mvsdd"] if "mvsdd" in fraction else "0.0",
                                                    kvsdd=fraction["kvsdd"] if "kvsdd" in fraction else "0.0",
                                                    num_gating_events=fraction["num_gating_events"])
                                            # print("  Substituted value:", substituedValue)

                                            if "path" in fractionLevelKey or "logs" in fractionLevelKey:
                                                actualValue = getActualFilePath(substituedValue, self.fsRootpath)
                                                if actualValue is None:
                                                    fractionObject[fractionLevelKey] = "not found"
                                                else:
                                                    fractionObject[fractionLevelKey] = actualValue
                                            else:
                                                fractionObject[fractionLevelKey] = substituedValue

                                        elif isinstance(fractionValue, dict):
                                            fractionObject[fractionLevelKey] = fractionValue.copy()  # important to make a copy
                                            substituedValue = fractionValue["path"].format( 
                                                    centre_patient_no=patientDetails["centre_patient_no"],
                                                    patient_trial_id=patientDetails["patient_trial_id"],
                                                    fraction_name=fraction["fraction_name"],
                                                    fraction_number=fraction["fraction_number"])
                                            actualValue = getActualFilePath(substituedValue, self.fsRootpath)
                                            if actualValue is None:
                                                fractionObject[fractionLevelKey]["path"] = "not found"
                                            else:
                                                fractionObject[fractionLevelKey]["path"] = actualValue

                                        else:
                                            fractionObject[fractionLevelKey] = fractionValue
                                    patientObject["fractions"].append(fractionObject)

                        else:
                            patientObject[topLevelKey] = patientDataTemplate[topLevelKey]

                    centreObject["patients"].append(patientObject)

                finalTrialStructrue["centres"].append(centreObject)

            organisedData["clinical_data"].append(finalTrialStructrue)

        organisedData = self._mergeWithReferencePatientData(organisedData)
        with open(srubbedDataFilePath, mode="w") as outputFile:
            json.dump(organisedData, outputFile, indent=4, sort_keys=False)
        


def scrubFilesystem():
    scrubber = FilesystemScrubber(patientsMetaDataPath="data/patients_meta_data.json")
    scrubber.generatePatientDataFromFileSystem("scrubbed_patient_data.json")


def findFractions():
    with open("data/local_settings.json") as localSettingsFile:
        localsettings = json.load(localSettingsFile)
    fsRootpath = localsettings["root_filesystem_path"]    
    fractionDetails = findFractionDetailsFromFiles("CMN", "SPARK", fsRootpath)

    for fractionDetail in fractionDetails:
        fractionDetail["num_gating_events"] = getNumberofGatingEvents(
                    fsRootPath=fsRootpath,
                    clinicalTrialName="SPARK",
                    testCentre="CMN",
                    measuredMotionFolder="Patient Measured Motion",
                    patientSequence=fractionDetail["patient_sequence"],
                    fractionName=fractionDetail["fraction_name"])
        print(fractionDetail)

    with open("scrubbed_fraction_data.json", mode="w") as outputFile:
        json.dump({"fractions" : fractionDetails},
                    outputFile, indent=4, sort_keys=False)


def updateScrubbedPatientDetailsWithFractions():
    with open("scrubbed_patient_data.json", "r") as patientFile:
        scrubbedPatientDetails = json.load(patientFile)

    with open("scrubbed_fraction_data.json", "r") as fractionFile:
        scrubbedFactionDetails = json.load(fractionFile)

    for trialDetails in scrubbedPatientDetails["clinical_data"]:
        for centreDetails in trialDetails["centres"]:
            centreName = centreDetails["centre"]
            for patientDetails in centreDetails["patients"]:
                patientNumber = patientDetails["centre_patient_no"]
                for fractionDetails in patientDetails["fractions"]:
                    for f in scrubbedFactionDetails["fractions"]:
                        if f["test_centre"] == centreName \
                                and f["patient_sequence"] == patientNumber:
                            pass

    with open("scrubbed_patient_data.json", mode="w") as outputFile:
        json.dump(scrubbedPatientDetails, outputFile, indent=4, sort_keys=False)


def testMergeFunctionality():
    with open("scrubbed_patient_data.json", "r") as patientDataFile:
        patientData = json.load(patientDataFile)
    scrubber = FilesystemScrubber(patientsMetaDataPath="data/patients_meta_data.json")
    mergedData = scrubber._mergeWithReferencePatientData(patientData)
    with open("merged_patient_data.json", "w") as mergedDataFile:
        json.dump(mergedData, mergedDataFile, indent=4)


if __name__ == "__main__":
    scrubFilesystem()
    # testMergeFunctionality()
    # findFractions()
    # updateScrubbedPatientDetailsWithFractions()
            