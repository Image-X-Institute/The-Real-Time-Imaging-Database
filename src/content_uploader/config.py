import json
from PySide6.QtCore import QStandardPaths
from sys import stderr
from pathlib import Path


class AppConfig:
    def __init__(self, appName=__name__) -> None:
        self.appName = appName
        self.config = {}
        self.loadSavedConfigSettings()

    def _getLocalConfigFilePath(self) -> str:
        appConfigFolderPath = QStandardPaths.writableLocation(
                            QStandardPaths.StandardLocation.AppConfigLocation)
        return appConfigFolderPath + f"/{self.appName}_config.json"

    def loadSavedConfigSettings(self):
        configFilePath = self._getLocalConfigFilePath()
        try:
            with open(configFilePath, 'r') as configFile:
                self.config = json.loads(configFile.read())
        except FileNotFoundError as err:
            print("No previously saved configuration found", file=stderr)
            
    def persistConfigSettings(self):
        configFilePath = self._getLocalConfigFilePath()
        configPathDir = Path(configFilePath).parent
        configPathDir.mkdir(parents=True, exist_ok=True)
        with open(configFilePath, 'w') as configFile:
             configJSONText = json.dumps(self.config, indent=4)
             configFile.write(configJSONText)

    def getValue(self, key:str, defaultValue:str='') -> str:
        key = key.strip('/')
        keyHierarchy = key.split('/')
        conf = self.config
        configValue = defaultValue
        level = 0
        for keyComponent in keyHierarchy:
            if keyComponent in conf:
                if level < (len(keyHierarchy) - 1):
                    conf = conf[keyComponent]
                    level += 1
                elif level == (len(keyHierarchy) - 1):
                    configValue = conf[keyComponent] \
                        if isinstance(conf[keyComponent], str) else defaultValue
                else:
                    break
            else:
                break
        return configValue

    def setValue(self, key:str, value:str):
        key = key.strip('/')
        keyHierarchy = key.split('/')
        conf = self.config
        level = 0
        for keyComponent in keyHierarchy:
            if keyComponent not in conf:
                if level < (len(keyHierarchy) - 1):
                    conf[keyComponent] = {}
                    conf = conf[keyComponent]
                    level += 1
                elif level == (len(keyHierarchy) - 1):
                    conf[keyComponent] = value
                else:
                    raise KeyError()
            else:
                if level < (len(keyHierarchy) - 1):
                    if isinstance(conf, dict):
                        level += 1
                        conf = conf[keyComponent]
                    else:
                        raise KeyError()
                elif level == (len(keyHierarchy) - 1):
                    conf[keyComponent] = value


def testAppConfig():
    appConfig = AppConfig()
    appConfig.loadSavedConfigSettings()
    print("Value of param1:", appConfig.getValue("param1"))
    print("Value of localsettings/now:", appConfig.getValue("localsettings/now", "unknown"))
    import datetime as dt
    appConfig.setValue("localsettings/now", str(dt.datetime.now()))
    print("Value of localsettings/now:", appConfig.getValue("localsettings/now"))
    appConfig.setValue("localsettings/some-key", "some-value")
    print("Value of /localsettings/now:", appConfig.getValue("/localsettings/now", "unknown"))
    print("Value of /localsettings/now/:", appConfig.getValue("/localsettings/now/", "unknown"))
    appConfig.persistConfigSettings()
    appConfig.setValue("localsettings/another-key/sub-key", "another value")
    appConfig.persistConfigSettings()
    appConfig.loadSavedConfigSettings()
    print("Value of /localsettings/another-key/sub-key:", 
            appConfig.getValue("/localsettings/another-key/sub-key"))


if __name__ == "__main__":
    testAppConfig()