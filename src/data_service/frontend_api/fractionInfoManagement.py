from flask import request, Blueprint
from .service.fraction import getFractionDetialByPatientId, updateFractionInfo, getMissingFractionFieldCheck, getUpdateFractionField, updateFractionField

fractionInfo_blueprint = Blueprint('fractionInfo', __name__)

@fractionInfo_blueprint.route('/api/fraction/getFractionDetialByPatientId', methods=['GET'])
def getFractionDetialByPatientIdFunction():
  return getFractionDetialByPatientId(request)

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