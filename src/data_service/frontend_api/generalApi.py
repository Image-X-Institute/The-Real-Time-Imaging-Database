from flask import request, Blueprint
from .service.util import getTrialList, getCenterList
from .service.patient import getPatientTrialStats

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


