import os
from flask import make_response
import config
import shutil
import subprocess

def create_folder_structure_json(path): 
    # Initialize the result dictionary with folder 
    # name, type, and an empty list for children 
    result = {
                'title': os.path.basename(path), 
                'key': path,
                'children': []
              }
  
    # Check if the path is a directory 
    if not os.path.isdir(path): 
        return result 
  
    # Iterate over the entries in the directory 
    for entry in os.listdir(path): 
       # Create the full path for the current entry 
        entry_path = os.path.join(path, entry) 
  
        # If the entry is a directory, recursively call the function 
        if os.path.isdir(entry_path): 
            result['children'].append(create_folder_structure_json(entry_path)) 
    return result 

def getFolderList(req):
  try:
    folderList = create_folder_structure_json(config.CLOUD_DRIVE_FOLDER)
    return make_response({"treeData":[folderList]}, 200)
  except:
    return make_response({"message": "Internal Server Error"}, 500)

def moveFolder(req):
  payload = req.json
  sourceList = payload["source"]
  for source in sourceList:
    destination = source.replace(config.CLOUD_DRIVE_FOLDER, config.DATA_FILESYSTEM_ROOT)
    shutil.copytree(source, destination, dirs_exist_ok=True)
  return make_response({"message": "ok"}, 200)

def deleteFolder(req):
  payload = req.json
  sourceList = payload["source"]
  for source in sourceList:
    shutil.rmtree(source)
  return make_response({"message": "ok"}, 200)

def syncCloudDrive(req):
  #  Update the onedrive folder with the latest data from the filesystem
  subprocess.run(['onedrive', '--synchronize', '--download-only'], check=True, text=True)
  return make_response({"message": "ok"}, 200)
