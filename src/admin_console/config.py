import json
def loadLocalSettings():    
    with open("local_settings.json") as localSettingsFile:
        localsettings = json.load(localSettingsFile)
    return localsettings

localSettings = loadLocalSettings()

LISTENING_HOST="0.0.0.0"  # listen to all the interfaces of the localhost
LISTENING_PORT=localSettings["listening_port"]

UI_DIR="./gui/web_gui"
DB_FOLDER_PATH="./database"
JINJA_TEMPLATES_FOLDER="./gui/web_gui"

UPLOAD_METADATA_FILENAME="upload_metadata.json"

APP_DEBUG_MODE=localSettings["debug_mode"]
UPLOAD_FOLDER=localSettings["upload_folder_path"]  # "C:/Indrajit/temp/data_store"
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
DATA_FILESYSTEM_ROOT=localSettings["root_filesystem_path"]
DATA_SERVICE_URL=localSettings["data_service_url"]
