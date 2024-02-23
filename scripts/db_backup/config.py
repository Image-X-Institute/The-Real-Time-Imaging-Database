import json

def loadLocalSettings():    
    with open("local_settings.json") as localSettingsFile:
        localsettings = json.load(localSettingsFile)
    return localsettings

localSettings = loadLocalSettings()

DB_HOST=localSettings["imaging_db_host"]
DB_PORT=localSettings["imaging_db_port"]
DB_USER=localSettings["imaging_db_user"]
DB_PASSWORD=localSettings["imaging_db_password"]
DB_NAME=localSettings["imaging_db_name"]
AUTH_DB_HOST=localSettings["auth_db_host"]
AUTH_DB_PORT=localSettings["auth_db_port"]
AUTH_DB_USER=localSettings["auth_db_user"]
AUTH_DB_PASSWORD=localSettings["auth_db_password"]
AUTH_DB_NAME=localSettings["auth_db_name"]