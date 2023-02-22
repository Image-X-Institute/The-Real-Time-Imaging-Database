import csv
import readline
import re
import json


def convertToJSON(inputFilePath:str, outputJSONPath:str): 
    with open(inputFilePath, "r") as dicomTagsFile:
        tagsData = dicomTagsFile.read()

    tagRules = []
    for row in tagsData.split("\n"):
        tagRuleComponents = row.split("\t")
        if len(tagRuleComponents) < 3:
            continue

        tagRule = {"name": tagRuleComponents[0]}
        matches = re.search(r"\((.+?),(.+?)\)", tagRuleComponents[1])
        if matches:
            tagRule["group"] = matches.group(1)
            tagRule["element"] = matches.group(2)

        tagRule["action"] = "overwrite" if tagRuleComponents[2] == "w" else "delete"
        if tagRuleComponents[2] == "w":
            tagRule["overwrite_with"] = {
                "value_type": "pattern|fixed",
                "value": ""
            }
        tagRules.append(tagRule)

    anonymisationRules = {
                "metadata": {
                "name": "DICOM de-identification configuration file",
                "version": "0.1.0"
            },
            "tags": tagRules
    }

    with open(outputJSONPath, "w") as outputJSONFile:
        json.dump(anonymisationRules, outputJSONFile, indent=4)


if __name__ == "__main__":
    convertToJSON("dicom_anon_tags.tsv", "dicom_anonymisation_rules.json")
