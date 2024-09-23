from flask import request, Blueprint
from .service.fraction import getFractionDetailByPatientId, updateFractionInfo, \
  getMissingFractionFieldCheck, getUpdateFractionField, \
    updateFractionField, addNewFraction, addBulkFraction \
  , getFractionListByPatientId, deleteFraction

fractionInfo_blueprint = Blueprint('fractionInfo', __name__)

@fractionInfo_blueprint.route('/api/fraction/getFractionDetailByPatientId', methods=['GET'])
def getFractionDetailByPatientIdFunction():
  return getFractionDetailByPatientId(request)

@fractionInfo_blueprint.route('/api/fraction/getFractionListByPatientId', methods=['GET'])
def getFractionListByPatientIdFunction():
  return getFractionListByPatientId(request)

@fractionInfo_blueprint.route('/api/fraction/updateFractionInfo', methods=['PATCH'])
def updateFractionInfoFunction():
  return updateFractionInfo(request)

@fractionInfo_blueprint.route('/api/fraction/getMissingFractionFieldCheck', methods=['GET'])
def getMissingFractionFieldCheckFunction():
  return getMissingFractionFieldCheck(request)

@fractionInfo_blueprint.route('/api/fraction/getUpdateFractionField', methods=['GET'])
def getUpdateFractionFieldFunction():
  return getUpdateFractionField(request)

@fractionInfo_blueprint.route('/api/fraction/updateFractionField', methods=['PATCH'])
def updateFractionFieldFunction():
  return updateFractionField(request)

@fractionInfo_blueprint.route('/api/fraction/addNewFraction', methods=['POST'])
def addNewFractionFunction():
  return addNewFraction(request)

@fractionInfo_blueprint.route('/api/fraction/addBulkFraction', methods=['POST'])
def addBulkFractionFunction():
  return addBulkFraction(request)

@fractionInfo_blueprint.route('/api/fraction/deleteFraction', methods=['DELETE'])
def deleteFractionFunction():
  return deleteFraction(request)