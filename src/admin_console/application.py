from flask import Flask, make_response, send_from_directory, redirect, \
        request, render_template, send_file
from DataImporter import DataImporter
import config
from UploadManager import UploadManager
from DatabaseAdapter import DatabaseAdapter
from AuthManagement import autheticated_access, authManagerInstance


app = Flask(__name__, 
            static_folder=config.UI_DIR, 
            template_folder=config.JINJA_TEMPLATES_FOLDER)
application = app  # required for making it work on AWS


@app.route('/')
def root():
    print("Got a request for / : ", request.path)
    rsp = redirect('/index.html')
    return rsp


@app.route('/index.html')
@autheticated_access
def sendSiteIndex():
    # Placeholder for a welcome page with options appropriate for user type
    # return redirect("/base_layout")
    return redirect("/uploads")


@app.route('/base_layout')
def sendBaseLayout():
    return render_template("/base_layout.html")


@app.route('/uploads')
@autheticated_access
def sendUploadsApprovalPage():
    uploadMgr = UploadManager()
    currentUserId = authManagerInstance.getUserIdForSession(request.cookies.get("session"))
    return render_template('uploads.html', data=uploadMgr.findCurrentUploads(currentUserId))


@app.route('/auth', methods=['GET', 'POST'])
def authenticate():
    error_msg = None
    if request.method == "POST":
        if "email" not in request.form or "password" not in request.form:
            error_msg = "Please provide the valid authtication parameters"
        else:
            result = authManagerInstance.validateAuthRequest(
                        request.form["email"], request.form["password"])
            if not result[0]:
                error_msg = "Invalid email or password, please try again."
            else:
                sessionId = authManagerInstance.addNewSession(result[1])
                resp = redirect("/index.html")
                resp.set_cookie("session", sessionId)
                return resp
    return render_template('login.html', error_msg=error_msg)

@app.route('/create_new_trial', methods=['GET'])
def createNewTrial():
    return render_template('create_new_trial.html')

@app.route('/download_template', methods=['GET'])
def downloadTemplate():
    return send_file("./gui/web_gui/assets/template.json", as_attachment=True)

@app.route('/id/<upload_id>')
@autheticated_access
def importUpload(upload_id):
    uploadMgr = UploadManager()
    uploadData = uploadMgr.getUploadDetails(upload_id)
    if not uploadData:
        return make_response({"status": "error", 
                            "message": f"Upload ID {upload_id} not found"})
    return render_template('upload_details.html', data=uploadData)


@app.route('/import/<upload_id>')
@autheticated_access
def importUploadPacket(upload_id):
    di = DataImporter()
    di.setUploadContext(upload_id)
    if config.APP_DEBUG_MODE:
        print("Preparing for data import of", upload_id)
    result = di.verifyUploadPacket()
    if result[0]:
        if config.APP_DEBUG_MODE:
            print("Verified upload packet", result[1])
        result = di.checkForConflicts()
        if result[0]:
            if config.APP_DEBUG_MODE:
                print("Checked for conflicts", result[1])
            result = di.copyFilesIntoStorage()
            if result[0]:
                if config.APP_DEBUG_MODE:
                    print("Copied files into storage", result[1])
                fileInfo = di.getUploadFileInfo()
                # if fileInfo['clinical_trial'] == "CHIRP":
                #     # Only design for CHIRP data import
                #     result = di.insertCHIRPDataIntoDatabase()
                # elif fileInfo['file_type'] == "fraction_folder":
                #     result = di.insertFractionDataIntoDatabase()
                #     result2 = di.insertImagePathIntoDatabase()
                #     if config.APP_DEBUG_MODE:
                #         print("Inserted fraction data into database", result[1])
                #         print("Inserted image path into database", result2[1])
                # elif fileInfo['file_type'] == "image_folder":
                #     result = di.checkAndInsertFractionDataIntoDatabase()
                #     result2 = di.insertPatientLevelImagePathIntoDatabase()
                # elif fileInfo['file_type'] == "trajectory_log_folder":
                #     result = di.insertTrajectoryLogIntoDatabase()
                # elif fileInfo['file_type'] == "DVH_folder" or fileInfo['file_type'] == "DICOM_folder":
                    # result = di.insertDoseReconstrcutionFileIntoDatabase()
                # elif fileInfo['file_type'] == "triangulation_folder" or fileInfo['file_type'] == "kim_logs":
                #     result = di.checkAndInsertFractionDataIntoDatabase()
                #     result2 = di.insertFractionFilePathIntoDatabase()
                #     if config.APP_DEBUG_MODE:
                #         print("Inserted fraction data into database", result[1])
                #         print("Inserted image path into database", result2[1])
                result = di.insertMetadataIntoDatabase()
                if config.APP_DEBUG_MODE:
                    print("Inserted metadata into database", result[1])

    if not result[0]:
        print("Error importing data:", result[1])
        make_response({"status": "error", "message": result[1]})
    return redirect("/")

@app.route('/download/<path:filename>')
@autheticated_access
def downloadFile(filename):
    return send_from_directory(config.UPLOAD_FOLDER, filename)

@app.route('/tokens')
@autheticated_access
def showTokens():
    dbAdapter = DatabaseAdapter()
    return render_template('user_tokens.html', data=dbAdapter.getTokenDetails())


@app.route('/toggle-token/<token_id>')
@autheticated_access
def toggleToken(token_id):
    dbAdapter = DatabaseAdapter()
    result = dbAdapter.toggleTokenStatus(token_id)
    print(result)
    return redirect('/tokens')    


@app.route('/css/<path:path>')
def sendStylesheet(path):
    # print("CSS request:", path)
    return send_from_directory(config.JINJA_TEMPLATES_FOLDER + "/css", path)


@app.route('/js/<path:path>')
def sendJavaScript(path):
    # print("JavaScript request:", path)
    return send_from_directory(config.JINJA_TEMPLATES_FOLDER + "/js", path)


if __name__ == '__main__':
    app.run (host=config.LISTENING_HOST, 
            port=config.LISTENING_PORT, 
            debug=config.APP_DEBUG_MODE)
