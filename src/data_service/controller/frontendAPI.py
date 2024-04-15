from flask import request, Blueprint
from .service import getTrialList, getCenterList, getPatientList, getPatientInfo, updatePatientInfo

frontendAPI_blueprint = Blueprint('frontendAPI', __name__)

@frontendAPI_blueprint.route('/api/getTrialList', methods=['GET'])
def getTrialListFunction():
  return getTrialList(request)

@frontendAPI_blueprint.route('/api/getCenterList', methods=['GET'])
def getCenterListFunction():
  return getCenterList(request)

@frontendAPI_blueprint.route('/api/getPatientList', methods=['GET'])
def getPatientListFunction():
  return getPatientList(request)

@frontendAPI_blueprint.route('/api/getPatientInfo', methods=['GET'])
def getPatinetInfoFunction():
  return getPatientInfo(request)

@frontendAPI_blueprint.route('/api/updatePatientInfo', methods=['PATCH'])
def updatePatientInfoFunction():
  return updatePatientInfo(request)