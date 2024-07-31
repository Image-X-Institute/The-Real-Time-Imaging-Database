import os
import json
from flask import Flask

def loadLocalSettings():    
    with open("local_settings.json") as localSettingsFile:
        localsettings = json.load(localSettingsFile)
    return localsettings

localSettings = loadLocalSettings()

SERVER_INSTANCE_NAME=localSettings["server_instance_name"]
LISTENING_HOST=localSettings["listening_addr"] # "0.0.0.0"  # listen to all the interfaces of the localhost
LISTENING_PORT=localSettings["listening_port"]
APP_DEBUG_MODE=localSettings["debug_mode"]
APP_DIAGNOSTICS_MODE=localSettings["diagnostics"]
UI_DIR="gui"
DB_FOLDER_PATH="./database"
JINJA_TEMPLATES_FOLDER="./gui/web_gui"
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
#VALIDATE_TOKEN=True  # change to false for debugging without validation
VALIDATE_TOKEN=False
TOKEN_KEY=os.getenv("SECRET_KEY", "secret_key")
TOKEN_ENCRYPTION_ALGO="HS256"
ACCESS_LOG_FILENAME="accesslog.txt"
DATA_FILESYSTEM_ROOT=localSettings["root_filesystem_path"]
LOGFILE_NAME="RealtimeImagingDB.txt"
UPLOAD_FOLDER=localSettings["upload_folder_path"]
TEMP_CACHE_PATH=localSettings["temp_cache_path"]
JWT_SECRET_KEY=localSettings['JWT_SECRET']
JWT_ALGORITHM=localSettings['JWT_ALGORITHM']
CLOUD_DRIVE_FOLDER=localSettings['cloud_drive_folder']

def setMailConfig(app: Flask):
    if app is not None:
        app.config['MAIL_SERVER'] = localSettings["notif_mail_host"]
        app.config['MAIL_PORT'] = localSettings["notif_mail_port"]
        app.config['MAIL_USERNAME'] = localSettings["notif_mail_user"]
        app.config['MAIL_PASSWORD'] = localSettings["notif_mail_password"]
        app.config['MAIL_USE_TLS'] = localSettings["notif_mail_use_tls"]
        app.config['MAIL_USE_SSL'] = localSettings["notif_mail_use_ssl"]
