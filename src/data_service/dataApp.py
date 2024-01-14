from flask import Flask, make_response, send_from_directory, redirect, \
        request, render_template, Response, send_file
import config
from ClinicalTrials import ClinicalTrials
from os import path
from typing import List
from AccessManager import valid_token_required, processTokenRequestApplication, \
        accessManagerInstance, getSitesAndTrials, SitesAndTrials, getSites, \
        SiteDetails, getTrials, addSiteTrial, getTrialStructure, getContentUploaderTrial, addTrialStructure
import sys
from utils import make_csv
from ContentManager import ContentManager
from diagnostics import ServiceStatusAgent
from flask_cors import CORS

# from flask_mail import Mail


app = Flask(__name__, 
            static_folder=config.UI_DIR, 
            template_folder=config.JINJA_TEMPLATES_FOLDER)
CORS(app)
application = app  # required for making it work on AWS

# config.setMailConfig(app)
# mail = Mail()
# mail.init_app(app)

@app.route('/')
def root():
    print("Got a request for / : ", request.path)
    rsp = redirect('/index.html')
    return rsp


@app.route('/<path:urlPath>')
@valid_token_required
def process_request(urlPath):
    if config.APP_DEBUG_MODE:    
        print("Got a request for:", request.path)

    pathComponents = urlPath.split("/")
    requestedEndPoint = pathComponents[-1]
    try:
        trails = ClinicalTrials()
        data = trails.getEndpointData(requestedEndPoint, 
                                    request.args, 
                                    request.headers)
        print("args:", request.args)
        rsp = make_response(data)
        if "format" in request.args.keys():
            if request.args["format"] == "csv":
                if requestedEndPoint in data:
                    rsp = Response(make_csv(data[requestedEndPoint]), 
                                    mimetype="text/csv")
                    rsp.headers["x-suggested-filename"] = f"{requestedEndPoint}.csv"

    except Exception as ex:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = exc_tb.tb_frame.f_code.co_filename.split(path.sep)[-1]
        rsp = make_response({"error": "exception in server code", 
                            "exception": str(ex), 
                            "file": fname, 
                            "line": exc_tb.tb_lineno})
        print(str(ex), exc_type, fname, exc_tb.tb_lineno)

    rsp.headers['Access-Control-Allow-Origin'] = '*'
    return rsp


@app.route('/trials')
def getCatalogOfTrials():
    trails = getTrials()
    trails = {"trials": [trial.name for trial in trails]}
    rsp = make_response(trails)
    rsp.headers['Access-Control-Allow-Origin'] = '*'
    return rsp


@app.route('/sites')
def getCatalogOfSites():
    sites = getSites()
    sites = {"sites": [site.name for site in sites]}
    rsp = make_response(sites)
    rsp.headers['Access-Control-Allow-Origin'] = '*'
    return rsp

@app.route('/add-patient', methods=['GET', 'POST'])
@valid_token_required
def addPatient():
    if config.APP_DEBUG_MODE:
        print("Got a request to add a new patient")
        print(request.headers)

    contentType = request.headers.get("Content-Type")
    if contentType == "application/json":
        trials = ClinicalTrials()
        result = trials.addPatient(request.json)
        rsp = make_response({"success":result[0], "message":result[1]})
        if result[0]:
            rsp.status_code = 201
        rsp.headers['Access-Control-Allow-Origin'] = '*'
        return rsp
    
    rsp = make_response({"success":False, 
                        "message":"Content-Type:application/json expected"})
    rsp.headers['Access-Control-Allow-Origin'] = '*'
    return rsp


@app.route('/add-fraction', methods=['GET', 'POST'])
@valid_token_required
def addFraction():
    if config.APP_DEBUG_MODE:
        print("Got a request to add a new fraction")
        print(request.headers)

    contentType = request.headers.get("Content-Type")
    if contentType == "application/json":
        trails = ClinicalTrials()
        result = trails.addFraction(request.json)
        rsp = make_response({"success":result[0], "message":result[1]})
        if result[0]:
            rsp.status_code = 201
        rsp.headers['Access-Control-Allow-Origin'] = '*'
        return rsp
    
    rsp = make_response({"success":False, 
                        "message":"Content-Type:application/json expected"})
    rsp.headers['Access-Control-Allow-Origin'] = '*'
    return rsp


@app.route('/apidoc')
def renderAPIDocs():
    try:
        return render_template("apis.html", 
                            apis=ClinicalTrials.getAPIFieldMapping())
    except Exception as ex:
        print("error in render template " + str(ex))
        rsp = make_response({"Exception caught": str(ex)})
        return rsp
    return None


@app.route('/server_info')
def sendServerInfo():
    serverInfo = {
        "current dir": path.abspath("."),
        "jinja template path": app.template_folder
        }
    rsp = make_response(serverInfo)
    rsp.headers['Access-Control-Allow-Origin'] = '*'
    return rsp


@app.route('/index.html')
def sendClinicalTrialsPage():
    return render_template('welcome.html')


@app.route('/content/<path:urlPath>')
@valid_token_required
def contentRequestHandler(urlPath):
    if config.APP_DEBUG_MODE:
        print("Got a request for:", request.path)
        print("UrlPath:", urlPath)
    contentMgr = ContentManager()
    return contentMgr.processRequest(urlPath, request.host_url + "content/")


@app.route('/upload/getUploadContext', methods=['GET', 'POST'])
@valid_token_required
def generateUploadContext():
    contentMgr = ContentManager()
    uploadContext:str = contentMgr.generateUploadId()
    if config.APP_DEBUG_MODE:
        print(f"Generated a new upload context: {uploadContext}")
    return make_response({"context":uploadContext, "status": "success"})


@app.route('/upload/<path:urlPath>', methods=['GET', 'POST'])
@valid_token_required
def contentUploadHandler(urlPath):
    if config.APP_DEBUG_MODE:
        print("Got a upload request for:", request.path)
        print("UrlPath:", urlPath)
    contentMgr = ContentManager()
    # contentMgr.setMailAgent(mail)
    return contentMgr.acceptAndSaveFile(request)


@app.route('/auth', methods=["POST"])
def authenticateAndCreateSession():
    if config.APP_DEBUG_MODE:
        print("Got an authentication request", request.headers)
    
    if "Token" in request.headers:
        authTokenParam = request.headers["Token"]
    else:
        return make_response({
                    "token":"", 
                    "status": "failure", 
                    "error" :"Authentication token missing in request"})

    status, sessionToken, message = accessManagerInstance.getSessionToken(authTokenParam)
    if not status:
        return make_response({
                    "token":sessionToken, 
                    "status": "failure", 
                    "error" :message})
    return make_response({"token":sessionToken, "status": "success"})


@app.route('/missing-data/<path:urlPath>')
@valid_token_required
def findMissingData(urlPath):
    if config.APP_DIAGNOSTICS_MODE:
        statusAgent = ServiceStatusAgent()
        if "format" in request.args.keys() and request.args["format"] == "csv":
            data = statusAgent.getMissingData(level=urlPath, 
                                        requestParams=request.args)
            rsp = Response(make_csv(data["records"]), mimetype="text/csv")
            rsp.headers["x-suggested-filename"] = f"missing_data_{urlPath}.csv"
        else:
            data = statusAgent.getMissingData(level=urlPath, 
                                        requestParams=request.args)

            if "debug" in request.args.keys() and request.args["debug"] == "true":
                rsp = make_response(data)
            else:
                rsp = render_template("missing_data.html", data=data)
    else:
        return make_response({"error": "Not Supported in current configuration"})
    return rsp


@app.route('/apply-access', methods=["GET", "POST"])
def applyForAccess():
    print("Got request for apply-access", request.headers, request.args)
    sitesAndTrials:SitesAndTrials = getSitesAndTrials()
    if request.method == "POST":
        result, formData = processTokenRequestApplication(request.form)
        if result["status"]:
            return render_template("token_download.html", 
                                    encodedToken=result["token"], 
                                    profile=result["profile"])
        else:
            return render_template("token_apply.html", 
                                    input_errors=result["input_errors"],
                                    form_data=formData,
                                    site_and_trial_data=sitesAndTrials)
    else:
        try:
            return render_template("token_apply.html", 
                                    input_errors={}, 
                                    form_data={},
                                    site_and_trial_data=sitesAndTrials)
        except Exception as ex:
            print("error in render template " + str(ex))
            rsp = make_response({"Exception caught": str(ex)})
            return rsp


@app.route('/profile/<path:profileName>')
def sendProfile(profileName):
    print(f"Got request for profile download: {profileName}")
    return send_file(config.TEMP_CACHE_PATH + '/' + profileName)


@app.route('/show-uploads')
def showUploads():
    contentMgr = ContentManager()
    # rsp = make_response({"uploads": contentMgr.uploadsSubmitted()})
    rsp = render_template("uploads.html", data={"uploads": contentMgr.uploadsSubmitted()})
    return rsp


@app.route('/upload-details/<path:urlPath>')
def showUploadDetails(urlPath:str):
    contentMgr = ContentManager()
    rsp = make_response({"files": contentMgr.uploadDetails(urlPath)})
    return rsp

@app.route('/trial-structure/<path:trialName>')
def queryTrialStructure(trialName:str):
    trailStructure = getTrialStructure(trialName)
    rsp = make_response(trailStructure)
    return rsp

@app.route('/trial-structure/contentUploader/<path:trialName>')
def queryTrialStructureForContentUploader(trialName:str):
    trailStructure = getContentUploaderTrial(trialName)
    rsp = make_response(trailStructure)
    return rsp

@app.route('/trial-structure/addNewTrial', methods=["POST"])
def queryAddNewTrial():
    if config.APP_DEBUG_MODE:
        print("Got an add new trial request", request.headers)
    print(request.json)
    result = addTrialStructure(request.json)
    rsp = make_response({"status": result[0], "message": result[1]})
    rsp.headers['Access-Control-Allow-Origin'] = '*'
    return rsp

@app.route('/add-site-trial', methods=['POST'])
def addSiteTrialEntry():
    if config.APP_DEBUG_MODE:
        print("Got a request to add a new site trial")
        print(request.headers)
    result = addSiteTrial(request.json)
    rsp = make_response({"success":result[0], "message":result[1]})
    rsp.headers['Access-Control-Allow-Origin'] = '*'
    return rsp

if __name__ == '__main__':
    if config.APP_DEBUG_MODE:
        app.run (host=config.LISTENING_HOST, 
                port=config.LISTENING_PORT, 
                debug=config.APP_DEBUG_MODE)
    else:
        from waitress import serve
        serve(app, host=config.LISTENING_HOST, port=config.LISTENING_PORT)
