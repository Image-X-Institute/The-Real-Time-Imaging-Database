from flask import request, Blueprint
from .service.util import getTrialList, getCenterList, getCenterDetailList, deleteCentre, deleteTrial
from .service.patient import getPatientTrialStats
from .service.general import addCentre, addTrial, getTrialStructure, getPatientInfoTemplate, getFractionInfoTemplate

generalApi_blueprint = Blueprint('generalApi', __name__)

@generalApi_blueprint.route('/api/getTrialList', methods=['GET'])
def getTrialListFunction():
  return getTrialList(request)

@generalApi_blueprint.route('/api/deleteTrial', methods=['DELETE'])
def deleteTrialFunction():
  return deleteTrial(request)

@generalApi_blueprint.route('/api/getCenterList', methods=['GET'])
def getCenterListFunction():
  return getCenterList(request)

@generalApi_blueprint.route('/api/getCenterDetailList', methods=['GET'])
def getCenterDetailListFunction():
  return getCenterDetailList(request)

@generalApi_blueprint.route('/api/deleteCentre', methods=['DELETE'])
def deleteCentreFunction():
  return deleteCentre(request)

@generalApi_blueprint.route('/api/getPatientTrialStats', methods=['GET'])
def getPatientTrialStatsFunction():
  return getPatientTrialStats(request)

@generalApi_blueprint.route('/api/addCentre', methods=['POST'])
def addCentreFunction():
  return addCentre(request)

@generalApi_blueprint.route('/api/addTrial', methods=['POST'])
def addTrialFunction():
  return addTrial(request)

@generalApi_blueprint.route('/api/getTrialStructure', methods=['GET'])
def getTrialStructureFunction():
  return getTrialStructure(request)

@generalApi_blueprint.route('/api/getPatientInfoTemplate', methods=['GET'])
def getPatientInfoTemplateFunction():
  return getPatientInfoTemplate(request)

@generalApi_blueprint.route('/api/getFractionInfoTemplate', methods=['GET'])
def getFractionInfoTemplateFunction():
  return getFractionInfoTemplate(request)