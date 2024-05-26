from flask import make_response
from .util import executeQuery
import sys
import config
import os
import re
from AccessManager import addSiteTrial, addTrialStructure

def addCentre(request):
  centreData = request.json
  if not centreData:
    return make_response({'message': 'No centre data provided.'}, 400)
  
  centreData['type'] = 'site'
  result = addSiteTrial(centreData)
  if result[0]:
    return make_response({'message': 'Centre added successfully.'}, 201)
  else:
    return make_response({'message': result[1]}, 400)
  
def addTrial(request):
  trialData = request.json
  if not trialData:
    return make_response({'message': 'No trial data provided.'}, 400)

  result = addTrialStructure(trialData)
  if result[0]:
    return make_response({'message': 'Trial added successfully.'}, 201)
  else:
    return make_response({'message': result[1]}, 400)
  