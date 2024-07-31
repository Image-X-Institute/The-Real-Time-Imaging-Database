from flask import request, Blueprint
from .service.user import getUserList, registerUser, loginUser, changePassword



userManagement_blueprint = Blueprint('userManagement', __name__)

@userManagement_blueprint.route('/api/user/getUserList', methods=['GET'])
def getUserListFunction():
  return getUserList(request)

@userManagement_blueprint.route('/api/user/register', methods=['POST'])
def registerUserFunction():
  return registerUser(request)

@userManagement_blueprint.route('/api/user/login', methods=['POST'])
def loginUserFunction():
  return loginUser(request)

@userManagement_blueprint.route('/api/user/changePassword', methods=['POST'])
def changePasswordFunction():
  return changePassword(request)