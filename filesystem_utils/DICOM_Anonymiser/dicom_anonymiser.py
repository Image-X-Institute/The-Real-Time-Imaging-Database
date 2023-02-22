from errno import EINVAL
from genericpath import isdir, isfile
from operator import ge
import sys
import pydicom as dcm
import argparse
from typing import Dict
import os
import magic
import json
import re


def _getResourcePath(relativePath:str) -> str:
    return os.path.join(
        os.environ.get(
            "_MEIPASS2",
            os.path.abspath(".")
        ),
        relativePath
    )


def getDefaultDeIdentificationConfig() -> Dict:
    # The following anonymization configuration is based on the publication:
    #  
    # Newhauser W, Jones T, Swerdloff S, et al. Anonymization of DICOM 
    # electronic medical records for radiation therapy. Comput Biol Med. 
    # 2014;53:134-140. doi:10.1016/j.compbiomed.2014.07.010
    try:
        basePath = sys._MEIPASS  # created by pyinstaller
    except Exception:
        basePath = os.path.abspath(".")
    defaultConfigFilePath = os.path.join(basePath, 
                                    "dicom_anonymisation_rules_default.json")
    
    with open(defaultConfigFilePath, "r") as DefaultConfigFile:
        defaultConfig = json.load(DefaultConfigFile)
    return defaultConfig


def resolvePattern(pattern:str, variables:Dict[str, str]) -> str:
    ...


def anonymise(filePath:str, 
                deIdentificationConfig:Dict,
                overwriteFile=False, 
                verbose=False,
                showProgress=True,
                variables:Dict={}) -> int:

    numberOfFileAnonymised = 0
    if os.path.isdir(filePath):
        for subpath in os.listdir(filePath):
            numberOfFileAnonymised += anonymise(filePath + '/' + subpath, 
                                                deIdentificationConfig,
                                                overwriteFile,
                                                verbose,
                                                showProgress,
                                                variables)
    elif os.path.isfile(filePath) and \
            "application/dicom" == magic.from_file(filePath, mime=True):
        ds:dcm.FileDataset = dcm.dcmread(filePath)
        if verbose:
            print(f"Processing {filePath} for anonymisation")
        for tagToBeAnonymised in deIdentificationConfig["tags"]:
            dicomTag = (int(tagToBeAnonymised["group"], base=16), 
                        int(tagToBeAnonymised["element"], base=16)) 
            tagValue = "<not present>"
            if dicomTag in ds:
                tagValue = str(ds[dicomTag].value)
                if tagToBeAnonymised["action"] == "delete":
                    del ds[dicomTag]
                elif tagToBeAnonymised["action"] == "overwrite":
                    if "overwrite_with" not in tagToBeAnonymised:
                        print("Invalid dicom anonymisation configuration: " \
                            + f"{tagToBeAnonymised['name']} is meant to be " \
                            + "overwritten but no overwrite details present",
                            file=sys.stderr)
                    else:
                        if tagToBeAnonymised["overwrite_with"]["value_type"] == "fixed":
                            ds[dicomTag].value = tagToBeAnonymised["overwrite_with"]["value"]
                        elif tagToBeAnonymised["overwrite_with"]["value_type"] == "pattern":
                            patternStr = tagToBeAnonymised["overwrite_with"]["value"]
                            matches = re.search("{(.+?)}", patternStr)
                            anonTagValue = ""
                            if matches:
                                for match in matches.groups():
                                    if isinstance(match, str):
                                        if match in variables:
                                            anonTagValue += variables[match]
                            ds[dicomTag].value = anonTagValue

                if verbose:
                    print(f" Anonymising {tagToBeAnonymised['name']} ",
                            f"with action \"{tagToBeAnonymised['action']}\" ",
                            f"(original value: {tagValue})")
        if overwriteFile:
            ds.save_as(filePath)
        else:
            fileNameComponents = os.path.splitext(filePath)
            outputFileName = fileNameComponents[0] + "_anon" 
            if len(fileNameComponents) > 1:
                outputFileName = outputFileName + fileNameComponents[1]
            ds.save_as(outputFileName)
        
        numberOfFileAnonymised += 1
        if showProgress:
            print(".", end="")

    return numberOfFileAnonymised


def prepareArgumentParser():
    argParser = argparse.ArgumentParser(description="DICOM anonymisation tool")

    argParser.add_argument("--config", dest="anonymisationConfig", 
                            help="Configuration file with dicom anonymisation "
                                "rules (expected in JSON format)", type=str)

    argParser.add_argument("--trailid", dest="trailId", 
                            help="An acronym for the clinical trail or an ID", 
                            type=str)

    argParser.add_argument("--patid", dest="patientId", 
                            help="The patient ID to be used after anonymisation", 
                            type=str)

    argParser.add_argument("-w", "--overwrite", dest="overwrite", 
                            help="Overwrite the original file while anonymising",
                            action="store_true", default=False)

    argParser.add_argument("-v", "--verbose", dest="verbose", 
                            help="print verbose details to output",
                            action="store_true", default=False)

    argParser.add_argument("--progress", dest="progress", 
                            help="print a dot for every file processed",
                            action="store_true", default=False)

    argParser.add_argument("path", help="DICOM file or folder path to be anonymised")
    

    return argParser


def main():
    argParser = prepareArgumentParser()
    args = argParser.parse_args()
    anonConfig = args.anonymisationConfig if args.anonymisationConfig \
                                    else getDefaultDeIdentificationConfig()
    variables = {}
    if args.trailId:
        variables["trialId"] = args.trialId
    if args.patientId:
        variables["patientId"] = args.patientId
    
    numAnon = anonymise(args.path, 
                        anonConfig,
                        overwriteFile=args.overwrite, 
                        verbose=args.verbose,
                        showProgress=args.progress,
                        variables=variables)

    print(f"Anonymised {numAnon} file(s)")
    if args.progress:
        print(" done")


if __name__ == "__main__":
    main()
