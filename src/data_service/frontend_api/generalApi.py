from flask import request, Blueprint
from .service.util import getTrialList, getCenterList
from .service.patient import getPatientTrialStats
from .service.general import addCentre, addTrial, getTrialStructure

generalApi_blueprint = Blueprint('generalApi', __name__)

@generalApi_blueprint.route('/api/getTrialList', methods=['GET'])
def getTrialListFunction():
  return getTrialList(request)

@generalApi_blueprint.route('/api/getCenterList', methods=['GET'])
def getCenterListFunction():
  return getCenterList(request)

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
