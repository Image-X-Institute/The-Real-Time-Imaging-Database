from flask import request, Blueprint
from .service.user import getUserList
userManagement_blueprint = Blueprint('userManagement', __name__)

@userManagement_blueprint.route('/api/user/getUserList', methods=['GET'])
def getUserListFunction():
  return getUserList(request)