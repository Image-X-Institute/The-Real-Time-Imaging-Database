import os
import zipfile
import time
import argparse


def findAndExpandCompressedFiles(rootPath, deleteUnzippedFiles=False,
                                    excludeFilesWithNameContaining="_done"):
    """ Searches a given folder and sub folders and finds any files with .zip 
        in the file name and uncompresses them in the  same folder where they 
        were found. In case the deleteUnzippedFiles argument is set to True, 
        the processed files would be deleted after unzipping.
    """
    assert os.path.isdir(rootPath), f"The path {rootPath} is not accessible"

    for dirpath, dirnames, filenames in os.walk(rootPath):
        for filename in filenames:
            if (".zip" in filename) and \
                    (deleteUnzippedFiles or \
                         (excludeFilesWithNameContaining not in filename)):
                fullFilePath = os.path.join(dirpath, filename)
                print(f"Extracting from {fullFilePath}", end=" ", flush=True)
                try:
                    with zipfile.ZipFile(fullFilePath, "r") as compressedFile:
                        for zipFileInfo in compressedFile.infolist():
                            compressedFile.extract(zipFileInfo, dirpath)
                            date_time = time.mktime(zipFileInfo.date_time + (0, 0, -1))
                            os.utime(
                                    os.path.join(dirpath, zipFileInfo.filename), 
                                    (date_time, date_time))
                            print('.', end='', flush=True)
                except zipfile.BadZipFile as badZipException:
                    print(f"Failed\n\t{fullFilePath}: {badZipException}")
                else:
                    if deleteUnzippedFiles:
                        os.remove(os.path.join(dirpath, filename))
                    else:
                        lastDotPos = filename.rfind('.')
                        if lastDotPos != -1:
                            modifiedFilename = filename[:lastDotPos] \
                                                + excludeFilesWithNameContaining \
                                                + filename[lastDotPos:]

                            os.rename(os.path.join(dirpath, filename),
                                        os.path.join(dirpath, modifiedFilename))
                    print(" Done")


def prepareArgumentParser():
    argParser = argparse.ArgumentParser(description="Recursively find and "
                                                "extract compressed files")

    argParser.add_argument("--delete", dest="deleteProcessedFiles", 
                            help="Delete the compressed files after they have "
                                "been successfully processed", 
                            action="store_true")
    
    argParser.add_argument("--done-suffix", dest="doneSuffix", 
                            help="Add a suffix to a file name after it is processed", 
                            type=str, default="_done")

    argParser.add_argument("path", help="The top level folder for finding files")

    return argParser


if __name__ == "__main__":
    argParser = prepareArgumentParser()
    args = argParser.parse_args()
    findAndExpandCompressedFiles(args.path, 
                                deleteUnzippedFiles=args.deleteProcessedFiles,
                                excludeFilesWithNameContaining=args.doneSuffix)

