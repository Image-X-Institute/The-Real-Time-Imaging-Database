from flask import make_response
from .util import executeQuery
from AccessManager import addSiteTrial, addTrialStructure
import json

def addCentre(request):
  centreData = request.json
  if not centreData:
    return make_response({'message': 'No centre data provided.'}, 400)
  try:
    centreData['type'] = 'site'
    result = addSiteTrial(centreData)
    if result[0]:
      return make_response({'message': 'Centre added successfully.'}, 201)
    else:
      return make_response({'message': result[1]}, 400)
  except Exception as err:
    return make_response({'message': 'An error occurred while adding the centre.'}, 400)
  
def addTrial(request):
  trialData = request.json
  if not trialData:
    return make_response({'message': 'No trial data provided.'}, 400)

  result = addTrialStructure(trialData)
  if result[0]:
    return make_response({'message': 'Trial added successfully.'}, 201)
  else:
    return make_response({'message': result[1]}, 400)
  
def getTrialStructure(request):
  trialName = request.args.get('trialName')
  if not trialName:
    return make_response({'message': 'Trial name not provided.'}, 400)
  
  if trialName == 'Template':
    with open('resources/template.json') as f:
      trialStructure = json.load(f)
    return make_response({'trialStructure': trialStructure}, 200)

  
  sqlStmt = f"SELECT trial_structure FROM trials WHERE trial_name='{trialName}'"
  result = executeQuery(sqlStmt, authDB=True)
  if not result:
    return make_response({'message': 'Trial structure not found.'}, 404)
  return make_response({'trialStructure': result[0][0]}, 200)


def getPatientInfoTemplate(request):
  with open('resources/patient_info_template.csv') as f:
    patientInfoTemplate = f.read()
  return make_response({'patientInfoTemplate': patientInfoTemplate}, 200)

def getFractionInfoTemplate(request):
  with open('resources/patient_fraction_template.csv') as f:
    fractionInfoTemplate = f.read()
  return make_response({'fractionInfoTemplate': fractionInfoTemplate}, 200)