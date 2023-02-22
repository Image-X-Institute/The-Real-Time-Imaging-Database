from flask import request, redirect
import functools
from typing import NamedTuple, List, Tuple
from datetime import datetime, timedelta
import random
import string
from DatabaseAdapter import DatabaseAdapter


class SessionInfo(NamedTuple):
    id: str
    expires: datetime
    peer_addr: str
    userId: str


def autheticated_access(func):
    """ Decorator function, to be used on routes that need to be protected 
    with an authenticated access mechanism.
    """
    @functools.wraps(func)
    def wrapper_decorator(*args, **kwargs):
        sessionId = request.cookies.get("session")
        if sessionId and authManagerInstance.checkSessionValidity(sessionId):
            return func(*args, **kwargs)
        return redirect('/auth')
    return wrapper_decorator


class _AuthManager:
    def __init__(self, ) -> None:
        self.currentSessions:List[SessionInfo] = []

    def addNewSession(self, userId:str, peer_addr="", size=12) -> str:
        chars = string.ascii_uppercase + string.digits
        newSessionId = ''.join(random.choice(chars) for _ in range(size))
        sessionInfo = SessionInfo(id=newSessionId, 
                                expires=datetime.now() + timedelta(hours=1),
                                peer_addr=peer_addr, userId=userId)
        self.currentSessions.append(sessionInfo)
        return newSessionId

    def getValidSessions(self) ->List[SessionInfo]:
        self.removeExpiredSessions()
        return self.currentSessions
    
    def checkSessionValidity(self, sessionId:str, peer_addr:str='') -> bool:
        for session in self.getValidSessions():
            if session.id == sessionId:
                return True
        return False

    def getUserIdForSession(self, sessionId: str) -> str:
        for session in self.currentSessions:
            if session.id == sessionId:
                return session.userId
        return None

    def removeExpiredSessions(self):
        self.currentSessions = [s for s in self.currentSessions \
                    if (s.expires - datetime.utcnow()).total_seconds() > 0]

    def validateAuthRequest(self, email:str, password:str) -> Tuple[bool, str]:
        dbAdapter =  DatabaseAdapter()
        return dbAdapter.authenticateUser(email, password)


authManagerInstance = _AuthManager()
