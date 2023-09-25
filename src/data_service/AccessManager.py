from enum import Enum
from typing import List, Dict, Tuple, NamedTuple
from xmlrpc.client import Boolean
import jwt
import jwt.exceptions as jwtex
import functools
from flask import request, make_response
import config
from datetime import datetime, timedelta, timezone
import random
import string
from dbconnector import DBConnector
import psycopg2 as pg
import sys
import os
from ProfileCreator import createProfile


def valid_token_required(func):
    """ Decorator function, to be used on routes that need to be protected 
    behind a token based access mechanism.
    """
    @functools.wraps(func)
    def wrapper_decorator(*args, **kwargs):
        if config.VALIDATE_TOKEN == False:
            print(f"WARNING: Access control disabled for {request.path}. " \
                "Please ensure that it is enabled on the production deployment configuration.")
            return func(*args, **kwargs)
        
        if "Token" in request.headers.keys():
            if accessManagerInstance.validateToken(request.headers["Token"]):
                logAccess(request.args)
                return func(*args, **kwargs)
            else:
                logAccess(request.args, isValid=False)
                return make_response({"error": "invalid token"}, 401)
        logAccess(request.args, isValid=False)
        return make_response({"error": "no validation token provided with request"}, 401)
    return wrapper_decorator


def logAccess(req: request, isValid: bool=True):
    # change to a more efficient logging mechanism later
    with open(config.ACCESS_LOG_FILENAME, 'a') as logfile:
        logMessage = "\n{time}: Access request from {addr} for {resource}"
        if not isValid:
            logMessage = "\n{time}: UNVALIDATED REQUEST from {addr} for {resource}"
        logfile.write(logMessage.format(time=datetime.now().strftime("%c"),
                                        addr=request.remote_addr, 
                                        resource=request.path))


class AccessType(Enum):
    NONE=0
    READ=1
    WRITE=2
    ADMIN=3
    UNKNOWN=4


class AccessManager:
    def __init__(self) -> None:
        self.connector = None
        self.sessionTokens = []

    def _connectToAuthDB(self):
        self.connector = DBConnector(config.AUTH_DB_NAME, 
                                config.AUTH_DB_USER, 
                                config.AUTH_DB_PASSWORD,
                                config.AUTH_DB_HOST)
        self.connector.connect()

    def _decodeToken(self, token:str) -> Tuple[Boolean,Dict,str]:
        try:
            tokenObj = jwt.decode(token, key=config.TOKEN_KEY, 
                                    algorithms=config.TOKEN_ENCRYPTION_ALGO,
                                    options={"verify_aud":False, "verify_iss":False})
        except:
            # This scenario can occur due to various reasons:
            #  1. The token string sent from the client side does not represent a valid token
            #  2. The key used to encode the token is different from the key being used now
            #  3. The token encryption algorithm used during encoding is not used now
            #  4. The token is not (yet) valid: the timezone used is different from UTC
            #  5. Other ... unknown
            return False, tokenObj, "Invalid token: cannot decode"
        return True, tokenObj, "Successfully decoded token"

    def validateToken(self, token: str) -> bool:
        try:
            decodeResult = self._decodeToken(token)
            if not decodeResult[0]:
                if config.APP_DEBUG_MODE:
                    print(f"{decodeResult[2]} for token: {token}")
                return False
            
            tokenObj = decodeResult[1]
            if config.APP_DEBUG_MODE:
                print("JWT token recieved:", tokenObj)

            print("existing session tokens:\n", self.sessionTokens)                

            self.sessionTokens = [s for s in self.sessionTokens \
                    if (s["exp"] - datetime.utcnow()).total_seconds() > 0]

            print(f"Keeping {len(self.sessionTokens)} tokens in session")

            for sessiontoken in self.sessionTokens:
                if sessiontoken["sub"] == tokenObj["sub"] \
                        and sessiontoken["jti"] == tokenObj["jti"] \
                        and sessiontoken["iss"] == tokenObj["iss"] \
                        and sessiontoken["aud"] == tokenObj["aud"]:
                    return True
        except:
            if config.APP_DEBUG_MODE:
                print(f"The token {token} could not be validated")
        return False

    def _authenticateToken(self, authToken: str) -> Tuple[Boolean, Dict, str]:
        tokenIsValid = False
        decodeResult = self._decodeToken(authToken)
        if not decodeResult[0]:
            return tokenIsValid, {}, decodeResult[2]
        tokenObj = decodeResult[1]
        try:
            if self.connector is None or self.connector.connection.closed > 0:
                self._connectToAuthDB()
            
            cur = self.connector.getConnection().cursor()
            cur.execute("SELECT * FROM token_details " \
                       + f" WHERE token_subject=\'{tokenObj['sub']}\' " \
                       + f" AND jwt_id=\'{tokenObj['jti']}\'")
            tokenDetails = cur.fetchall()
            cur.close()

            for tokenDetail in tokenDetails:
                tokenExpiryDate = tokenDetail[5]
                tokenIsEnabled = tokenDetail[7]
                isTokenLockedToHost = tokenDetail[9]
                preferredHostAddr = tokenDetail[10]
                if (tokenExpiryDate - datetime.now()).total_seconds() > 0 \
                        and tokenIsEnabled:
                    tokenIsValid = True
                    break
        except(Exception, pg.DatabaseError) as error:
            print(error)
            return tokenIsValid, tokenObj, str(error)
        return tokenIsValid, tokenObj, "authentication successful"

    def getSessionToken(self, authToken:str) -> Tuple[Boolean,str,str]:
        authenticationResult = self._authenticateToken(authToken)
        if not authenticationResult[0]:
            return False, "", authenticationResult[2]
        
        authTokenObj = authenticationResult[1]
        sessionTokenObj = {}
        payload = {
            "iss": "LearnDB Session Management System",
            "sub": authTokenObj["sub"],
            "aud": authTokenObj["aud"],
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(days=1),
            "jti": authTokenObj["jti"]
        }
        sessionTokenObj = jwt.encode(payload, key=config.TOKEN_KEY, 
                                    algorithm=config.TOKEN_ENCRYPTION_ALGO)
        self.sessionTokens.append(payload)
        return True, sessionTokenObj, "Session token successfully generated"

    def getReadACLForToken(self, token:str) -> Tuple[List[str], List[str]]:
        return self.getACLForToken(token, accessType=AccessType.READ)

    def getWriteACLForToken(self, token:str) -> Tuple[List[str], List[str]]:
        return self.getACLForToken(token, accessType=AccessType.WRITE)

    def getAdminACLForToken(self, token:str) -> Tuple[List[str], List[str]]:
        return self.getACLForToken(token, accessType=AccessType.ADMIN)

    def getACLForToken(self, token:str, accessType:AccessType) -> Tuple[List[str], List[str]]:
        invalidACl = ["unknown"], ["unknown"]
        decodeResult = self._decodeToken(token)
        if not decodeResult[0]:
            return invalidACl 
        tokenObj = decodeResult[1]

        try:
            if self.connector is None or self.connector.connection.closed > 0:
                self._connectToAuthDB()
            
            cur = self.connector.getConnection().cursor()
            accessTypeClause = ""
            if accessType == AccessType.READ:
                accessTypeClause = "AND read_access = TRUE "
            elif accessType == AccessType.WRITE:
                accessTypeClause = "AND write_access = TRUE "
            elif accessType == AccessType.ADMIN:
                accessTypeClause = "AND admin_access = TRUE "

            cur.execute("SELECT site_name, trial_name FROM token_details, " \
                        + " acl_roles, trials, treatment_sites " \
                        + f" WHERE token_subject=\'{tokenObj['sub']}\' " \
                        + f" AND jwt_id=\'{tokenObj['jti']}\' " \
                        + " AND token_details.id = acl_roles.token_id " \
                        + " AND treatment_sites.site_id = acl_roles.site_id " \
                        + " AND trials.trial_id = acl_roles.trial_id " \
                        + accessTypeClause)
            aclEntries = cur.fetchall()
            cur.close()

            if len(aclEntries) == 0:
                acl = invalidACl
            else:
                acl = [], []
                for aclEntry in aclEntries:
                    if aclEntry[0] not in acl[0]:
                        acl[0].append(aclEntry[0])
                    if aclEntry[1] not in acl[1]:
                        acl[1].append(aclEntry[1])
        except(Exception, pg.DatabaseError) as error:
            print(error)
            return invalidACl
        return acl



# Single instance of AccessManager for the module
accessManagerInstance = AccessManager()

def generateRandomString(length: int) -> str:
    return str([random.choice(string.ascii_letters) for counter in range(length)])


def createToken():
    # Temporary mechanism to generate a deveopment token, to be replaced by a 
    # proper token management mechanism.
    payload = {
        "iss": "Image-X Access Management System",
        "sub": "Development User",
        "aud": "Development System",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=365),
        "jti": "JTID00000001"
        }
    with open("tokenfile.txt", 'w') as tokenFile:
        tokenFile.write(jwt.encode(payload, key=config.TOKEN_KEY, 
                        algorithm=config.TOKEN_ENCRYPTION_ALGO))


def createTokenWithDetails(subject: str, audience: str, issuedAt: datetime, 
                            expiresAt: datetime, jwtId: str) -> str:
    payload = {
        "iss": "LearnDB Access Management System",
        "sub": subject,
        "aud": audience,
        "iat": datetime.fromtimestamp(issuedAt.timestamp(), tz=timezone.utc),
        "exp": datetime.fromtimestamp(expiresAt.timestamp(), tz=timezone.utc),
        "jti": jwtId
        }
    return jwt.encode(payload, key=config.TOKEN_KEY, 
                        algorithm=config.TOKEN_ENCRYPTION_ALGO)


def processTokenRequestApplication(applicationData: Dict[str, str]) -> Tuple[Dict, Dict, str]:
    if config.APP_DEBUG_MODE:
        print(f"applicationData: {applicationData}")
    expectedFields = ["subject_name", "subject_email", "audience", 
                    "password_once", "password_twice", "notes", "consent"]
    result = {
        "status": True,
        "message": "", 
        "jwt_id": "", 
        "input_errors": {k:"" for k in expectedFields}
    }
    sitesAndTrials:SitesAndTrials = getSitesAndTrials()
    inputData = {}
    for field in expectedFields:
        if field not in applicationData or not applicationData[field].strip():
            result["status"] = False
            result["message"] += f" missing value for {field};"
            result["input_errors"][field] = "Cannot accept an empty value"
        else:
            print(f"{field} has {applicationData[field]}")
            inputData[field] = applicationData[field].strip()

    if not result["status"]:
        return result, inputData

    if inputData["password_once"] != inputData["password_twice"]:
            result["status"] = False
            result["message"] += f" passwords not matching;"
            result["input_errors"]["password_twice"] = "Passwords not matching"

    if '@' not in inputData["subject_email"] or '.' not in inputData["subject_email"]:
            result["status"] = False
            result["message"] += f" unexpected e-mail format;"
            result["input_errors"]["subject_email"] = "Unexpected e-mail format"

    if inputData["consent"] not in ['on', 'yes', 'true']:
            result["status"] = False
            result["message"] += f" agreement to terms and conditions required;"
            result["input_errors"]["consent"] = "Agreement to terms and conditions required"

    if result["status"]:
        connector = DBConnector(config.AUTH_DB_NAME, 
                                config.AUTH_DB_USER, 
                                config.AUTH_DB_PASSWORD,
                                config.AUTH_DB_HOST)
        connector.connect()

        try:
            conn = connector.getConnection() 
            cur = conn.cursor()
            cur.execute("INSERT INTO token_details (token_subject, " \
                        + "subject_email, audience, hashed_secret, reason) " \
                        + "VALUES (%s, %s, %s, %s, %s);", 
                        (inputData["subject_name"], 
                        inputData["subject_email"],
                        inputData["audience"],
                        inputData["password_once"],
                        inputData["notes"]))
            conn.commit()

            cur.execute("SELECT jwt_id, token_subject, " \
                        + "audience, issued_at, expires_at " \
                        + "FROM token_details WHERE " \
                        + "token_subject = %s AND " \
                        + "subject_email = %s AND " \
                        + "audience = %s " \
                        + "ORDER BY issued_at DESC;",
                        (inputData["subject_name"],
                        inputData["subject_email"],
                        inputData["audience"]))
            insertedTokenDetails = cur.fetchone()

            if "sites" in applicationData and "trials" in applicationData:
                print("sites:", applicationData.getlist("sites"))
                for site in applicationData.getlist("sites"):
                    for trial in applicationData.getlist("trials"):
                        cur.execute("INSERT INTO acl_roles (token_id, " \
                                    + "trial_id, site_id, read_access) " \
                                    + "VALUES ( " \
                                    + "(SELECT id FROM token_details WHERE jwt_id=%s), " \
                                    + "(SELECT trial_id FROM trials WHERE trial_name=%s), " \
                                    + "(SELECT site_id FROM treatment_sites WHERE site_name=%s), " \
                                    + "TRUE);", 
                                    (insertedTokenDetails[0], 
                                    trial,
                                    site))
                        conn.commit()
            cur.close()
        except (Exception, pg.DatabaseError) as error:
            print(error)
    
        if not insertedTokenDetails:
            result["status"] = False
            result["message"] += f" could not save details to database;"
        else:
            result["jwt_id"] = insertedTokenDetails[0]
            result["token"] = createTokenWithDetails(
                                    subject=insertedTokenDetails[1], 
                                    audience=insertedTokenDetails[2],
                                    issuedAt=insertedTokenDetails[3],
                                    expiresAt=insertedTokenDetails[4],
                                    jwtId=insertedTokenDetails[0])
            profile = createProfile(result["jwt_id"], 
                        f"{config.LISTENING_HOST}", 
                        f"{config.SERVER_INSTANCE_NAME}",
                        f"http://{config.LISTENING_HOST}:{config.LISTENING_PORT}", 
                        config.LISTENING_PORT,
                        result["token"], 
                        inputData["password_once"],

                        config.TEMP_CACHE_PATH)
            if not os.path.exists(profile):
                if config.APP_DEBUG_MODE:
                    print(f"Profile creation failed for {result['jwt_id']}: {profile}", 
                        file=sys.stderr)
            else:
                if config.APP_DEBUG_MODE:
                    print("profile:", profile)
            result["profile"] = os.path.basename(profile)
    return result, inputData

# TODO: Create a common package with custom types etc. and use it across services 
class SiteDetails(NamedTuple):
    name: str
    fullName: str

class TrialDetails(NamedTuple):
    name: str
    fullName: str

class SitesAndTrials(NamedTuple):
    sites: List[SiteDetails]
    trials: List[TrialDetails]


def getSitesAndTrials() -> SitesAndTrials:
    connector = DBConnector(config.AUTH_DB_NAME, 
                            config.AUTH_DB_USER, 
                            config.AUTH_DB_PASSWORD,
                            config.AUTH_DB_HOST)
    connector.connect()

    trials = []
    sites = []

    try:
        conn = connector.getConnection() 
        cur = conn.cursor()
        cur.execute("SELECT trial_name, trial_full_name FROM trials")
        trialRows = cur.fetchall()
        for trial in trialRows:
            trials.append(TrialDetails(name=trial[0], fullName=trial[1]))
        cur.close()

        cur = conn.cursor()
        cur.execute("SELECT site_name, site_full_name FROM treatment_sites")
        siteRows = cur.fetchall()
        for site in siteRows:
            sites.append(SiteDetails(name=site[0], fullName=site[1]))
        cur.close()

    except (Exception, pg.DatabaseError) as error:
        print(error, file=sys.stderr)

    return SitesAndTrials(sites, trials)


def _executeQuery(queryStmt:str) -> List[Tuple]:
    connector = DBConnector(config.AUTH_DB_NAME, 
                            config.AUTH_DB_USER, 
                            config.AUTH_DB_PASSWORD,
                            config.AUTH_DB_HOST)
    connector.connect()
    conn = connector.getConnection()

    fetchedRows = None
    try:
        cur = conn.cursor()
        cur.execute(queryStmt)
        fetchedRows = cur.fetchall()
        cur.close()
    except (Exception, pg.DatabaseError) as err:
        print(err, file=sys.stderr)
    return fetchedRows


def getSites() -> List[SiteDetails]:
    rows = _executeQuery("SELECT site_name, site_full_name FROM treatment_sites")
    sites = []
    for siteRow in rows:
        sites.append(SiteDetails(name=siteRow[0], fullName=siteRow[1]))
    return sites


def getTrials() -> List[TrialDetails]:
    rows = _executeQuery("SELECT trial_name, trial_full_name FROM trials")
    trials = []
    for trialRow in rows:
        trials.append(SiteDetails(name=trialRow[0], fullName=trialRow[1]))
    return trials

def addSiteTrial(newDetails: Dict[str, str]) -> Tuple[bool, str]:
    query = ""
    if newDetails['type'] == 'site':
        query = "INSERT INTO treatment_sites (site_name, site_full_name, site_location) " \
                + f"VALUES (\'{newDetails['name']}\', \'{newDetails['fullName']}\', \'{newDetails['location']}\');"
    elif newDetails['type'] == 'trial':
        query = "INSERT INTO trials (trial_name, trial_full_name) " \
                + f"VALUES (\'{newDetails['name']}\', \'{newDetails['fullName']}\');"
    else:
        return False, "Invalid type specified"
    connector = DBConnector(config.AUTH_DB_NAME,
                            config.AUTH_DB_USER,
                            config.AUTH_DB_PASSWORD,
                            config.AUTH_DB_HOST)
    connector.connect()
    conn = connector.getConnection()
    try:
        cur = conn.cursor()
        cur.execute(query)
        conn.commit()
        cur.close()
    except (Exception, pg.DatabaseError) as err:
        print(err, file=sys.stderr)
        return False, str(err)
    return True, "Successfully added new site/trial"
    

def getSitesForTrial(trial:str) ->List[SiteDetails]:
    rows = _executeQuery("SELECT site_name, site_full_name " \
                        + "FROM treatment_sites, trials, site_trial_mapping " \
                        + "WHERE treatment_sites.site_id = site_trial_mapping.site_id " \
                        + "AND trials.trial_id = site_trial_mapping.trial_id " \
                        + f"AND trials.trial_name = \'{trial}\'")
    sites = []
    for siteRow in rows:
        sites.append(SiteDetails(name=siteRow[0], fullName=siteRow[1]))
    return sites
