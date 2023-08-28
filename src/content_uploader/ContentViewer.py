from textwrap import indent
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QVBoxLayout, QWidget, \
    QPushButton, QLineEdit, QApplication, QLabel, QTableWidget, QTextEdit, \
    QTableWidgetItem, QAbstractItemView, QFileDialog, QFormLayout
from PySide6.QtCore import QFile, QRect, Slot, Signal, QModelIndex
from PySide6.QtGui import QPixmap, QScreen, QDesktopServices
from PySide6 import QtCore
from typing import Optional, List, Dict
import sys
# sys.path.insert(0, "..")
from ImagingDBClient import Clients
import re
from config import AppConfig
import json


def loadUiWidget(uifilename, parent=None):
    loader = QUiLoader()
    uifile = QFile(uifilename)
    uifile.open(QFile.ReadOnly)
    ui = loader.load(uifile, parent)
    uifile.close()
    return ui


class SettingsScreen(QWidget):
    settingsUpdated = Signal()

    def __init__(self, parent: Optional[QWidget] = None, appConfig = None) -> None:
        super().__init__(parent)
        self.appConfig = appConfig if appConfig is not None else AppConfig(appName="ContentViewer")
        self.initGUI()

    def initGUI(self):
        self.setWindowTitle("Settings")

        self.tokenFileLineEdit = QLineEdit()
        self.tokenFileLineEdit.setText(self.appConfig.getValue("/auth/tokenpath"))
        self.tokenFileLineEdit.setReadOnly(True)
        findTokenFilePushBtn = QPushButton("🗁") 
        findTokenFilePushBtn.setMaximumSize(30, findTokenFilePushBtn.height())
        findTokenFilePushBtn.clicked.connect(self.displayFileOpenDialog)
        tokenLayout = QHBoxLayout()
        tokenLayout.setContentsMargins(2, 0, 0, 0)
        tokenLayout.addWidget(self.tokenFileLineEdit)
        tokenLayout.addWidget(findTokenFilePushBtn)
        tokenFileHoldingWidget = QWidget()
        tokenFileHoldingWidget.setLayout(tokenLayout)

        # self.serviceUrl = QLineEdit("http://data-service-dev.ap-southeast-2.elasticbeanstalk.com")
        self.serviceUrl = QLineEdit(self.appConfig.getValue("/service/url"))

        tokenLayout = QFormLayout()
        tokenLayout.addRow("Access token:", tokenFileHoldingWidget)
        tokenLayout.addRow("Service URL:", self.serviceUrl)

        pushBtnSaveAndClose = QPushButton("Save And Close")
        pushBtnSaveAndClose.clicked.connect(self.saveSettingsAndClose)
        pushBtnCancel = QPushButton("Cancel")
        pushBtnCancel.clicked.connect(self.hide)
        buttonsLayout = QHBoxLayout()
        buttonsLayout.addStretch()
        buttonsLayout.addWidget(pushBtnSaveAndClose)
        buttonsLayout.addWidget(pushBtnCancel)

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(tokenLayout)
        mainLayout.addLayout(buttonsLayout)
        self.setLayout(mainLayout)

    @Slot()
    def displayFileOpenDialog(self):
        selectedPathTuple = QFileDialog.getOpenFileName(parent=self, \
                                                        caption="Access Token")
        self.tokenFilePath:str = selectedPathTuple[0]
        self.tokenFileLineEdit.setText(self.tokenFilePath.split('/')[-1])
        self.appConfig.setValue("/auth/tokenpath", self.tokenFilePath)

    @Slot()
    def saveSettingsAndClose(self):
        self.appConfig.setValue("/service/url", self.serviceUrl.text())
        self.appConfig.persistConfigSettings()
        self.hide()
        self.settingsUpdated.emit()


class ContentViewer(QWidget):
    def __init__(self, parent: Optional[QWidget]=None) -> None:
        super().__init__(parent=parent)
        self.initGUI()
        self.dbClient = Clients.ImagingDBClient()
        self.appConfig = AppConfig(appName="ContentViewer")
        self.reloadSettings()
        self.settingsScreen = SettingsScreen(appConfig=self.appConfig)
        self.settingsScreen.setVisible(False)
        self.settingsScreen.settingsUpdated.connect(self.reloadSettings)
        
    def initGUI(self) -> None:
        label = QLabel("URL:")
        self.lineEditURL = QLineEdit()
        self.pushBtnGo = QPushButton("Go")
        # self.pushBtnGo.clicked.connect(self.fetchContents)
        self.pushBtnGo.clicked.connect(self.getPatientDetails)
        self.pushBtnAuthenticate = QPushButton("🔐")
        self.pushBtnAuthenticate.setMaximumSize(30, self.pushBtnAuthenticate.height())
        self.pushBtnAuthenticate.clicked.connect(self.authenticateWithService)
        self.pushBtnSettings = QPushButton("🛠")
        self.pushBtnSettings.setMaximumSize(30, self.pushBtnSettings.height())
        self.pushBtnSettings.clicked.connect(self.displaySettingsScreen)
        self.lineEditURL.returnPressed.connect(self.pushBtnGo.click)

        self.dirListingTable = QTableWidget()
        self.dirListingTable.doubleClicked.connect(self.dirEntitySelectionAction)
        self.textContentDisplay = QTextEdit()
        self.textContentDisplay.setReadOnly(True)
        self.textContentDisplay.setVisible(False)
        self.imageDisplay = QLabel()
        self.imageDisplay.setVisible(False)
        self.labelStatus = QLabel("Ready")
        
        urlLayout = QHBoxLayout()
        urlLayout.addWidget(label)
        urlLayout.addWidget(self.lineEditURL)
        urlLayout.addWidget(self.pushBtnGo)
        urlLayout.addWidget(self.pushBtnAuthenticate)
        urlLayout.addWidget(self.pushBtnSettings)

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(urlLayout)
        mainLayout.addWidget(self.dirListingTable)
        mainLayout.addWidget(self.textContentDisplay)
        mainLayout.addWidget(self.imageDisplay)
        mainLayout.addWidget(self.labelStatus)

        self.setLayout(mainLayout)
        self.setWindowTitle("Imaging DB Folder API client")

    @Slot()
    def reloadSettings(self):
        self.dbClient.baseUrl = self.appConfig.getValue("/service/url")
        self.lineEditURL.setText(self.appConfig.getValue("/service/url"))

    @Slot()
    def authenticateWithService(self):
        tokenFilePath = self.appConfig.getValue("/auth/tokenpath")
        try:
            with open(tokenFilePath, 'r') as tokenFile:
                tokenStr = tokenFile.readline()
        except FileNotFoundError as fnfErr:
            print(f"Token file \'{tokenFilePath}\': {fnfErr}", file=sys.stderr)
            tokenStr = None
        self.dbClient.authToken = tokenStr
        self.dbClient.makeAuthRequest()

    @Slot()
    def getPatientDetails(self) -> None:
        if not self.dbClient.isAuthenticated:
            self.authenticateWithService()
        
        print(f"Fetching patient details from {self.lineEditURL.text()}")
        self.textContentDisplay.setVisible(False)
        self.imageDisplay.setVisible(False)

        self.labelStatus.setText("Calling service API")
        QApplication.instance().processEvents()
        resp = self.dbClient.getPatients()
        responseText = json.dumps(resp, indent=4)
        self.textContentDisplay.setText(responseText)
        self.textContentDisplay.setVisible(True)
        self.labelStatus.setText("Ready")

    @Slot()
    def fetchContents(self) -> None:
        if not self.dbClient.isAuthenticated:
            self.authenticateWithService()
        
        print(f"Fetching contents from {self.lineEditURL.text()}")
        self.textContentDisplay.setVisible(False)
        self.imageDisplay.setVisible(False)
        # self.dbClient.clearCache()
        self.labelStatus.setText("Making content request")
        QApplication.instance().processEvents()
        resp = self.dbClient.makeContentRequest(self.lineEditURL.text())
        self.labelStatus.setText("Ready")

        if resp[0] == Clients.ImagingDBClient.RESPONSE_TYPE_LISTING:
            self.updateDirListing(resp[2])
        elif resp[0] == Clients.ImagingDBClient.RESPONSE_TYPE_FILE:
            displaytext = "Only plain text files can be diplayed"
            if re.match("text/plain[\W]*", resp[1]):
                with open(resp[2], "r") as textFile:
                    displaytext = textFile.read()
                self.textContentDisplay.setText(displaytext)
                self.textContentDisplay.setVisible(True)
            elif re.match("image/[\W]*", resp[1]):
                pixmap = QPixmap()
                if not pixmap.load(resp[2]):
                    self.textContentDisplay.setText("Could not display image")
                    self.textContentDisplay.setVisible(True)
                else:
                    self.imageDisplay.setPixmap(pixmap)
                    self.imageDisplay.setVisible(True)
        elif resp[0] == Clients.ImagingDBClient.RESPONSE_TYPE_ERR:
            if "message" in resp[2]:
                self.labelStatus.setText(f"Encountered error: {resp[2]['message']}")
            else:
                self.labelStatus.setText(f"Unknown error encountered")

    @Slot()
    def displaySettingsScreen(self):
        self.settingsScreen.show()

    def updateDirListing(self, listing:Dict) -> None:
        self.currentListing = listing.copy()
        self.dirListingTable.setRowCount(len(listing["contents"]))
        self.dirListingTable.setColumnCount(5)
        self.dirListingTable.setSelectionBehavior(
                                QTableWidget.SelectionBehavior.SelectRows)
        header = self.dirListingTable.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        header.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        vHeader = self.dirListingTable.verticalHeader()
        vHeader.setVisible(False)
        self.dirListingTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.dirListingTable.setHorizontalHeaderLabels(
                ["Name", "Type", "Format", "Creation Time", "Size (bytes)"])
        for index, item in enumerate(listing["contents"]):
            # print(item)
            itemName = QTableWidgetItem(item["entity_name"])
            self.dirListingTable.setItem(index, 0, itemName)

            itemType = QTableWidgetItem(item["type"])
            self.dirListingTable.setItem(index, 1, itemType)
            
            itemFormat = QTableWidgetItem(item["format"] 
                                if item["type"] == "file" else "")
            self.dirListingTable.setItem(index, 2, itemFormat)
            
            itemTime = QTableWidgetItem(item["c_time"])
            self.dirListingTable.setItem(index, 3, itemTime)
            
            itemSize = QTableWidgetItem(str(item["size"])
                                if item["type"] == "file" else "")
            self.dirListingTable.setItem(index, 4, itemSize)

    @Slot()
    def dirEntitySelectionAction(self, modelIndex:QModelIndex) -> None:
        selectedURL = self.currentListing["contents"][modelIndex.row()]["full_path"]
        self.lineEditURL.setText(selectedURL)
        self.pushBtnGo.click()


def main(argv: List[str]):
    app = QApplication(argv)
    contentViewer = ContentViewer()
    contentViewer.setMinimumSize(640, 480)
    contentViewer.show()

    # mainWindow = loadUiWidget("ContentClient.ui", contentViewer)
    # mainWindow.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main(sys.argv)
