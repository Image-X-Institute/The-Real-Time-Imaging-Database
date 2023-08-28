from typing import Dict, List, Tuple    # Type hinting
import re                               # regular Expressions
import json                             # JSON serialisation functionalities
import numpy as np
import sys                              # Command line arguments


class DVHParser:
    def __init__(self, filepath:str) -> None:
        self.dvhFilePath = filepath
        self.parsedDVH = {}

    def parse(self) -> Dict:
        """ Parse the DVH file and return a dictionary of values, including the 
        dose series. 
        
        While parsing, the following assumptions are made:
            * All key value pairs are seperated by a colon character
            * There are one or more "Structure" fields in the file
            * The dose value series always starts after a line break after the "Gradient Measure"
            * Each dose value series ends with an empty line (and there are no empty lines in between)

        """
        parsedDVH = {"header": {}, "structures":[]}
        if not self.isEciplseFormat():
            print(f"ERROR: Unsupported format: {self.dvhFilePath}")
            return None
        
        with open(self.dvhFilePath) as dvhFile:
            dvhFileLines = dvhFile.readlines()

        prevKey:str = ''
        currentStructure:str = None
        currentStructureValues = {}
        currentDoseValues = {}
        recordDoseValuesMode = False
        for line in dvhFileLines:

            if recordDoseValuesMode:
                if len(line.strip()) > 0:
                    doseValues = line.strip().split()
                    columnCounter = 0
                    for key in currentDoseValues.keys():
                        if columnCounter >= len(doseValues):
                            break
                        currentDoseValues[key].append(float(doseValues[columnCounter]))
                        columnCounter += 1
                else:
                    recordDoseValuesMode = False
                    currentStructureValues["dose values"] = currentDoseValues.copy()
            else:
                tokens = line.split(":")

                if len(tokens) > 1:
                    key = tokens[0].strip()
                    value = tokens[1].strip()

                    prevKey = key
                    if key == "Structure":
                        if currentStructure is not None:
                            parsedDVH["structures"].append(
                                                currentStructureValues.copy())
                            currentStructureValues = {}
                        currentStructure = key

                    if currentStructure is None:
                        parsedDVH["header"][key] = value
                    else:
                        currentStructureValues[key] = value

                elif len(line.strip()) > 0:
                    if prevKey == "Gradient Measure [cm]":
                        recordDoseValuesMode = True
                        doseHeadings = self._getDoseValueHeadings(line)
                        currentDoseValues = {} 
                        for heading in doseHeadings:
                            currentDoseValues[heading[2]] = []

        if len(currentStructure) > 0:
            parsedDVH["structures"].append(currentStructureValues)

        self.parsedDVH = parsedDVH
        self._standardiseDoseUnits()
        return parsedDVH

    def isEciplseFormat(self) -> bool:
        try:
            with open(self.dvhFilePath) as dvhFile:
                line = dvhFile.readline()
                if "Patient Name" in line and ":" in line:
                    return True
                else:
                    return False
        except UnicodeDecodeError as ex:
            print(f"ERROR: While trying to read {self.dvhFilePath} {ex}")
            return False
        return False

    def getAllStructureNames(self) -> List[str]:
        names = []
        if "structures" in self.parsedDVH:
            for structure in self.parsedDVH["structures"]:
                names.append(structure["Structure"])
        return names

    def getMeanDoseValueForStructure(self, structureName:str) -> float:
        meanDoseValue = None
        if "structures" in self.parsedDVH:
            for structure in self.parsedDVH["structures"]:
                if structure["Structure"] == structureName:
                    for key in structure.keys():
                        if re.match("Mean Dose [\S]*", key):  # "Mean Dose [%]"
                            meanDoseValue = structure[key]
        return meanDoseValue

    def _getDoseValueHeadings(self, line:str) -> List[Tuple[str, str, str]]:
        headings = []
        headingsWithUnits = line.strip().split("]")

        # the last element of the list is just an empty string beyond the last ']'
        for headingWithUnit in headingsWithUnits[:-1]:  
            headingAndUnit = headingWithUnit.strip().split("[")
            headings.append((headingAndUnit[0].strip(), headingAndUnit[1].strip(), 
                            f"{headingAndUnit[0].strip()} [{headingAndUnit[1].strip()}]"))

        return headings

    def _getUnitsForKey(self, keyName:str) -> str:
        """ The DVH file lists the units in the key name using square brackets.
        This function extracts the unit value from the key name and returns it.
        """
        keyComponents = keyName.strip().split("[")
        if len(keyComponents) > 1:
            unitComponents = keyComponents[1].strip().split("]")
            return unitComponents[0]
        return None

    def _convertPercentageValueToGray(self, percentValue:str, structureName:str) -> float:
        """ The DVH file may store the structure level dose values in either 
        absolute units (such as Gy or cGy) or in therms of percentages. To 
        convert the percentage values to the corresponding absolute Gray values,
        this function looks up the index of 100% value of the relative dose and
        then multiplies the percentage value provided with the amount listed in
        the dose column at the same index location and returns this value.  
        """
        assert self.parsedDVH, f"File {self.dvhFilePath} has not been parsed"
        for structure in self.parsedDVH["structures"]:
            if structure["Structure"] == structureName:
                doseValues = structure["dose values"]
                for doseKey in doseValues.keys():
                    if re.match("Relative dose[\S]*", doseKey):
                        matchingIndex = doseValues[doseKey].index(100)
                for doseKey in doseValues.keys():
                    if re.match("Dose[\S]*", doseKey):
                        matchingDose = doseValues[doseKey][matchingIndex]
                        if self._getUnitsForKey(doseKey) == "cGy":
                            matchingDose /= 100
                        convertedValue = matchingDose * (float(percentValue)/100)
                        return convertedValue
        return None  # It is an error if control comes to this statement

    def _standardiseDoseUnits(self):
        """This function converts all dose values listed in % to the equivalent
        Gy units
        """ 
        assert self.parsedDVH, f"File {self.dvhFilePath} has not been parsed"
        copyOfStructures = []
        for structure in self.parsedDVH["structures"]:
            copyOfStructure = structure.copy()
            for structKey in structure.keys():
                if re.match("[\S]* Dose [\S]*", structKey) or re.match("STD [\S]*", structKey):
                    if self._getUnitsForKey(structKey) == "%":
                        updatedKeyName = structKey.replace("%", "Gy")
                        copyOfStructure[updatedKeyName] = \
                             self._convertPercentageValueToGray(structure[structKey], 
                                                                structure["Structure"])
                        del(copyOfStructure[structKey])
                    elif self._getUnitsForKey(structKey) == "cGy":
                        updatedKeyName = structKey.replace("cGy", "Gy")
                        # print(f"structKey: {structKey}, value: {structure[structKey]}")
                        copyOfStructure[updatedKeyName] = float(structure[structKey])/100
                        del(copyOfStructure[structKey])
            copyOfStructures.append(copyOfStructure)
        self.parsedDVH["structures"] = copyOfStructures

    def computeDoseForPercentOfStructureVolume(self, structureName:str, percent:int) -> float:
        assert self.parsedDVH, f"File {self.dvhFilePath} has not been parsed"

        for structure in self.parsedDVH["structures"]:
            if structureName == structure["Structure"]:
                for doseKey in structure["dose values"].keys():
                    if re.match("Ratio of Total Structure Volume[\S]*", doseKey):
                        ratioOfTotalStructVolList = structure["dose values"][doseKey]
                    elif re.match("Dose[\S]*", doseKey):
                        doseValuesList = structure["dose values"][doseKey]
                        doseValuesUnits = self._getUnitsForKey(doseKey)
        if percent in ratioOfTotalStructVolList:
            # Since this list is ordered in descending order
            matchingIndex = len(ratioOfTotalStructVolList) - 1 \
                            - ratioOfTotalStructVolList[::-1].index(percent)
        else:
            ratioOfTotalStructVolArray = np.array(ratioOfTotalStructVolList)
            matchingIndex = (np.abs(ratioOfTotalStructVolArray - float(percent))).argmin()
        matchingDoseValue = doseValuesList[matchingIndex]

        if doseValuesUnits == "cGy":
            matchingDoseValue = matchingDoseValue/100
        
        return matchingDoseValue


def testParser(dvhFilePath:str):
    """ This is a test method included in the module for convenience and can be 
    moved to a seperate unit test file instead
    """
    # parser = DVHParser("X:/2RESEARCH/1_ClinicalData/SPARK/CMN/Dose Reconstruction/DVH/PAT02/PAT02CMN_Original.txt")
    # parser = DVHParser("X:/2RESEARCH/1_ClinicalData/SPARK/Liverpool/Dose Reconstructions/DVH/PAT2/1501033_K-Wrestored_R_Doserecon1_Frac3-WithKIM.dvh")
    parser = DVHParser(dvhFilePath)
    if not parser.isEciplseFormat():
        print("The DVH file format is not supported")
        return
    
    parsedContent = parser.parse()
    
    filename = dvhFilePath
    if '\\' in dvhFilePath:
        filename = dvhFilePath.split('\\')[-1]
    elif '/' in dvhFilePath:
        filename = dvhFilePath.split('/')[-1]
    
    extPosition = filename.rfind(".")
    jsonFileName = filename[:extPosition] + ".json"
    with open(jsonFileName, "w") as jsonDVHFile:
        json.dump(parsedContent, jsonDVHFile, indent=4)
    
    allStructures = parser.getAllStructureNames()
    print("Structures present in DVH:", allStructures)
    print("Structure       \tmean dose value\t D95\tD100")
    print("----------------\t---------------\t-------\t--------")
    for structure in allStructures:
        structureStr = structure
        if len(structureStr) < 16:
            structureStr += (16 - len(structureStr))*" "
        elif len(structureStr) > 16:
            structureStr = structureStr[:6] + "..."
        
        meanDose = str(parser.getMeanDoseValueForStructure(structure))
        d95Value = str(parser.computeDoseForPercentOfStructureVolume(structure, 95))
        d100Value = str(parser.computeDoseForPercentOfStructureVolume(structure, 100))

        structureStr = f"{structureStr}\t{meanDose}" + (16 - len(meanDose))*" "
        structureStr = structureStr + d95Value + (8 - len(d95Value))*" "
        structureStr = structureStr + d100Value + (8 - len(d100Value))*" "
        print (structureStr)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <File path of DVH file>")
        sys.exit(1)
    
    testParser(sys.argv[1])
