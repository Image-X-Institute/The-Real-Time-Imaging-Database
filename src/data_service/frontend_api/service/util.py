from dbconnector import DBConnector
import config
import psycopg2 as pg
import psycopg2.extras
import sys
from AccessManager import getSites, getTrials
from flask import make_response

def executeQuery(queryStmt:str, withDictCursor:bool=False, authDB=False):
  if authDB:
    connector = DBConnector(config.AUTH_DB_NAME, 
                            config.AUTH_DB_USER, 
                            config.AUTH_DB_PASSWORD,
                            config.AUTH_DB_HOST)
  else:
    connector = DBConnector(config.DB_NAME, 
                            config.DB_USER, 
                            config.DB_PASSWORD,
                            config.DB_HOST)
  connector.connect()
  conn = connector.getConnection()

  fetchedRows = None
  try:
    if withDictCursor:
      cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
      cur.execute(queryStmt)
      fetchedRows = cur.fetchall()
      colName = [desc[0] for desc in cur.description]
      fetchedRows = [dict(zip(colName, row)) for row in fetchedRows]
    else:
      cur = conn.cursor()
      cur.execute(queryStmt)
      conn.commit()
      fetchedRows = cur.fetchall()
    cur.close()
  except (Exception, pg.DatabaseError) as err:
    print(err, file=sys.stderr)
  return fetchedRows

def getTrialList(req):
  trials = getTrials()
  trials = {"trials": [trial.name for trial in trials], "trialDetails": trials}
  rsp = make_response(trials)
  return rsp

def deleteTrial(req):
  trialName = req.json['trialName']
  if not trialName:
    return make_response({'message': 'trialName is required.'}, 400)
  try:
    sqlStmt = f"DELETE FROM trials WHERE trial_name='{trialName}'"
    executeQuery(sqlStmt, authDB=True)
    return make_response({'message': 'Trial deleted successfully.'}, 200)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({'message': 'An error occurred while deleting trial.'}, 400)

def getCenterList(req):
  sites = getSites()
  sites = {"sites": [site.name for site in sites]}
  rsp = make_response(sites)
  return rsp

def getCenterDetailList(req):
  sqlStmt = "SELECT * FROM treatment_sites"
  fetchedRows = executeQuery(sqlStmt, withDictCursor=True, authDB=True)
  returnPack = []
  for row in fetchedRows:
    sitePack = {
      "siteName": row['site_name'],
      "siteFullName": row['site_full_name'],
      "siteLocation": row['site_location'],
    }
    returnPack.append(sitePack)
  return make_response({"sites": returnPack}, 200)

def deleteCentre(req):
  siteName = req.json['siteName']
  if not siteName:
    return make_response({'message': 'siteName is required.'}, 400)
  try:
    sqlStmt = f"DELETE FROM treatment_sites WHERE site_name='{siteName}'"
    executeQuery(sqlStmt, authDB=True)
    return make_response({'message': 'Site deleted successfully.'}, 200)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({'message': 'An error occurred while deleting site.'}, 400)