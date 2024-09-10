from datetime import datetime as dt
from io import TextIOWrapper
import os
import json
from sys import stderr
from time import sleep
import msal
import requests
from typing import Dict, Callable
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from urllib.parse import urlparse, parse_qs
import asyncio


_onedriveClientInstance = None


def getOndriveClientInstance(applicaionId:str, clientSecret:str, newInstance=False):
    global _onedriveClientInstance
    if newInstance or _onedriveClientInstance is None:
        clientInstance = OnedriveClient(applicaionId, clientSecret)
        _onedriveClientInstance = clientInstance
    return _onedriveClientInstance


class CallbackURLHandler(SimpleHTTPRequestHandler):
    ignoreRequests = False
    def do_GET(self) -> None:
        if CallbackURLHandler.ignoreRequests:
            self.sendResponsePage(authSuccess=True)
        # print(self.headers, self.request)
        if _onedriveClientInstance is not None:
            # print("Got the request:", self.request)
            code = parse_qs(urlparse(self.path).query).get('code', None)
            if code is not None:
                self.sendResponsePage(authSuccess=True)
                CallbackURLHandler.ignoreRequests = True
                _onedriveClientInstance.setAuthorisationCode(code)
            else:
                print("Could not find code in the authorised URL", file=stderr)
                self.sendResponsePage(authSuccess=False)

    def sendResponsePage(self, authSuccess:bool=False):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        # print("Sending a response HTML page to the browser")
        authResultMessage = "Thanks for Authenticating" \
                if authSuccess else "Authentication Unsuccessful. Please try again."

        responseHtml = "<html> <head> <title>" \
                    + f"Authentication {'Successful' if authSuccess else 'Failed'} " \
                    + "</title> <style> " \
                    + ".message_area { " \
                    + "margin: auto; " \
                    + "text-align: center; " \
                    + "width: 50%; " \
                    + "border: 3px solid #1e5bdf; " \
                    + "padding: 10px; } " \
                    + ".button { " \
                    + "background-color: #1e5bdf; " \
                    + "border: none; " \
                    + "color: white; " \
                    + "padding: 10px 30px; " \
                    + "text-align: center; " \
                    + "text-decoration: none; " \
                    + "display: inline-block; " \
                    + "font-size: 16px; " \
                    + "border-radius: 10%; " \
                    + "outline-offset: 4px;} " \
                    + ".button:active { transform: translateY(2px); } " \
                    + ".err_text { color: red;} " \
                    + "</style> </head>" \
                    + "<body> <div class=\"message_area\"> " \
                    + "</strong {'class=\"err_text\"' if authSuccess else ''}> " \
                    + f"{authResultMessage}</strong> <br/> " \
                    + "You may close this window. " \
                    + "<br/><br/> " \
                    + "<button class=\"button\" onclick=\"window.close()\">Close</button> " \
                    + "</div> </body> </html>"

        self.wfile.write(bytes(responseHtml, "utf8"))

class OnedriveClient:
    BASE_URL = "https://graph.microsoft.com/v1.0/"  # This module uses the MS Graph API
    APP_SCOPES = ["User.Read", "Files.ReadWrite.All"]

    def __init__(self, applicaionId:str, clientSecret:str, 
                authorityUrl:str="https://login.microsoftonline.com/consumers/",
                localCallbackPort:int=8000) -> None:
        print("Creating new instance of OnedriveClient")
        self.applicaionId = applicaionId
        self.authorityUrl = authorityUrl
        self.clientSecret = clientSecret
        self.localCallbackPort = localCallbackPort
        self.accessToken = {}
        self.requestHeaders = {}
        self.currentSessionToken = None
        self.localAccessTokenPath = "microsoft_graph_token.json" 
        self._initialiseTokenCache()
        self.serverThread = None
        self.callbackServer = None
        # self._initialiseClientWithLocalToken()
        self._startCallbackServer()

    def __del__(self):
        if self.serverThread is not None:
            self.serverThread.join()

    def authenticateWithServer(self):
        self.clientInstance = msal.ConfidentialClientApplication(
                                client_id=self.applicaionId,
                                client_credential=self.clientSecret,
                                authority=self.authorityUrl)
        authReqURL = self.clientInstance.get_authorization_request_url(
                                                scopes=self.APP_SCOPES)
        print("opening the URL:", authReqURL)
        self.openURLinWebBrowser(authReqURL)
        authThread = Thread(self._authenticationThreadBody)
        authThread.start()
        authThread.join()  # block till the authentication process is complete

    def openURLinWebBrowser(self, url:str):
        chromePath = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe'
        if os.path.exists(chromePath):
            chromeInvocationCmd = f"{chromePath} %s --incognito"
            webbrowser.get(chromeInvocationCmd).open_new(url)
        else:
            webbrowser.open(url)

    def _authenticationThreadBody(self):
        """
        This function is meant to be called from the Python multithreading
        system and is not supposed to be called directly.
        """
        

    def _postAuthenticationCallback(self, request:Dict):
        print("callback function called with", request)

    def _runHttpCallback(self):
        self.callbackServer = HTTPServer(("localhost", self.localCallbackPort), 
                                    CallbackURLHandler)
        self.callbackServer.serve_forever()

    def _requestHttpServerToShutdownFromStopFunction(self):
        if self.callbackServer is not None:
            print("Waiting for a few seconds before sending the callback server a shutdown request")
            sleep(3)  # seconds
            print("Calling callbackServer.shutdown()")
            self.callbackServer.shutdown()
        else:
            print("self.callbackServer is None")
        print("After calling callbackServer.shutdown()")

    def _stopCallbackServer(self):
        print("Starting a new thread to request callback server to stop")
        shutdownThread = Thread(target=self._requestHttpServerToShutdownFromStopFunction)
        shutdownThread.start()
        shutdownThread.join()

    def _startCallbackServer(self):
        print("Starting a thread to run the Callback server")
        self.serverThread = Thread(target=self._runHttpCallback)
        self.serverThread.start()

    def _isLocalTokenValid(self, accessTokenFile:TextIOWrapper) -> bool:
        tokenDetail = json.load(accessTokenFile)
        tokenDetailKey = list(tokenDetail['AccessToken'].keys())[0]
        tokenExpiration = dt.fromtimestamp(int(tokenDetail['AccessToken'][tokenDetailKey]['expires_on']))
        if dt.now() > tokenExpiration:
            return False
        return True

    def _initialiseTokenCache(self):
        if os.path.exists(self.localAccessTokenPath):
            with open(self.localAccessTokenPath, 'r') as accessTokenFile:
                if self._isLocalTokenValid(accessTokenFile):
                    os.remove(self.localAccessTokenPath)
                    self._accessTokenCache = msal.SerializableTokenCache()
                else:
                    self._accessTokenCache.deserialize(accessTokenFile.read())
        else:
            self._accessTokenCache = msal.SerializableTokenCache()

    def _initialiseClientWithLocalToken(self):
        self.clientInstance = msal.PublicClientApplication(client_id=self.applicaionId, 
                                                token_cache=self._accessTokenCache)
        print(self.clientInstance)
        clientAccounts = self.clientInstance.get_accounts()
        print(clientAccounts)
        if clientAccounts:
            self.currentSessionToken = self.clientInstance.acquire_token_silent(
                                                            self.APP_SCOPES, 
                                                            clientAccounts[0])
        else:
            flow = self.clientInstance.initiate_device_flow(scopes=self.APP_SCOPES)
            print("flow:", flow)
            if "user_code" in flow:
                print("user_code: " + flow["user_code"])
                self.openURLinWebBrowser("https://microsoft.com/devicelogin")
                self.currentSessionToken = self.clientInstance.acquire_token_by_device_flow(flow)
            else:
                ...
        # self._saveAccessTokenLocally()

    def setAuthorisationCode(self, authCode:str):
        self.accessToken = self.clientInstance.acquire_token_by_authorization_code(
                                        code=authCode,
                                        scopes=self.APP_SCOPES)
        print("Access token:", self.accessToken)
        # self._stopCallbackServer()
        # self._saveAccessTokenLocally()
        self.requestHeaders = {
                "Authorization": "Bearer " + self.accessToken["access_token"]}
                #"Content-Type": "Application/json"}

        self.uploadFile("CT_15_01_1501006_DEIDENT_1667298.dcm", 
                     "/data_transfer/test_folder")
        # self.uploadAllFilesFromCurrentFolder()

    def _saveAccessTokenLocally(self):
        if self.accessToken:
            with open(self.localAccessTokenPath, 'w') as accessTokenFile:
                accessTokenFile.write(self._accessTokenCache.serialize())

    def getProfileInformation(self) -> Dict:
        endPoint = self.BASE_URL + "me"
        response = requests.get(endPoint, headers=self.requestHeaders)
        print(response)
        print(response.json())
        return response.json()

    def uploadFile(self, localFilePath:str, remoteFolderPath:str):
        print(f"Uploading {localFilePath}")
        # mimeType = magic.from_file(filename=localFilePath, mime=True)
        # requestHeader = self.requestHeaders.copy()
        # requestHeader["Content-Type"] = mimeType
        with open(localFilePath, 'rb') as uploadFile:
            uploadContent = uploadFile.read()
        filename = localFilePath.split('/')[-1]
        rsp = requests.put(self.BASE_URL \
                            + f"me/drive/items/root:{remoteFolderPath}/{filename}:/content",
                            headers=self.requestHeaders,
                            data=uploadContent)
        responseFromServer = rsp.json()
        print(responseFromServer)
        if "name" in responseFromServer and "size" in responseFromServer:
            if responseFromServer["name"] == filename:
                print(f"\n\n{30*'-'}\nFile Upload Test Successful\n{30*'-'}\n")
                return True
        return False

    def uploadAllFilesFromCurrentFolder(self):
        thisFileName = os.path.realpath(__file__)[-1]
        filesFromCurrentFolder = [os.path.join(os.getcwd(), f) \
                                    for f in os.listdir(os.getcwd()) \
                                        if os.path.isfile(os.path.join(os.getcwd(), f)) \
                                            and f.split('.')[-1] != "exe"]
        for fileForUpload in filesFromCurrentFolder:
            self.uploadFile(fileForUpload, "/data_transfer") 

    
