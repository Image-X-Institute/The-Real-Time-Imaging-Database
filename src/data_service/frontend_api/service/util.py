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
  trials = {"trials": [trial.name for trial in trials]}
  rsp = make_response(trials)
  return rsp

def getCenterList(req):
  sites = getSites()
  sites = {"sites": [site.name for site in sites]}
  rsp = make_response(sites)
  return rsp