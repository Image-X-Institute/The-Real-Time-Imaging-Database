from flask import request, Blueprint
from .service.patient import getPatientIdList, getPatientInfo, addOnePatient, addBulkPatient, getPatientDetailList, deleteOnePatient

patientInfo_blueprint = Blueprint('patientInfo', __name__)


@patientInfo_blueprint.route('/api/patient/getPatientIdList', methods=['GET'])
def getPatientIdListFunction():
  return getPatientIdList(request)

@patientInfo_blueprint.route('/api/patient/getPatientInfo', methods=['GET'])
def getPatinetInfoFunction():
  return getPatientInfo(request)

@patientInfo_blueprint.route('/api/patient/addOnePatient', methods=['POST'])
def addOneFunction():
  return addOnePatient(request)

@patientInfo_blueprint.route('/api/patient/addBulkPatient', methods=['POST'])
def addBulkFunction():
  return addBulkPatient(request)

@patientInfo_blueprint.route('/api/patient/getPatientDetailList', methods=['GET'])
def getPatientDetailListFunction():
  return getPatientDetailList(request)

@patientInfo_blueprint.route('/api/patient/deleteOnePatient', methods=['POST'])
def deleteOnePatientFunction():
  return deleteOnePatient(request)