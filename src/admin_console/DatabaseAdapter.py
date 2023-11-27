from cgitb import reset
import psycopg2 as pg
import config
from typing import Dict, List, Tuple
from CustomTypes import SiteDetails, TrialDetails, DBUpdateResult, DBFindResult
import sys


class DatabaseAdapter:
    def __init__(self) -> None:
        self.imageDBConn = None
        self.authDBConn = None

    def __del__(self):
        if self.imageDBConn:
            self.imageDBConn.close()
        if self.authDBConn:
            self.authDBConn.close()

    def _connect(self, connectionParams:Dict):
        try:
            dbConn = pg.connect(database=connectionParams["database"], 
                                user=connectionParams["user"], 
                                password=connectionParams["password"],
                                host=connectionParams["host"])

            cur = dbConn.cursor()
            print("Connected to PostgreSQL version:", end=" ")
            cur.execute("SELECT version()")
            db_version = cur.fetchone()
            print(db_version)
            cur.close()
        except (Exception, pg.DatabaseError) as error:
             print(error, file=sys.stderr)
             dbConn = None
        return dbConn

    def getImageDBConnection(self):
        if self.imageDBConn is None:
            connParams = {
                "database": config.DB_NAME, 
                "user": config.DB_USER, 
                "password": config.DB_PASSWORD, 
                "host": config.DB_HOST
                }
            self.imageDBConn = self._connect(connectionParams=connParams)
        return self.imageDBConn

    def getAuthDBConnection(self):
        if self.authDBConn is None:
            connParams = {
                "database": config.AUTH_DB_NAME, 
                "user": config.AUTH_DB_USER, 
                "password": config.AUTH_DB_PASSWORD, 
                "host": config.AUTH_DB_HOST
                }
            self.authDBConn = self._connect(connectionParams=connParams)
        return self.authDBConn

    def getTreatementSites(self) -> List[SiteDetails]:
        sites = []
        try:
            conn = self.getAuthDBConnection() 
            cur = conn.cursor()
            cur.execute("SELECT site_name, site_full_name FROM treatment_sites")
            siteRows = cur.fetchall()
            for site in siteRows:
                sites.append(SiteDetails(name=site[0], fullName=site[1]))
            cur.close()
        except (Exception, pg.DatabaseError) as error:
            print(error, file=sys.stderr)
        return sites

    def getSiteNames(self) -> List[str]:
        sites = self.getTreatementSites()
        siteNames = [site.name for site in sites]
        return siteNames        

    def getClinicalTrials(self) -> List[TrialDetails]:
        trials = []
        try:
            conn = self.getAuthDBConnection()
            cur = conn.cursor()
            cur.execute("SELECT trial_name, trial_full_name FROM trials")
            trialRows = cur.fetchall()
            for trial in trialRows:
                trials.append(TrialDetails(name=trial[0], fullName=trial[1]))
            cur.close()
        except (Exception, pg.DatabaseError) as error:
            print(error, file=sys.stderr)
        return trials

    def getClinicalTrialNames(self) -> List[str]:
        trials = self.getClinicalTrials()
        trialNames = [trial.name for trial in trials]
        return trialNames

    def getTokenDetails(self) -> List[Dict]:
        tokens = []
        try:
            conn = self.getAuthDBConnection()
            cur = conn.cursor()
            cur.execute("SELECT token_subject, audience, issued_at, " \
                    "jwt_id, is_enabled, reason FROM token_details " \
                    "ORDER BY issued_at DESC")
            tokenRows = cur.fetchall()
            for token in tokenRows:
                tokens.append({
                    "token_subject": token[0],
                    "audience": token[1],
                    "issued_at": token[2],
                    "jwt_id": token[3],
                    "is_enabled": token[4],
                    "status": "ACTIVE" if token[4] else "INACTIVE",
                    "reason": token[5],
                    })
            cur.close()
        except (Exception, pg.DatabaseError) as error:
            print(error, file=sys.stderr)
        return tokens

    def authenticateUser(self, email:str, password:str) -> Tuple[bool, str]:
        result = False
        id = ''
        query = "SELECT jwt_id FROM token_details WHERE " \
                f"subject_email=\'{email}\' " \
                f"AND hashed_secret=\'{password}\' " \
                "AND is_enabled=true " \
                "AND expires_at > now()"
        print(query)
        try:
            conn = self.getAuthDBConnection()
            cur = conn.cursor()
            cur.execute(query)
            jwtIds = cur.fetchall()
            print("result:", jwtIds)
            if len(jwtIds) > 0:
                result = True
                id = jwtIds[0][0]
            cur.close()
        except (Exception, pg.DatabaseError) as error:
            print(error, file=sys.stderr)
        return result, id

    def getWritableTrialsAndSitesForUser(self, userId:str) -> Dict[str, List[str]]:
        result = {}
        query = "SELECT trial_name, site_name FROM token_details, acl_roles, " \
                "treatment_sites, trials WHERE " \
                f"token_details.jwt_id = \'{userId}\' " \
                "AND token_details.id = acl_roles.token_id " \
                "AND token_details.is_enabled = true " \
                "AND acl_roles.read_access = true " \
                "AND acl_roles.trial_id = trials.trial_id " \
                "AND acl_roles.site_id = treatment_sites.site_id"
        try:
            conn = self.getAuthDBConnection()
            cur = conn.cursor()
            cur.execute(query)
            trialsAndSites = cur.fetchall()
            for trialAndSite in trialsAndSites:
                if trialAndSite[0] not in result:
                    result[trialAndSite[0]] = []
                if trialAndSite[1] not in result[trialAndSite[0]]:
                    result[trialAndSite[0]].append(trialAndSite[1])
            cur.close()
        except (Exception, pg.DatabaseError) as error:
            print(error, file=sys.stderr)
        return result

    def toggleTokenStatus(self, tokenId:str):
        rowsUpdated = 0
        try:
            conn = self.getAuthDBConnection()
            cur = conn.cursor()
            cur.execute(f"UPDATE token_details SET is_enabled = NOT is_enabled WHERE jwt_id = '{tokenId}'")
            rowsUpdated = cur.rowcount
            conn.commit()
            cur.close()
        except (Exception, pg.DatabaseError) as error:
            print(error, file=sys.stderr)
            return DBUpdateResult(success=False, rowsUpdated=0, message=str(error)) 
        return DBUpdateResult(success=True, rowsUpdated=rowsUpdated, message="Success")

    def executeUpdateOnImageDB(self, stmt:str) -> DBUpdateResult:
        print("Executing UPDATE Statement:", stmt)
        rowsUpdated = 0
        try:
            conn = self.getImageDBConnection()
            cur = conn.cursor()
            cur.execute(stmt)
            rowsUpdated = cur.rowcount
            conn.commit()
            cur.close()
        except (Exception, pg.DatabaseError) as error:
            print(error, file=sys.stderr)
            return DBUpdateResult(success=False, rowsUpdated=0, message=str(error)) 
        return DBUpdateResult(success=True, rowsUpdated=rowsUpdated, message="Success")
    
    def executeFindOnImageDB(self, stmt:str) -> List[Dict]:
        print("Executing SELECT Statement:", stmt)
        result = []
        try:
            conn = self.getImageDBConnection()
            cur = conn.cursor()
            cur.execute(stmt)
            result = cur.fetchall()
            cur.close()
        except (Exception, pg.DatabaseError) as error:
            print(error, file=sys.stderr)
            return DBFindResult(success=False, result=[], message=str(error))
        return DBFindResult(success=True, result=result, message="Success")
    
    def getFractionIdAndDate(self, patientTrialId:str, fractionNumber:int) -> tuple:
        strQuery = "SELECT fraction_id, fraction_date FROM fraction, patient, prescription " \
                    + "WHERE patient.patient_trial_id = '" + patientTrialId + "' " \
                    + "AND prescription.patient_id = patient.id " \
                    + "AND fraction.prescription_id = prescription.prescription_id " \
                    + "AND fraction.fraction_number = " + str(fractionNumber) + ";"
        if config.APP_DEBUG_MODE:
            print("Executing Query:", strQuery)

        try:
            conn = self.getImageDBConnection()
            cur = conn.cursor()
            cur.execute(strQuery)
            fractionIdAndDate = cur.fetchone()
            cur.close()
        except (Exception, pg.DatabaseError) as error:
            print(error, file=sys.stderr)
            return (None, None)
        return fractionIdAndDate
    
    def getFractionIdAndName(self, patientTrialId:str, fractionNumber:int) -> List[tuple]:
        strQuery = "SELECT fraction_id, fraction_name FROM fraction, patient, prescription " \
                    + "WHERE patient.patient_trial_id = '" + patientTrialId + "' " \
                    + "AND prescription.patient_id = patient.id " \
                    + "AND fraction.prescription_id = prescription.prescription_id " \
                    + "AND fraction.fraction_number = " + str(fractionNumber) + ";"
        if config.APP_DEBUG_MODE:
            print("Executing Query:", strQuery)

        try:
            conn = self.getImageDBConnection()
            cur = conn.cursor()
            cur.execute(strQuery)
            fractionIdAndName = cur.fetchall()
            cur.close()
        except (Exception, pg.DatabaseError) as error:
            print(error, file=sys.stderr)
            return []
        return fractionIdAndName
    
    def updateFractionName(self, fractionId:str, fractionName:str) -> DBUpdateResult:
        stmt = "UPDATE fraction SET fraction_name = '" + fractionName + "' " \
                + "WHERE fraction_id = '" + fractionId + "';"
        return self.executeUpdateOnImageDB(stmt=stmt)
    
    def getPatientId(self, patientTrialId:str) -> str:
        strQuery = "SELECT id FROM patient WHERE patient_trial_id = '" + patientTrialId + "';"
        if config.APP_DEBUG_MODE:
            print("Executing Query:", strQuery)

        try:
            conn = self.getImageDBConnection()
            cur = conn.cursor()
            cur.execute(strQuery)
            patientId = cur.fetchone()[0]
            cur.close()
        except (Exception, pg.DatabaseError) as error:
            print(error, file=sys.stderr)
            return None
        return patientId
    
    def insertFractionIntoDB(self, fractionDetails:Dict)  -> bool:
        insertStmt = "INSERT INTO fraction (prescription_id, " \
                                + "fraction_date, fraction_number, " \
                                + "fraction_name) " \
                                + "SELECT get_prescription_id_for_patient('" \
                                +  fractionDetails["patient_trial_id"] + "'), " \
                                + "'" + fractionDetails["date"] + "', " \
                                + str(fractionDetails["number"]) + ", " \
                                + "'" + fractionDetails["name"] + "' " \
                                + "RETURNING fraction_id"
        if config.APP_DEBUG_MODE:
            print(insertStmt)
        
        try:
            conn = self.getImageDBConnection()
            cur = conn.cursor()
            cur.execute(insertStmt)
            fractionUUID = cur.fetchone()[0]
            if config.APP_DEBUG_MODE:
                print("Cursor Description after insert:", cur.description, fractionUUID)
            self.getImageDBConnection().commit()
            cur.close()
        except(Exception, pg.DatabaseError) as error:
            return False, str(error)

        insertStmt = "INSERT INTO images (fraction_id) " \
                    + "VALUES ('" \
                    + fractionUUID + "')"
        try:
            conn = self.getImageDBConnection()
            cur = conn.cursor()
            cur.execute(insertStmt)
            if config.APP_DEBUG_MODE:
                print("Cursor Description after insert:", cur.description)
            self.getImageDBConnection().commit()
            cur.close()
        except(Exception, pg.DatabaseError) as error:
            return False
                    
        return True

