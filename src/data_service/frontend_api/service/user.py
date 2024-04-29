from .util import executeQuery
from flask import make_response
import sys
import hashlib
from flask_jwt_extended import create_access_token

def getUserList(request):
  try:
    sqlStmt = "SELECT * FROM token_details"
    result = executeQuery(sqlStmt, withDictCursor=True, authDB=True)
    return make_response(result, 200)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({'message': 'An error occurred while fetching user details.'}, 400)
  
def registerUser(request):
  try:
    userData = request.json
    if not userData:
      return make_response({'message': 'No user data provided.'}, 400)
    
    # Check if the user already exists
    sqlStmt = f"SELECT * FROM token_details WHERE subject_email='{userData['email']}'"
    result = executeQuery(sqlStmt, withDictCursor=True, authDB=True)
    print(sqlStmt, result, file=sys.stderr)
    if result:
      return make_response({'message': 'User already exists.'}, 400)
    
    # Encrypt the password
    userData['password'] = hashlib.md5(userData['password'].encode()).hexdigest()

    # Insert the user data
    sqlStmt = f"INSERT INTO token_details (token_subject, subject_email, hashed_secret, access_level) VALUES ('{userData['username']}', '{userData['email']}', '{userData['password']}', '2')"
    executeQuery(sqlStmt, authDB=True)

    # Generaate Token
    tokenPack = {
      'username': userData['username'],
      'email': userData['email'],
      'access_level': 2
    }
    token = create_access_token(identity=tokenPack)

    return make_response({'username':userData['username'], 'token': token, 'access_level':2}, 201)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({'message': 'An error occurred while registering the user.'}, 400)
  
def loginUser(request):
  try:
    userData = request.json
    if not userData:
      return make_response({'message': 'No user data provided.'}, 400)
    
    # Check if the user exists
    sqlStmt = f"SELECT * FROM token_details WHERE subject_email='{userData['email']}'"
    result = executeQuery(sqlStmt, withDictCursor=True, authDB=True)
    if not result:
      return make_response({'message': 'User does not exist.'}, 400)
    
    # Check if the password is correct
    userData['password'] = hashlib.md5(userData['password'].encode()).hexdigest()
    if result[0]['hashed_secret'] != userData['password']:
      return make_response({'message': 'Incorrect password.'}, 400)
    
    # Generate Token
    tokenPack = {
      'username': result[0]['token_subject'],
      'email': result[0]['subject_email'],
      'access_level': result[0]['access_level']
    }
    token = create_access_token(identity=tokenPack)

    return make_response({'username':result[0]['token_subject'], 'token': token, 'access_level':result[0]['access_level']}, 200)
  except Exception as err:
    print(err, file=sys.stderr)
    return make_response({'message': 'An error occurred while logging in.'}, 400)