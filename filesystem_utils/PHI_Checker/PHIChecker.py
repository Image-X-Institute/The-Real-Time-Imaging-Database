from distutils import extension
from genericpath import isdir, isfile
from time import sleep
import pydicom as dcm
import argparse
import os
import magic
from typing import List, Tuple
import csv


def getValuesForTags(ds:dcm.Dataset, tags:List[str]) -> List[Tuple]:
    tagValues = []
    for tag in tags:
        if tag in ds:
            de:dcm.DataElement = ds.data_element(tag)
            tagValues.append((tag,"Not Present" if de is None else str(de.value)))
        else:
            tagValues.append((tag,"Not Present"))
    return tagValues


def getExtFromFilename(filename: str) -> str:
    extensionPos = filename.rfind('.')
    extension = ''
    if extensionPos != -1:
        extension = filename[extensionPos + 1:].lower()
    return extension


def findAndCheckDICOMFilesCustom(path, outputPath, overwriteOutPut=False, 
                ignoreDirectories=["KIM-KV", "KIM-MV", ".AppleDouble"]):
    expectedMIMEType = "application/dicom"
    ignoreExtensions = ["txt", "xls", "xlsx", "jpg", "jpeg", "png", "fig",
                        "log", "dvh", "tif", "tiff", "his", "doc", "bin",
                        "xml", "db", "DS_Store", "csv", "mat", "zip"]
    tagsToCheck = ["PatientID", "PatientName", "PatientBirthDate", "PatientSex",
                    "PatientBirthDate", "OtherPatientIDs", "PatientSize", 
                    "AccessionNumber", "InstitutionName", "InstitutionAddress", 
                    "ReferringPhysicianName"]
    heading = ["DICOM File"] + tagsToCheck

    if not os.path.isdir(path):
        if not os.path.isfile(path) or not expectedMIMEType == magic.from_file(path, mime=True):
            print(f"{path} is not a DICOM file")
            return

    if os.path.isfile(outputPath) and not overwriteOutPut:
        userChoice = input(f"{outputPath} already exists. Overwrite? [Y/n]")
        if userChoice not in ["Y", "y", "yes"]:
            print(f"Not overwriting existing {outputPath}. Please provide a different output path.")
            return

    with open(outputPath, 'w', encoding="UTF8") as outputFile:
        csvwriter = csv.writer(outputFile)
        csvwriter.writerow(heading)  

        dirsToProcess = [path]
        while dirsToProcess:
            for p in dirsToProcess:
                files = []
                # subDirs = [p + '/' + d for d in os.listdir(p) \
                #         if os.path.isdir(p + '/' + d) and d not in ignoreDirectories]
                subDirs = []
                for fsElement in os.listdir(p):
                    if os.path.isdir(p + '/' + fsElement) and fsElement not in ignoreDirectories:
                        subDirs.append(p + '/' + fsElement)

                    if os.path.isfile(p + '/' + fsElement):
                        if getExtFromFilename(fsElement) not in ignoreExtensions:
                            files.append(p + '/' + fsElement)
                
                dirsToProcess.remove(p)
                dirsToProcess.extend(subDirs)
                
                if len(files) >= 1:
                    print(f"\nChecking {len(files)} files in {p}")
                else:
                    print('.', end='', flush=True)
                
                for filePath in files:
                    if expectedMIMEType == magic.from_file(filePath, mime=True):
                        print(f"\tProcessing {filePath}", flush=True)
                        ds:dcm.FileDataset = dcm.dcmread(filePath)
                        values = getValuesForTags(ds, tagsToCheck)
                        result = [v[1] for v in values]
                        result.insert(0, os.path.relpath(filePath, path))
                        csvwriter.writerow(result)
                        outputFile.flush()
                    else:
                        print(f"\tIgnoring {filePath} as it is not DICOM")


def findAndCheckDICOMFiles(path, outputPath, overwriteOutPut=False):
    expectedMIMEType = "application/dicom"
    tagsToCheck = ["PatientID", "PatientName", "PatientBirthDate", "PatientSex",
                    "PatientBirthDate", "OtherPatientIDs", "PatientSize", 
                    "AccessionNumber", "InstitutionName", "InstitutionAddress", 
                    "ReferringPhysicianName"]
    heading = ["DICOM File"] + tagsToCheck
    # results = [heading]

    if not os.path.isdir(path):
        if not os.path.isfile(path) or not expectedMIMEType == magic.from_file(path, mime=True):
            print(f"{path} is not a DICOM file")
            return

    if os.path.isfile(outputPath) and not overwriteOutPut:
        userChoice = input(f"{outputPath} already exists. Overwrite? [Y/n]")
        if userChoice not in ["Y", "y", "yes"]:
            print(f"Not overwriting existing {outputPath}. Please provide a different output path.")
            return

    with open(outputPath, 'w', encoding="UTF8") as outputFile:
        csvwriter = csv.writer(outputFile)
        csvwriter.writerow(heading)  

        for dirpath, dirnames, filenames in os.walk(path):
            currentDir = os.path.dirname(dirpath)
            ignoreDirectories = ["KIM-KV", "KIM-MV"]
            if currentDir in ignoreDirectories:
                continue
            for filename in filenames:
                extensionPos = filename.rfind('.')
                if extensionPos != -1:
                    extension = filename[extensionPos + 1:].lower()
                    ignoreExtensions = ["txt", "xls", "xlsx", "jpg", "jpeg", 
                                        "png", "fig", "doc", "log", "dvh", 
                                        "tif", "tiff", "his", "xml", "db", 
                                        "DS_Store", "csv", "mat", "bin", "zip"]
                    if extension in ignoreExtensions:
                        continue  # look at the next file in the directory
                print(".", end="")
                fullPath = os.path.join(dirpath, filename)
                if expectedMIMEType == magic.from_file(fullPath, mime=True):
                    print("Processing DICOM file:", os.path.relpath(fullPath, path))
                    ds:dcm.FileDataset = dcm.dcmread(fullPath)
                    values = getValuesForTags(ds, tagsToCheck)
                    result = [v[1] for v in values]
                    result.insert(0, os.path.relpath(fullPath, path))
                    csvwriter.writerow(result)
                    outputFile.flush()
            sleep(0.5)  # pause for half a second to avoid too many I/O calls on RDS


def prepareArgumentParser():
    argParser = argparse.ArgumentParser(description="DICOM PHI Checker")
    
    argParser.add_argument("-o", "--output", dest="output", type=str,
                            default="results.csv",
                            help="Name of the output CSV file containing PHI check results")

    argParser.add_argument("-f", "--force-overwrite-output", dest="forceOverwrite", 
                            action="store_true", default=False,
                            help="Overwrite the output file if it exists")

    argParser.add_argument("path", help="The top level path for checking")
    
    return argParser


def main():
    argParser = prepareArgumentParser()
    args = argParser.parse_args()
    # findAndCheckDICOMFiles(args.path, args.output, args.forceOverwrite)
    findAndCheckDICOMFilesCustom(args.path, args.output, args.forceOverwrite)


if __name__ == "__main__":
    main()
