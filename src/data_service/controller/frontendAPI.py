from flask import request, Blueprint
from .service import getTrialList, \
                      getCenterList, \
                      getPatientList, \
                      getPatientInfo, \
                      updatePatientInfo, \
                      getFractionDetialByPatientId, \
                      updateFractionInfo, \
                      getPatientTrialStats, \
                      getMissingPrescriptionFieldCheck, \
                      getMissingFractionFieldCheck

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

@frontendAPI_blueprint.route('/api/getFractionDetialByPatientId', methods=['GET'])
def getFractionDetialByPatientIdFunction():
  return getFractionDetialByPatientId(request)

@frontendAPI_blueprint.route('/api/updateFractionInfo', methods=['PATCH'])
def updateFractionInfoFunction():
  return updateFractionInfo(request)

@frontendAPI_blueprint.route('/api/getPatientTrialStats', methods=['GET'])
def getPatientTrialStatsFunction():
  return getPatientTrialStats(request)

@frontendAPI_blueprint.route('/api/getMissingPrescriptionFieldCheck', methods=['GET'])
def getMissingPrescriptionFieldCheckFunction():
  return getMissingPrescriptionFieldCheck(request)

@frontendAPI_blueprint.route('/api/getMissingFractionFieldCheck', methods=['GET'])
def getMissingFractionFieldCheckFunction():
  return getMissingFractionFieldCheck(request)