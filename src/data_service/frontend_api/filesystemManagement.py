from flask import request, Blueprint
from .service.filesystem import getFolderList, moveFolder, deleteFolder, syncCloudDrive

filesystemManagement_blueprint = Blueprint('filesystemManagement', __name__)

@filesystemManagement_blueprint.route('/api/filesystem/getFolderList', methods=['GET'])
def getFolderListFunction():
  return getFolderList(request)

@filesystemManagement_blueprint.route('/api/filesystem/moveFolder', methods=['POST'])
def moveFolderFunction():
  return moveFolder(request)

@filesystemManagement_blueprint.route('/api/filesystem/deleteFolder', methods=['POST'])
def deleteFolderFunction():
  return deleteFolder(request)

@filesystemManagement_blueprint.route('/api/filesystem/syncCloudDrive', methods=['GET'])
def syncCloudDriveFunction():
  return syncCloudDrive(request)