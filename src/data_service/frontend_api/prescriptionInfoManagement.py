from flask import request, Blueprint
from .service.prescription import getMissingPrescriptionFieldCheck, getUpdatePrescriptionField, \
  updatePrescriptionField, exportPrescriptionCsv, syncPrescriptionCsv
from .service.patient import updatePatientInfo

prescriptionInfo_blueprint = Blueprint('prescriptionInfo', __name__)


@prescriptionInfo_blueprint.route('/api/prescription/getMissingPrescriptionFieldCheck', methods=['GET'])
def getMissingPrescriptionFieldCheckFunction():
  return getMissingPrescriptionFieldCheck(request)

@prescriptionInfo_blueprint.route('/api/prescription/updatePatientInfo', methods=['PATCH'])
def updatePatientInfoFunction():
  return updatePatientInfo(request)

@prescriptionInfo_blueprint.route('/api/prescription/getUpdatePrescriptionField', methods=['GET'])
def getUpdatePrescriptionFieldFunction():
  return getUpdatePrescriptionField(request)

@prescriptionInfo_blueprint.route('/api/prescription/updatePrescriptionField', methods=['PATCH'])
def updatePrescriptionFieldFunction():
  return updatePrescriptionField(request)

@prescriptionInfo_blueprint.route('/api/prescription/exportPrescriptionCsv', methods=['GET'])
def exportPrescriptionCsvFunction():
  return exportPrescriptionCsv(request)

@prescriptionInfo_blueprint.route('/api/prescription/syncPrescriptionCsv', methods=['POST'])
def syncPrescriptionCsvFunction():
  return syncPrescriptionCsv(request)