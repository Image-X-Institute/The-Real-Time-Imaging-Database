from zipfile import ZipFile, BadZipFile
from enum import Enum
from typing import Dict, List
import json
import hashlib
import sys


class ConnectionType(Enum):
    IMPORT_ONLY = 0,
    DIRECT = 1,
    ONEDRIVE = 2,
    SFTP = 3


class ProfileManager:
    def __init__(self, profilePath:str, password:bytes) -> None:
        self.profilePath = profilePath
        self.password = password
        self.isValid = False
        self.profile = None
        self._openAndReadProfile()
        
    def _openAndReadProfile(self):
        self.profile = None
        self.isValid = False
        try:
            with ZipFile(self.profilePath, mode='r') as profileZip:
                profileJSONName = ''
                for zipiinfo in profileZip.infolist():
                    if zipiinfo.filename.split('.')[-1] == "json":
                        profileJSONName = zipiinfo.filename
                        break
                self.profile = json.loads(profileZip.read(profileJSONName, 
                                                        pwd=self.password))
                self.isValid = self._evaluateProfileValidity()

        except RuntimeError as rterr:
            print("Incorrect password entered")
        except (BadZipFile, FileNotFoundError) as err:
            print("Could not open profile:", err)

    def _hasConnectionProfiles(self) -> bool:
        if self.profile is None or not self.profile:
            return False

        if not self.isValid:
            return False

        if "profiles" not in self.profile:
            return False
        
        return True

    def getDefaultConnectionProfileIndex(self) -> int:
        if not self._hasConnectionProfiles():
            return -1

        if "default_profile" in self.profile:
            defaultProfile = self.profile["default_profile"]
            if defaultProfile >= len(self.profile["profiles"]):
                return -1
        else:
            defaultProfile = 0

        return defaultProfile              

    def getDefaultConnectionProfile(self) -> Dict:
        defaultProfileIndex = self.getDefaultConnectionProfileIndex()
        defaultProfile = self.profile["profiles"][defaultProfileIndex] \
                                if defaultProfileIndex >= 0 else None
        return defaultProfile


    def getAllProfileDetails(self) -> List[Dict]:
        allProfileDetails = []
        if not self._hasConnectionProfiles():
            return allProfileDetails
        return self.profile["profiles"]

    def getConnectionProfileNames(self) -> List[str]:
        profileNames = []
        if not self._hasConnectionProfiles():
            return profileNames

        for profile in self.profile["profiles"]:
            profileNames.append(profile["name"])
        
        return profileNames

    def _evaluateProfileValidity(self) -> bool:
        if self.profile is None or not self.profile:
            return False

        if "code" in self.profile:
            verificationCode = self.profile["code"]
            del self.profile["code"]
            profileStr = json.dumps(self.profile, sort_keys=True, indent=4)
            currentCode = hashlib.sha256(profileStr.encode("utf-8")).hexdigest()
            # print("code should be:", currentCode)
            if currentCode != verificationCode:
                print("Profile integrity cannot be confirmed", file=sys.stderr)
                return False

        if "expires" in self.profile:
            if self.profile["expires"] == "never":
                return True
            # if the expiry date is later than today:
            #   return True
        return False

    def getServerInstanceName(self) -> str:
        if self.profile and "instance_name" in self.profile:
            return self.profile["instance_name"]
        return "Learn DB Service"


def _test_ProfileManager():
    profileMgr = ProfileManager("testdata/test.profile", b"password")
    print("Default connection:", profileMgr.getDefaultConnectionProfile())


if __name__ == "__main__":
    _test_ProfileManager()
