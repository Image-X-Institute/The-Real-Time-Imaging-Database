from .util import executeQuery
from flask import make_response
import sys

def getUserList(request):
  try:
    sqlStmt = "SELECT * FROM token_details"
    result = executeQuery(sqlStmt, withDictCursor=True, authDB=True)
    return make_response(result)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({'message': 'An error occurred while fetching user details.'}, 400)