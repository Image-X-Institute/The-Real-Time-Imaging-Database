import re
import os
import sys


def findFolderContainingFiles(filenamePattern:str, searchPathRoot:str):
    for dirpath, dirnames, filenames in os.walk(searchPathRoot):
        for filename in filenames:
            if re.match(filenamePattern, filename):
                print(f"Found: {dirpath}")
                break


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Please provide the search pattern and search path for searching")
        sys.exit()

    print(f"Searching for folders containing {sys.argv[1]} under {sys.argv[2]}")
    findFolderContainingFiles(sys.argv[1], sys.argv[2])