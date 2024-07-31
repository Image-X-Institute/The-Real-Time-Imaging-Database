from flask import request, Blueprint
from .service.patient import getPatientList, getPatientInfo, addOnePatient, addBulkPatient

patientInfo_blueprint = Blueprint('patientInfo', __name__)


@patientInfo_blueprint.route('/api/patient/getPatientList', methods=['GET'])
def getPatientListFunction():
  return getPatientList(request)

@patientInfo_blueprint.route('/api/patient/getPatientInfo', methods=['GET'])
def getPatinetInfoFunction():
  return getPatientInfo(request)

@patientInfo_blueprint.route('/api/patient/addOnePatient', methods=['POST'])
def addOneFunction():
  return addOnePatient(request)

@patientInfo_blueprint.route('/api/patient/addBulkPatient', methods=['POST'])
def addBulkFunction():
  return addBulkPatient(request)