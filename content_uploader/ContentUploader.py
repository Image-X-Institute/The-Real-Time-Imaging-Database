from sqlite3 import connect
from turtle import clearscreen, isvisible, width
from typing import Dict, List, Optional, Tuple, overload
import PySide6
from PySide6.QtWidgets import QApplication, QCheckBox, QLineEdit, QMessageBox, \
    QProgressBar, QPushButton, QSpinBox, QWidget, QGridLayout, \
    QFrame, QLabel, QVBoxLayout, QSizePolicy, QHBoxLayout, QFormLayout, \
    QComboBox, QSizePolicy, QFileDialog, QTableWidget, QTableWidgetItem, \
    QAbstractItemView, QHeaderView, QDateEdit, QCalendarWidget, QGroupBox, \
    QRadioButton, QTextEdit
from PySide6.QtGui import QDrag, QDragEnterEvent, QDropEvent, QDragMoveEvent, \
    QDragLeaveEvent, QPalette, QPaintEvent, QPainter, QShowEvent, QColor, \
    QDoubleValidator
from PySide6.QtCore import QUrl, SignalInstance, Slot, QMimeData, Signal, Qt, \
    QRect, QPoint, QSize, QDate

import sys
from ImagingDBClient import Clients
from urllib.parse import urlparse, unquote 
import os
import platform
import magic   # provides functionality similar to Unix's file command
from ProfileManager import ProfileManager
import json


class ClinicalTrialsMetaData:
    def __init__(self) -> None:
        self.fileTypes = {
            "RT Plan DICOM": {
                "level": "prescription", 
                "key":"rt_plan_path",
                "field_type": "file",
                "allowed":["application/dicom"]
            }, 
            "Pre-treatment CT series": {
                "level": "prescription", 
                "key":"rt_ct_path",
                "field_type": "folder",
                "allowed":["application/dicom"]
            },
            "RT Structure set DICOM": {
                "level": "prescription", 
                "key":"rt_structure_path", 
                "field_type": "file",
                "allowed":["application/dicom"]
            },
            "RT Dose DICOM": {
                "level": "prescription", 
                "key":"rt_dose_path",
                "field_type": "file", 
                "allowed":["application/dicom"]
            },
            "Pre-treatment MRI series": {
                "level": "prescription", 
                "key":"rt_mri_path", 
                "field_type": "folder",
                "allowed":["application/dicom"]
            },
            "cumulative DVH": {
                "level": "prescription", 
                "key":"planned_dvh_path",
                "field_type": "file",
                "allowed":["text/plain"]
            },
            "Patient Centroid": {
                "level": "prescription", 
                "key":"centroid_path",
                "field_type": "file",
                "allowed":["text/plain"]
            },
            "Miscellanious files (patient level)": {
                "level": "prescription", 
                "key":"other",
                "field_type": "file",
                "denied": ["application/x-dosexec", 
                            "application/vnd.microsoft.portable-executable", 
                            "text/x-shellscript", 
                            "application/x-sh", 
                            "application/x-csh", 
                            "text/javascript"
                ]
            },
            "Fraction Folder (Images Only)": {
                "level":"fraction",
                "key":"fraction_folder",
                "field_type":"folder",
                "allowed":[
                    "text/plain", 
                    "image/tiff", 
                    "application/dicom", 
                    "application/octet-stream",
                    "text/xml",
                ]
            },
            "KIM log files": {
                "level": "fraction", 
                "key":"kim_logs",
                "field_type": "file",
                "allowed":["text/plain", "text/csv"]
            }, 
            # "kV images": {
            #     "level": "fraction", 
            #     "key":"kv_images",
            #     "field_type": "folder",
            #     "allowed":["image/tiff", 
            #                 "application/dicom", 
            #                 "application/octet-stream",
            #                 "text/plain",
            #                 "text/xml",
            #     ]
            # }, 
            # "MV Images": {
            #     "level": "fraction", 
            #     "key":"mv_images",
            #     "field_type": "folder",
            #     "allowed":["image/tiff", 
            #                 "application/dicom", 
            #                 "application/octet-stream",
            #                 "text/plain",
            #                 "text/xml",
            #     ]
            # }, 
            "Metrics Spreadsheet": {
                "level": "fraction", 
                "key":"metrics",
                "field_type": "file",
                "allowed": ["text/plain", 
                            "application/vnd.ms-excel", 
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                            "application/vnd.oasis.opendocument.spreadsheet", 
                            "text/csv"
                ]		
            }, 
            "Triangulation Spreadsheet": {
                "level": "fraction", 
                "key":"triangulation",
                "field_type": "file",
                "allowed": ["text/plain", 
                            "application/vnd.ms-excel", 
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                            "application/vnd.oasis.opendocument.spreadsheet", 
                            "text/csv"
                ]
            }, 
            "trajectory log files": {
                "level": "fraction", 
                "key":"trajectory_logs", 
                "field_type": "file",
                "allowed":["application/octet-stream", 
                            "application/zip", 
                            "application/x-7z-compressed", 
                            "application/gzip", 
                            "application/x-bzip2", 
                            "application/x-bzip"
                ]
            }, 
            "fraction level DVH (tracked)": {
                "level": "fraction", 
                "key":"DVH_track_path",
                "field_type": "file",
                "allowed":["text/plain"]
            }, 
            "fraction level DVH (not tracked)": {
                "level": "fraction", 
                "key":"DVH_no_track_path", 
                "field_type": "file",
                "allowed":["text/plain"]
            }, 
            "DICOM plan for dose per fraction (tracked)": {
                "level": "fraction", 
                "key":"DICOM_track_plan_path", 
                "field_type": "file",
                "allowed":["application/dicom"]
            },
            "DICOM plan for dose per fraction (not tracked)": {
                "level": "fraction", 
                "key":"DICOM_no_track_plan_path", 
                "field_type": "file",
                "allowed":["application/dicom"]
            },
            "Miscellanious files (fraction level)": {
                "level": "fraction", 
                "key":"other",
                "field_type": "file",
                "denied": ["application/x-dosexec", 
                            "application/vnd.microsoft.portable-executable", 
                            "text/x-shellscript", 
                            "application/x-sh", 
                            "application/x-csh", 
                            "text/javascript"
                ]
            }
        }
        self.centres = ["Select Centre", 
                        "CMN", 
                        "Liverpool", 
                        "RNSH", 
                        "PMC", 
                        "Westmead", 
                        "Nepean", 
                        "PAH", 
                        "Blacktown",
                        "VCU",
                        "TestCentre_1"]
        
        self.trials = ["Select Trial", 
                        "SPARK", 
                        "LARK", 
                        "VCU_P4", 
                        "CHIRP", 
                        "MANGO", 
                        "SpanC",
                        "VALKIM",
                        "MAGIK",
                        "DB_TEST"]

    def fetchMetadata(self, patientTrialId:str) -> bool:
        return False

    def getFileTypesSupported(self) -> List[str]:
        return self.fileTypes.keys()

    def getMatchingFileTypes(self, mimeType) -> List[str]:
        matchingFileTypes = []
        for fileType, fileTypeDetails in self.fileTypes:
            if mimeType not in fileTypeDetails["denied"] or \
                            mimeType in fileTypeDetails["allowed"]:
                matchingFileTypes.append(fileType)
        return matchingFileTypes

    def getLevelofFileType(self, fileType:str) -> str:
        return self.fileTypes[fileType]["level"]

    def getKeywordForFileType(self, fileType:str) -> str:
        return self.fileTypes[fileType]["key"]

    def getListOfTestCentres(self) -> List[str]:
        return self.centres

    def getListofTrials(self) -> List[str]:
        return self.trials

    def getFractionNames(self) -> List[str]:
        return ["Fraction", "FX01", "FX02", "FX03", "FX04", "FX05"]
    
    def getSubFractionNames(self) -> List[str]:
        return ["Sub-Fraction", "A", "B", "C"]


class LoginScreen(QWidget):
    authorisationRequested:SignalInstance = Signal()

    def __init__(self, parent: Optional[QWidget]=None) -> None:
        super().__init__(parent=parent)
        self.tokenFilePath = ""
        self.selectedProfileDetails = {}
        self.treatmentCentreName = ""
        self.serverInstanceName = ""
        self.profileMgr = None
        self._initGUI()

    def _initGUI(self):
        self.setWindowTitle("Uploader Authentication")

        headingLabel = QLabel("<strong>Please select the profile and enter " \
                                + "the password below to login</strong>")
        headingLabel.setWordWrap(True)
        horizontalLine = QFrame()
        horizontalLine.setFrameShape(QFrame.HLine)
        
        self.tokenFileLineEdit = QLineEdit("Select a profile --->")
        self.tokenFileLineEdit.setReadOnly(True)
        self.profileVerificationLabel = QLabel(" ")
        findTokenFilePushBtn = QPushButton("🗁") 
        findTokenFilePushBtn.setMaximumSize(30, findTokenFilePushBtn.height())
        findTokenFilePushBtn.clicked.connect(self.displayFileOpenDialog)
        tokenLayout = QHBoxLayout()
        tokenLayout.setContentsMargins(2, 0, 0, 0)
        tokenLayout.addWidget(self.tokenFileLineEdit)
        tokenLayout.addWidget(self.profileVerificationLabel)
        tokenLayout.addWidget(findTokenFilePushBtn)
        tokenFileHoldingWidget = QWidget()
        tokenFileHoldingWidget.setLayout(tokenLayout)

        self.passwordLineEdit = QLineEdit()
        self.passwordLineEdit.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.decodeProfilePushBtn = QPushButton("➪") 
        self.decodeProfilePushBtn.setMaximumSize(30, self.decodeProfilePushBtn.height())
        self.decodeProfilePushBtn.clicked.connect(self.decodeProfile)
        self.passwordLineEdit.returnPressed.connect(self.decodeProfilePushBtn.click)
        self.decodeProfilePushBtn.setEnabled(False)

        passwordLayout = QHBoxLayout()
        passwordLayout.setContentsMargins(2, 0, 0, 0)
        passwordLayout.addWidget(self.passwordLineEdit)
        passwordLayout.addWidget(QLabel(" "))
        passwordLayout.addWidget(self.decodeProfilePushBtn)
        passwordHoldingWidget = QWidget()
        passwordHoldingWidget.setLayout(passwordLayout)

        self.connectionProfileBox = QComboBox()
        self.connectionProfileBox.setEditable(False)
        self.connectionProfileBox.currentIndexChanged.connect(self.selectedProfileIndexChanged)

        tokenLayout = QFormLayout()
        tokenLayout.addRow("Profile:", tokenFileHoldingWidget)
        tokenLayout.addRow("Secret:", passwordHoldingWidget)
        tokenLayout.addRow("Connection:", self.connectionProfileBox)

        self.pushBtnLogin = QPushButton("Login")
        self.pushBtnLogin.clicked.connect(self.initiateLogin)
        self.pushBtnLogin.setEnabled(False)
        pushBtnCancel = QPushButton("Cancel")
        pushBtnCancel.clicked.connect(self.close)
        buttonsLayout = QHBoxLayout()
        buttonsLayout.addStretch()
        buttonsLayout.addWidget(self.pushBtnLogin)
        buttonsLayout.addWidget(pushBtnCancel)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(headingLabel)
        mainLayout.addWidget(horizontalLine)
        mainLayout.addLayout(tokenLayout)
        mainLayout.addLayout(buttonsLayout)
        self.setLayout(mainLayout)

    @Slot()
    def selectedProfileIndexChanged(self, index: int):
        if self.profileMgr is not None:
            allProfileDetails = self.profileMgr.getAllProfileDetails()
            if allProfileDetails:
                self.selectedProfileDetails = allProfileDetails[index]

    @Slot()
    def decodeProfile(self):
        self.profileMgr = ProfileManager(self.tokenFilePath, 
                                    self.passwordLineEdit.text().encode("utf-8"))
        if self.profileMgr.isValid:
            self.profileVerificationLabel.setText("✔️")
            self.pushBtnLogin.setEnabled(True)
            self.connectionProfileBox.addItems(self.profileMgr.getConnectionProfileNames())
            defaultIndex = self.profileMgr.getDefaultConnectionProfileIndex()
            self.serverInstanceName = self.profileMgr.getServerInstanceName()
            if defaultIndex >= 0:
                self.connectionProfileBox.setCurrentIndex(defaultIndex)
                self.selectedProfileDetails = self.profileMgr.getDefaultConnectionProfile()

    @Slot()
    def displayFileOpenDialog(self):
        selectedPathTuple = QFileDialog.getOpenFileName(parent=self, \
                                                        caption="Connection Profile")
        self.tokenFilePath:str = selectedPathTuple[0]
        self.tokenFileLineEdit.setText(self.tokenFilePath.split('/')[-1])
        self.profileVerificationLabel.setText(" ")
        self.connectionProfileBox.clear()
        self.pushBtnLogin.setEnabled(False)
        self.decodeProfilePushBtn.setEnabled(True)

    @Slot()
    def initiateLogin(self):
        self.authorisationRequested.emit()

    def _readTokenFromFile(self) -> str:
        try:
            with open(self.tokenFilePath, 'r') as tokenFile:
                tokenStr = tokenFile.readline()
        except FileNotFoundError as fnfErr:
            print(f"Token file {self.tokenFilePath} not found")
            tokenStr = None
        return tokenStr

class AddSubFractionScreen(QWidget):
    addSubFraction:SignalInstance = Signal(dict)
    def __init__(self, parent: Optional[QWidget]=None) -> None:
        super().__init__(parent)
        self.initGUI()

    def initGUI(self):
        self.setWindowFlags(self.windowFlags() & Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMinMaxButtonsHint)
        self.setWindowTitle("Add Sub-Fraction")

        self.fractionNameInput = QLineEdit("Fx1")

        fractionDetailsLayout = QFormLayout()
        fractionDetailsLayout.addRow("Name:", self.fractionNameInput)

        self.pushBtnAdd = QPushButton("Add Fraction")
        self.pushBtnAdd.clicked.connect(self.addFractionSlot)
        pushBtnCancel = QPushButton("Cancel")
        pushBtnCancel.clicked.connect(self.close)
        buttonsLayout = QHBoxLayout()
        buttonsLayout.addStretch()
        buttonsLayout.addWidget(self.pushBtnAdd)
        buttonsLayout.addWidget(pushBtnCancel)

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(fractionDetailsLayout)
        mainLayout.addLayout(buttonsLayout)
        self.setLayout(mainLayout)
        
    @Slot()
    def addFractionSlot(self):
        subFractionDetails = { 
                "name": self.fractionNameInput.text(), 
                }
        self.addSubFraction.emit(subFractionDetails)
 
    

class AddFractionScreen(QWidget):
    addFraction:SignalInstance = Signal(dict)

    def __init__(self, parent: Optional[QWidget]=None) -> None:
        super().__init__(parent)
        self.initGUI()

    def initGUI(self):
        self.setWindowFlags(self.windowFlags() & Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMinMaxButtonsHint)
        self.setWindowTitle("Add Fraction")

        self.fractionNumberInput = QSpinBox()
        self.fractionNumberInput.setMinimum(0)
        self.fractionNumberInput.setValue(1)
        self.fractionNumberInput.valueChanged.connect(self.fractionNumberChanged)

        self.fractionNameInput = QLineEdit("Fx1")

        self.fractionDateInput = QCalendarWidget()

        fractionDetailsLayout = QFormLayout()
        fractionDetailsLayout.addRow("Number:", self.fractionNumberInput)
        fractionDetailsLayout.addRow("Name:", self.fractionNameInput)
        fractionDetailsLayout.addRow("Date:", self.fractionDateInput)

        self.pushBtnAdd = QPushButton("Add Fraction")
        self.pushBtnAdd.clicked.connect(self.addFractionSlot)
        pushBtnCancel = QPushButton("Cancel")
        pushBtnCancel.clicked.connect(self.close)
        buttonsLayout = QHBoxLayout()
        buttonsLayout.addStretch()
        buttonsLayout.addWidget(self.pushBtnAdd)
        buttonsLayout.addWidget(pushBtnCancel)

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(fractionDetailsLayout)
        mainLayout.addLayout(buttonsLayout)
        self.setLayout(mainLayout)

    @Slot()
    def addFractionSlot(self):
        fractionDetails = { "number": self.fractionNumberInput.value(), 
                "name": self.fractionNameInput.text(), 
                "date": self.fractionDateInput.selectedDate().toString("dd-MMM-yyyy")
                }
        self.addFraction.emit(fractionDetails)

    @Slot(int)
    def fractionNumberChanged(self, value:int):
        self.fractionNameInput.setText(f"Fx{value}")

class AddPatientScreen(QWidget):
    addPatient:SignalInstance = Signal(dict)

    def __init__(self, parent: Optional[QWidget]=None) -> None:
        super().__init__(parent)
        self.trialsMetaData = ClinicalTrialsMetaData()
        self.initGUI()

    def initGUI(self):
        self.setWindowFlags(self.windowFlags() & Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMinMaxButtonsHint)
        self.setWindowTitle("Add Patient")

        infolabel = QLabel("Please enter the patient details carefully. " \
                    "If in doubt, please enquire with the trial coordinator.")
        infolabel.setWordWrap(True)

        horizontalLine = QFrame()
        horizontalLine.setFrameShape(QFrame.HLine)

        self.patientTrialIdLineEdit = QLineEdit()

        self.testCentreSelector = QComboBox()
        self.testCentreSelector.addItems(self.trialsMetaData.getListOfTestCentres())

        self.trialSelector = QComboBox()
        self.trialSelector.addItems(self.trialsMetaData.getListofTrials())

        self.tumourSiteSelector = QComboBox()
        self.tumourSiteSelector.addItems(["Select Anatomy", "Head and Neck", 
                                            "Lungs", "Liver", "Pancreas", 
                                            "Prostate", "Other"])

        self.patientSeqInput = QSpinBox()
        self.patientSeqInput.setMinimum(1)

        patientDetailsLayout = QHBoxLayout()
        patientDetailsLayout.addWidget(QLabel("Patient Clinical Trial ID:"))
        patientDetailsLayout.addWidget(self.patientTrialIdLineEdit)

        trialDetailsLayout = QHBoxLayout()
        trialDetailsLayout.addWidget(QLabel("Trial:"))
        trialDetailsLayout.addWidget(self.trialSelector)
        trialDetailsLayout.addWidget(QLabel("Tumour Site:"))
        trialDetailsLayout.addWidget(self.tumourSiteSelector)

        testCentreLayout = QHBoxLayout()
        testCentreLayout.addWidget(QLabel("Centre:"))
        testCentreLayout.addWidget(self.testCentreSelector)
        testCentreLayout.addWidget(QLabel("Patient Sequence:"))
        testCentreLayout.addWidget(self.patientSeqInput)

        self.linacTypeSelector = QComboBox()
        self.linacTypeSelector.addItems(["Select LINAC Make and Type",
                                        "ADAC Pinnacle3", "Elekta Infinity",
                                        "Elekta Versa HD", "Elekta Harmony",
                                        "Elekta Unity", "Varian Halcyon",
                                        "Varian TrueBeam", "Varian VitalBeam",
                                        "Varian Medical Systems ARIA RadOnc",
                                        "Radiation Therapy not involved"])

        linacTypeLayout = QHBoxLayout()
        linacTypeLayout.addWidget(QLabel("Type of LINAC:"))
        linacTypeLayout.addWidget(self.linacTypeSelector)

        numMarkersLayout = QHBoxLayout()
        numMarkersLayout.addWidget(QLabel("Number of markers in target region:"))
        self.numMarkersInput = QSpinBox()
        self.numMarkersInput.setMinimum(0)
        numMarkersLayout.addWidget(self.numMarkersInput)

        treatmentTimelayout = QHBoxLayout()
        treatmentTimelayout.addWidget(QLabel("Average treatment time:"))
        self.avgTreatTimeHoursInput = QSpinBox()
        self.avgTreatTimeHoursInput.setMinimum(0)
        self.avgTreatTimeMinsInput = QSpinBox()
        self.avgTreatTimeMinsInput.setMinimum(0)
        self.avgTreatTimeMinsInput.setMaximum(59)
        treatmentTimelayout.addWidget(self.avgTreatTimeHoursInput)
        treatmentTimelayout.addWidget(QLabel("hours"))
        treatmentTimelayout.addWidget(self.avgTreatTimeMinsInput)
        treatmentTimelayout.addWidget(QLabel("minutes"))

        kimAccuracyLayout = QHBoxLayout()
        kimAccuracyLayout.addWidget(QLabel("KIM Accuracy:"))
        self.kimAccuracyInput = QLineEdit()
        kimAccuracyValidator = QDoubleValidator(0.0, 100.0, 2)
        self.kimAccuracyInput.setValidator(kimAccuracyValidator)
        kimAccuracyLayout.addWidget(self.kimAccuracyInput)

        treatmentOptionsBox = QGroupBox("Treatment Specific")
        treatmentOptMainLayout = QVBoxLayout()
        treatmentOptMainLayout.addLayout(linacTypeLayout)
        treatmentOptMainLayout.addLayout(numMarkersLayout)
        treatmentOptMainLayout.addLayout(treatmentTimelayout)
        treatmentOptMainLayout.addLayout(kimAccuracyLayout)
        treatmentOptionsBox.setLayout(treatmentOptMainLayout)

        patientAgeLayout = QHBoxLayout()
        patientAgeLayout.addWidget(QLabel("Age at the time of treatment:"))
        self.ageSelector = QComboBox()
        self.ageSelector.addItem("Unknown")
        self.ageSelector.addItems([str(age) for age in range(0, 126)])
        patientAgeLayout.addWidget(self.ageSelector)

        genderOptionsBox = QGroupBox("Select Gender:")
        genderOptionsLayout = QHBoxLayout()
        self.genderOptionUnknown = QRadioButton("Prefer not to disclose")
        self.genderOptionUnknown.setChecked(True)
        self.genderOptionMale = QRadioButton("Male")
        self.GenderOptionFemale = QRadioButton("Female")
        self.genderOptionOther = QRadioButton("Other")
        
        genderOptionsLayout.addWidget(self.genderOptionUnknown)
        genderOptionsLayout.addWidget(self.genderOptionMale)
        genderOptionsLayout.addWidget(self.GenderOptionFemale)
        genderOptionsLayout.addWidget(self.genderOptionOther)
        genderOptionsBox.setLayout(genderOptionsLayout)

        self.clinicalDiagInput = QTextEdit()

        clinicalDiagLayout = QHBoxLayout()
        clinicalDiagLayout.addWidget(QLabel("Clinical Diagnosis:"))
        clinicalDiagLayout.addWidget(self.clinicalDiagInput)

        optionalDetailsBox = QGroupBox("Optional Patient Details")
        optDetailsMainLayout = QVBoxLayout()
        optDetailsMainLayout.addLayout(patientAgeLayout)
        optDetailsMainLayout.addWidget(genderOptionsBox)
        optDetailsMainLayout.addLayout(clinicalDiagLayout)
        optionalDetailsBox.setLayout(optDetailsMainLayout)

        self.pushBtnAdd = QPushButton("Add Patient")
        self.pushBtnAdd.clicked.connect(self.addPatientSlot)
        pushBtnCancel = QPushButton("Cancel")
        pushBtnCancel.clicked.connect(self.close)
        buttonsLayout = QHBoxLayout()
        buttonsLayout.addStretch()
        buttonsLayout.addWidget(self.pushBtnAdd)
        buttonsLayout.addWidget(pushBtnCancel)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(infolabel)
        mainLayout.addWidget(horizontalLine)
        mainLayout.addLayout(patientDetailsLayout)
        mainLayout.addLayout(trialDetailsLayout)
        mainLayout.addLayout(testCentreLayout)
        mainLayout.addWidget(treatmentOptionsBox)
        mainLayout.addWidget(optionalDetailsBox)
        mainLayout.addLayout(buttonsLayout)
        self.setLayout(mainLayout)

    def showEvent(self, ev:QShowEvent):
        if self.isVisible():
            self.clearScreen()
        return super().showEvent(ev)

    @Slot(str)
    def setPatientTrialId(self, id: str):
        self.patientTrialIdPrompt = id

    @Slot()
    def clearScreen(self):
        self.patientTrialIdLineEdit.setText(self.patientTrialIdPrompt)
        self.testCentreSelector.setCurrentIndex(0)
        self.trialSelector.setCurrentIndex(0)
        self.tumourSiteSelector.setCurrentIndex(0)
        self.patientSeqInput.clear()
        self.linacTypeSelector.setCurrentIndex(0)
        self.numMarkersInput.clear()
        self.avgTreatTimeHoursInput.setValue(0)
        self.avgTreatTimeMinsInput.setValue(0)
        self.kimAccuracyInput.clear()
        self.ageSelector.setCurrentIndex(0)
        self.genderOptionUnknown.setChecked(True)
        self.clinicalDiagInput.clear()

    def _validateInput(self) -> str:
        validationMessage = ''
        if self.patientTrialIdLineEdit.text().strip() == '':
            validationMessage += "The Patient ID should not be empty\n"
        if self.trialSelector.currentIndex() == 0:
            validationMessage += "Please select a Trial\n"
        if self.testCentreSelector.currentIndex() == 0:
            validationMessage += "Please select a Treatment Centre\n"
        if self.tumourSiteSelector.currentIndex() == 0:
            validationMessage += "Please select an anatomical region of treatment\n"
        if self.linacTypeSelector.currentIndex() == 0:
            validationMessage += "Please select the LINAC Type\n"
        return validationMessage

    @Slot()
    def addPatientSlot(self):
        validationResult = self._validateInput()
        if validationResult != '':
            QMessageBox.warning(self, "Add Patient", 
                    f"Following error(s) enoucountered:\n{validationResult}")
            return

        genderValue = ''
        if self.genderOptionMale.isChecked():
            genderValue = 'M'
        elif self.GenderOptionFemale.isChecked():
            genderValue = 'F'
        elif self.genderOptionOther.isChecked():
            genderValue = 'O'

        kimAccuracy = 0.0
        if len(self.kimAccuracyInput.text()) > 0:
            kimAccuracy = float(self.kimAccuracyInput.text())

        patientDetails = {
            "patient": {
                "patient_trial_id": self.patientTrialIdLineEdit.text(),
                "clinical_trial": self.trialSelector.currentText(),
                "test_centre": self.testCentreSelector.currentText(),
                "centre_patient_no": self.patientSeqInput.value(),
                "tumour_site": self.tumourSiteSelector.currentText(),
                "number_of_markers": self.numMarkersInput.value(),
                "avg_treatment_time": \
                    f"00 {self.avgTreatTimeHoursInput.text()}:{self.avgTreatTimeMinsInput.text()}:00",
                "kim_accuracy": kimAccuracy
            },
            "prescription": {
                "LINAC_type": self.linacTypeSelector.currentText()
            }
        }
        if self.ageSelector.currentText() != "Unknown":
            patientDetails["patient"]["age"] = int(self.ageSelector.currentText())

        if genderValue != '':
            patientDetails["patient"]["gender"] = genderValue

        self.patientTrialIdPrompt = ''
        self.addPatient.emit(patientDetails)


class UploadDataScreen(QWidget):
    readyForUpload:SignalInstance = Signal()

    def __init__(self, parent: Optional[QWidget]=None) -> None:
        super().__init__(parent)
        self.trialsMetaData = ClinicalTrialsMetaData()
        self.dbClient = Clients.ImagingDBClient()
        self.uploadQueue:List[Dict] = []
        self.currentlyUploading = False
        self.cancelRequest = False
        self.isPatientIdValidated = False
        self.currentProfile = None
        self._initGUI()

        self.loginScreen = LoginScreen()
        self.loginScreen.setMinimumWidth(380)
        self.loginScreen.authorisationRequested.connect(self.requestAuth)
        self.loginScreen.show()

        self.addFractionScreen = AddFractionScreen()
        self.addFractionScreen.setVisible(False)
        self.addFractionScreen.addFraction.connect(self.addNewFraction)
        
        self.addSubFractionScreen = AddSubFractionScreen()
        self.addSubFractionScreen.setVisible(False)
        self.addSubFractionScreen.addSubFraction.connect(self.addNewSubFraction)
        

        self.addPatientScreen = AddPatientScreen()
        self.addPatientScreen.setVisible(False)
        self.addPatientScreen.addPatient.connect(self.addNewPatient)

    def closeEvent(self, event):
        for window in QApplication.topLevelWidgets():
            window.close()        
    
    def _initGUI(self):
        self.setWindowTitle("Upload Patient Data")
        self.instanceNameLabel= QLabel("", alignment=Qt.AlignmentFlag.AlignHCenter)
        self.instanceNameLabel.setStyleSheet("font-weight:bold")
        infolabel = QLabel("Please enter details related to the files chosen " \
            "below to help assign them to the correct patient data records.")
        infolabel.setWordWrap(True)

        horizontalLine = QFrame()
        horizontalLine.setFrameShape(QFrame.HLine)

        self.testCentreSelector = QComboBox()
        self.testCentreSelector.addItems(self.trialsMetaData.getListOfTestCentres())

        self.fileTypeSelector = QComboBox()
        self.fileTypeSelector.addItems(self.trialsMetaData.getFileTypesSupported())
        self.fileTypeSelector.setMaximumWidth(200)
        self.fileTypeSelector.currentTextChanged.connect(self.fileTypeSelected)

        self.trialSelector = QComboBox()
        self.trialSelector.addItems(self.trialsMetaData.getListofTrials())

        self.fractionSelector = QComboBox()
        self.fractionSelector.addItems(self.trialsMetaData.getFractionNames())
        self.fractionSelector.currentTextChanged.connect(self.fractionSelected)
        self.fractionSelector.setDisabled(True)


        addFractionPushBtn = QPushButton("+")
        addFractionPushBtn.setMaximumSize(30, addFractionPushBtn.height())
        addFractionPushBtn.clicked.connect(self.showNewFractionScreen)

        self.subFractionSelector = QComboBox()
        self.subFractionSelector.addItems(self.trialsMetaData.getSubFractionNames())
        addSubFractionPushBtn = QPushButton("+")
        addSubFractionPushBtn.setMaximumSize(30, addSubFractionPushBtn.height())
        addSubFractionPushBtn.clicked.connect(self.showNewSubFractionScreen)
        self.subFractionSelector.setDisabled(True)

        self.patientTrialIdLineEdit = QLineEdit()

        self.patientIdVerifiedIndicator = QLabel()
        
        verifyIdPushBtn = QPushButton("⟲")
        verifyIdPushBtn.setMaximumSize(30, verifyIdPushBtn.height())
        verifyIdPushBtn.clicked.connect(self.fetchPatientDetails)
        self.patientTrialIdLineEdit.returnPressed.connect(verifyIdPushBtn.click)

        self.patientSequenceInput = QSpinBox()

        patientIdLayout = QHBoxLayout()
        patientIdLayout.addWidget(QLabel("Patient clinical trial ID:"))
        patientIdLayout.addWidget(self.patientIdVerifiedIndicator)
        patientIdLayout.addWidget(self.patientTrialIdLineEdit)
        patientIdLayout.addWidget(verifyIdPushBtn)
        patientIdLayout.addSpacing(20)
        patientIdLayout.addWidget(QLabel("Patient Sequence:"))
        patientIdLayout.addWidget(self.patientSequenceInput)

        self.uploadQueueTable = QTableWidget()
        self.initialiseUploadQueueTable()

        testCentreLayout = QHBoxLayout()
        testCentreLabel = QLabel("Test Centre:")
        testCentreLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        testCentreLayout.addWidget(testCentreLabel)
        testCentreLayout.addWidget(self.testCentreSelector)
        testCentreLayout.addSpacing(20)
        trialNameLabel = QLabel("Trial Name:")
        trialNameLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        testCentreLayout.addWidget(trialNameLabel)
        testCentreLayout.addWidget(self.trialSelector)

        inputLayout = QGridLayout()
        fileTypeLayout = QHBoxLayout()
        typeofFileLabel = QLabel("Type of file:")
        typeofFileLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        fileTypeLayout.addWidget(typeofFileLabel)
        fileTypeLayout.addWidget(self.fileTypeSelector)

        mainFractionLayout = QHBoxLayout()
        fractionLabel = QLabel("Fraction:")
        fractionLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        mainFractionLayout.addWidget(fractionLabel)
        mainFractionLayout.addWidget(self.fractionSelector)
        mainFractionLayout.addWidget(addFractionPushBtn)

        subFractionLayout = QHBoxLayout()
        subFractionLabel = QLabel("Sub-Fraction:")
        subFractionLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        subFractionLayout.addWidget(subFractionLabel)
        subFractionLayout.addWidget(self.subFractionSelector)
        subFractionLayout.addWidget(addSubFractionPushBtn)

        inputLayout.addLayout(fileTypeLayout, 0, 0)
        inputLayout.addLayout(mainFractionLayout, 0, 1)
        inputLayout.addLayout(subFractionLayout, 1, 1)
        inputLayout.setVerticalSpacing(0)

        self.dropArea = DropArea()
        self.dropArea.signalFilesDropped.connect(self.filesDropped)

        self.droppedFileLabel = QLabel()
        self.droppedFileLabel.setWordWrap(True)
        self.droppedFileLabel.setSizePolicy(QSizePolicy.Expanding, 
                                            QSizePolicy.Preferred)

        addFilesPushBtn = QPushButton("Add Files")
        addFilesPushBtn.clicked.connect(self.addEntryForUpload)

        addFilesFrameLayout = QVBoxLayout()
        addFilesFrameLayout.addLayout(inputLayout)
        addFilesFrameLayout.addWidget(QLabel("Please drag and drop files/folders " \
                                            "to be uploaded in the area below:"))
        addFilesFrameLayout.addWidget(self.dropArea)
        addFilesButtonLayout = QHBoxLayout()
        addFilesButtonLayout.addWidget(self.droppedFileLabel)
        addFilesButtonLayout.addWidget(addFilesPushBtn)
        addFilesFrameLayout.addLayout(addFilesButtonLayout)

        addFilesFrame = QFrame()
        addFilesFrame.setFrameShape(QFrame.Box)
        addFilesFrame.setLayout(addFilesFrameLayout)

        progressLayout = QFormLayout()
        self.overallProgress = QProgressBar()
        progressLayout.addRow("Overall:", self.overallProgress)
        self.fileUploadProgress = QProgressBar()
        progressLayout.addRow("Files:", self.fileUploadProgress)

        self.checkboxAnonymise = QCheckBox("Anonymise")
        self.checkboxAnonymise.setChecked(False)
        self.checkboxAnonymise.setEnabled(False)
        self.pushBtnUpload = QPushButton("Upload")
        self.pushBtnUpload.setEnabled(False)
        self.pushBtnUpload.clicked.connect(self.uploadButtonClicked)
        pushBtnCancel = QPushButton("Cancel")
        pushBtnCancel.clicked.connect(self.cancelButtonClicked)
        buttonsLayout = QHBoxLayout()
        buttonsLayout.addStretch()
        buttonsLayout.addWidget(self.checkboxAnonymise)
        buttonsLayout.addWidget(self.pushBtnUpload)
        buttonsLayout.addWidget(pushBtnCancel)

        statusSeperatorLine = QFrame()
        statusSeperatorLine.setFrameShape(QFrame.HLine)
        self.statusLabel = QLabel("Ready")

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.instanceNameLabel)
        mainLayout.addWidget(infolabel)
        mainLayout.addWidget(horizontalLine)
        mainLayout.addLayout(patientIdLayout)
        mainLayout.addLayout(testCentreLayout)
        mainLayout.addWidget(addFilesFrame)
        mainLayout.addWidget(self.uploadQueueTable)
        mainLayout.addLayout(progressLayout)
        mainLayout.addLayout(buttonsLayout)
        mainLayout.addWidget(statusSeperatorLine)
        mainLayout.addWidget(self.statusLabel)
        self.setLayout(mainLayout)

    def initialiseUploadQueueTable(self):
        self.uploadQueueTable.setColumnCount(5)
        self.uploadQueueTable.setSelectionBehavior(
                                QTableWidget.SelectionBehavior.SelectRows)
        header = self.uploadQueueTable.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        vHeader = self.uploadQueueTable.verticalHeader()
        vHeader.setVisible(False)
        self.uploadQueueTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.uploadQueueTable.setHorizontalHeaderLabels(
                ["File/Folder", "Type", "Fraction", "Number of files", "Total Size"])

    def _getSelectedFileNames(self, filePaths:List[str]) -> str:
        selectedFilenames:str = ""
        if len(filePaths) > 1:
            firstFile = filePaths[0].split('/')[-1]
            lastFile = filePaths[-1].split('/')[-1]
            selectedFilenames = f"{firstFile} ... {lastFile}"
        else:
            filename = self.dropArea.droppedFiles[0].split('/')[-1]
            selectedFilenames = f"{filename}"
        return selectedFilenames

    def _checkForAllowedFileTypes(self, path:str, allowedFileTypes:List[str],
                                        deniedFileTypes:List[str]=[]) -> bool:
        # print(f"Looking at {path}; allowed: {allowedFileTypes}, denied: {deniedFileTypes}")
        if os.path.isfile(path):
            mimeType:str = magic.from_file(filename=path, mime=True)
            # print(f"{path} has mime type: {mimeType}")
            if mimeType in deniedFileTypes:
                print(f"Found {path} with MIME:{mimeType} in the denied list, not queuing file.")
                return False
            elif mimeType in allowedFileTypes:
                # print(f"Found {mimeType} in the allowed list.")
                return True
            elif not allowedFileTypes:
                return True
        return False

    def _getNumberofFilesPathsAndTotalSize(self, paths:List[str], 
                                            allowedFileTypes:List[str],
                                            deniedFileTypes:List[str]=[]
                                            ) -> Tuple[int, List[str], int]:
        numberOfFiles:int = 0
        totalSize:int = 0
        files:List[str] = []
        QApplication.setOverrideCursor(Qt.WaitCursor)
        for path in paths:
            if os.path.isdir(path):
                for dirpath, dirnames, filenames in os.walk(path):
                    QApplication.instance().processEvents()
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        if self._checkForAllowedFileTypes(filepath, 
                                                    allowedFileTypes, 
                                                    deniedFileTypes):
                            totalSize += os.stat(filepath).st_size
                            numberOfFiles += 1
                            files.append(filepath)
            else:
                if self._checkForAllowedFileTypes(path, 
                                            allowedFileTypes, 
                                            deniedFileTypes):
                    totalSize += os.stat(path).st_size
                    numberOfFiles += 1
                    files.append(path)
        QApplication.restoreOverrideCursor()
        return numberOfFiles, files, totalSize

    def _getHumanFriendlyFileSize(self, fileSizeInBytes:int) -> str:
        units = ["bytes", "KB", "MB", "GB", "TB"]
        for unit in units:
            if fileSizeInBytes < 1024 or unit == units[-1]:
                humanFriendlySize = f"{fileSizeInBytes:.2f} {unit}"
                break
            else:
                fileSizeInBytes /= 1024
        return humanFriendlySize


    def _hideLoginScreenAndShowSelf(self):
        if not self.isVisible():
            self.show()
        self.loginScreen.close()

    @Slot()
    def requestAuth(self):
        if self.loginScreen.isVisible():
            if not self.loginScreen.selectedProfileDetails:
                QMessageBox.warning(self, "Connection Profile Not Available",
                                    "Please select a connection profile")
                return
            self.currentProfile = self.loginScreen.selectedProfileDetails
            self.instanceNameLabel.setText(self.loginScreen.serverInstanceName)
            if self.currentProfile["connection_type"] == "DIRECT" \
                    or self.currentProfile["connection_type"] == "IMPORT_ONLY":
                self.dbClient.baseUrl = self.currentProfile["url"]
                # self.dbClient.baseUrl = "http://10.48.16.163:8090"
                self.dbClient.authToken = self.currentProfile["token"]
                if not self.dbClient.makeAuthRequest(
                        {"password": self.currentProfile["password"]}):
                    QMessageBox.warning(self, "Authentication Failed",
                                        "Please make sure that the correct token " \
                                        ", password and URL are entered")
                else:
                    self._hideLoginScreenAndShowSelf()
            else:
                QMessageBox.warning(self, "Unsupported Connection Profile",
                                    "The selected connection profile is not supported")

    @Slot()
    def fetchPatientDetails(self):
        self.statusLabel.setText("Querying server")
        QApplication.instance().processEvents()
        patientTrialId = self.patientTrialIdLineEdit.text().strip()
        patDetails = self.dbClient.getPatientDetails(patientTrialId)
        
        self.isPatientIdValidated = False
        self.patientIdVerifiedIndicator.setText("")
        if "patients" in patDetails:
            if len(patDetails["patients"]) > 0:
                for patient in patDetails["patients"]:
                    self.patientSequenceInput.setValue(patient["patient_no"])
                    self.testCentreSelector.setCurrentText(patient["test_centre"])
                    self.trialSelector.setCurrentText(patient["trial"])
                    self.statusLabel.setText("Ready")
                    self.updateFractionsListForCurrentPatient()
                    self.isPatientIdValidated = True
                    self.patientIdVerifiedIndicator.setText("✔️")
                    break  # use the first match 
            else:
                self.statusLabel.setText("No matching patient information found")
        else:
            self.statusLabel.setText("Invalid response format from server")

        if not self.isPatientIdValidated:
            response:QMessageBox.StandardButton = QMessageBox.question(self, 
                                "No Matching Patient Found", 
                                "No patients matching the patient trial ID " \
                                f"{patientTrialId} are found.\n Would you " \
                                "like to create a new patient using this ID?")

            affirmativeResponses = [QMessageBox.StandardButton.Yes, 
                                    QMessageBox.StandardButton.Ok, 
                                    QMessageBox.StandardButton.YesAll, 
                                    QMessageBox.StandardButton.YesToAll,
                                    QMessageBox.StandardButton.Apply]
            if response in affirmativeResponses:
                # QMessageBox.information(self, "Adding a new patient",
                #                     "The workflow for adding new patients " \
                #                     "is not yet implemented in this version.\n" \
                #                     "This is a placeholder for the add patient " \
                #                     "screen. Please check for this functionality " \
                #                     "in future versions of this tool.")
                self.showAddPatientScreen()

    @Slot()
    def fetchFractionDetails(self):
        fracDetails = self.dbClient.getFractionDetailsForPatient(
                                            self.patientTrialIdLineEdit.text())
        fractionsAvailable = ["Fraction"]
        if "fractions" in fracDetails:
            for fraction in fracDetails["fractions"]:
                if not f'FX{fraction["fraction_no"]}' in fractionsAvailable:
                    fractionsAvailable.append(f'FX{fraction["fraction_no"]}')
        return fractionsAvailable
    
    @Slot()
    def fetchSubFractionDetails(self):
        fracDetails = self.dbClient.getFractionDetailsForPatient(
                                            self.patientTrialIdLineEdit.text())
        subFractionsDetails = {
            "subFractionsAvailable": ["Sub-Fraction"]
        }
        fractionNumber = self.fractionSelector.currentText().split("FX")[-1]
        if "fractions" in fracDetails:
            for fraction in fracDetails["fractions"]:
                if fractionNumber and fraction["fraction_no"] == int(fractionNumber):
                    subFractionsDetails["subFractionsAvailable"].append(fraction["fraction_name"])
                    subFractionsDetails["date"] = fraction["date"]
                    subFractionsDetails["patient_trial_id"] = fraction["patient_trial_id"]
                    subFractionsDetails["number"] = fraction["fraction_no"]
        return subFractionsDetails


    @Slot()
    def updateFractionsListForCurrentPatient(self):
        self.fractionSelector.clear()
        fractionsAvailable = self.fetchFractionDetails()
        for index,frac in enumerate(fractionsAvailable):
            self.fractionSelector.insertItem(index, frac)

    @Slot()
    def updateSubFractionsListForCurrentPatient(self):
        self.subFractionSelector.clear()
        subFractionsDetails = self.fetchSubFractionDetails()
        for index,subFrac in enumerate(subFractionsDetails["subFractionsAvailable"]):
            self.subFractionSelector.insertItem(index, subFrac)

    @Slot()
    def showAddPatientScreen(self):
        self.addPatientScreen.setPatientTrialId(self.patientTrialIdLineEdit.text())
        self.addPatientScreen.setVisible(True)
        windowGeometry = self.addPatientScreen.geometry()
        windowGeometry.moveCenter(self.geometry().center())
        self.addPatientScreen.setGeometry(windowGeometry)
        self.statusLabel.setText("Prompting for new patient creation")

    @Slot(dict)
    def addNewPatient(self, patientDetails:Dict):
        print("Got patient details:", patientDetails)
        result:Clients.Result = self.dbClient.addPatient(patientDetails)
        if not result.success:
            QMessageBox.warning(self.addPatientScreen, "Adding Patient", 
                                "The new patient could not be added: " \
                                    + result.message )
            self.statusLabel.setText("Patient could not added")
        else:
            self.addPatientScreen.setVisible(False)
            self.patientTrialIdLineEdit.setText(patientDetails["patient"]["patient_trial_id"])
            self.fetchPatientDetails()
            self.statusLabel.setText(
                f"Newly added Patient {patientDetails['patient']['patient_trial_id']} selected")

    @Slot()
    def showNewFractionScreen(self):
        self.addFractionScreen.setVisible(True)
        windowGeometry = self.addFractionScreen.geometry()
        windowGeometry.moveCenter(self.geometry().center())
        self.addFractionScreen.setGeometry(windowGeometry)
        
    @Slot()
    def showNewSubFractionScreen(self):
        self.addSubFractionScreen.setVisible(True)
        windowGeometry = self.addSubFractionScreen.geometry()
        windowGeometry.moveCenter(self.geometry().center())
        self.addSubFractionScreen.setGeometry(windowGeometry)
    
    def _getNewSubFractionName(self, fractionDetails:Dict):
        subFractionList = sorted(fractionDetails["subFractionsAvailable"])
        fractionNumber = fractionDetails["number"]
        subFractionList.remove("Sub-Fraction")
        if len(subFractionList) == 0:
            newSubFraction = f'Fx{fractionNumber}-A'
        else:
            lastSubFraction = subFractionList[-1].split("-")[-1]
            newSubFraction = f'Fx{fractionNumber}-{chr(ord(lastSubFraction)+1)}'
        return newSubFraction
    
    @Slot()
    def addNewSubFraction(self, subFractionDetail:Dict):
        subFractionDetail["patient_trial_id"] = self.patientTrialIdLineEdit.text()
        subFractionDetail["number"] = int(self.fractionSelector.currentText().split("FX")[-1])
        fractionDetails = self.fetchSubFractionDetails()
        fractionDetailsPackage = {
            "patient_trial_id": subFractionDetail["patient_trial_id"],
            "number": subFractionDetail["number"],
            "name":  subFractionDetail ["name"],
            "date": fractionDetails["date"],
        }
        result:Clients.Result = self.dbClient.addFraction(fractionDetailsPackage)
        if not result.success:
            QMessageBox.warning(self.addFractionScreen, "Adding sub-fraction", 
                                "The new sub-fraction could not be added: " \
                                    + result.message )
            self.statusLabel.setText("Sub-fraction could not added")
        else:
            self.addSubFractionScreen.setVisible(False)
            self.updateSubFractionsListForCurrentPatient()


    @Slot(dict)
    def addNewFraction(self, fractionDetails:Dict):
        fractionDetails["patient_trial_id"] = self.patientTrialIdLineEdit.text()
        print("Got fraction details:", fractionDetails)
        result:Clients.Result = self.dbClient.addFraction(fractionDetails)
        if not result.success:
            QMessageBox.warning(self.addFractionScreen, "Adding fraction", 
                                "The new fraction could not be added: " \
                                    + result.message )
            self.statusLabel.setText("Fraction could not added")
        else:
            self.addFractionScreen.setVisible(False)
            self.updateFractionsListForCurrentPatient()

    @Slot()
    def filesDropped(self):
        print(f"dropped {len(self.dropArea.droppedFiles)} files/dirs for upload")
        self.droppedFileLabel.setText(
                f"{self._getSelectedFileNames(self.dropArea.droppedFiles)} " \
                f"({len(self.dropArea.droppedFiles)} files/folders)")

    @Slot()
    def addEntryForUpload(self):
        print(f"Using connection type: {self.currentProfile['connection_type']}")
        if not self.isPatientIdValidated:
            QMessageBox.warning(self, "Set Patient Information", 
                            "Please select a valid patient trial ID (or " \
                            "create a new one) before adding files for upload.")
            return
        
        # if self.currentProfile["connection_type"] == "IMPORT_ONLY":
        #     response = QMessageBox.question(self, "Upload All Files", 
        #                     "The current implementation of this tool would " \
        #                     "anyway initiate a full copy of the files during " \
        #                     "import. If this is not be the behaviour you " \
        #                     "expect then please select No.\n " \
        #                     "Do you want to proceed with uploading all " \
        #                     "the files?")
        #     if response == QMessageBox.StandardButton.No:
        #         return

        self.statusLabel.setText("Queuing files for upload")
        proposedCategory = self.fileTypeSelector.currentText()
        allowedFileTypes = self.trialsMetaData.fileTypes[proposedCategory]["allowed"] \
                            if "allowed" in self.trialsMetaData.fileTypes[proposedCategory] \
                            else []
        deniedFileTypes = self.trialsMetaData.fileTypes[proposedCategory]["denied"] \
                            if "denied" in self.trialsMetaData.fileTypes[proposedCategory] \
                            else []

        numFiles, files, size = self._getNumberofFilesPathsAndTotalSize(
                                                self.dropArea.droppedFiles, 
                                                allowedFileTypes, 
                                                deniedFileTypes)
        if self.currentProfile["connection_type"] == "DIRECT" and numFiles < 1:
            self.statusLabel.setText("Please select valid files for upload")
            self.pushBtnUpload.setEnabled(False)
            return
        else:
            self.pushBtnUpload.setEnabled(True)

        lastRowIndex = self.uploadQueueTable.rowCount() 
        self.uploadQueueTable.insertRow(self.uploadQueueTable.rowCount())
        itemName = QTableWidgetItem(
                    self._getSelectedFileNames(self.dropArea.droppedFiles))
        self.uploadQueueTable.setItem(lastRowIndex, 0, itemName)
        itemName = QTableWidgetItem(proposedCategory)
        self.uploadQueueTable.setItem(lastRowIndex, 1, itemName)
        level = self.trialsMetaData.getLevelofFileType(
                                        self.fileTypeSelector.currentText())
        itemName = QTableWidgetItem(self.fractionSelector.currentText() \
                                        if level == "fraction" else "N/A")
        self.uploadQueueTable.setItem(lastRowIndex, 2, itemName)
        itemName = QTableWidgetItem(str(numFiles))
        self.uploadQueueTable.setItem(lastRowIndex, 3, itemName)
        itemName = QTableWidgetItem(self._getHumanFriendlyFileSize(size))
        self.uploadQueueTable.setItem(lastRowIndex, 4, itemName)

        uploadEntity = {
            "data": {
                "test_centre": self.testCentreSelector.currentText(),
                "patient_trial_id": self.patientTrialIdLineEdit.text(),
                "centre_patient_no": self.patientSequenceInput.value(),
                "level": self.trialsMetaData.getLevelofFileType(
                                        self.fileTypeSelector.currentText()),
                "file_type": self.trialsMetaData.getKeywordForFileType(
                                        self.fileTypeSelector.currentText()),
                "fraction": self.fractionSelector.currentText() \
                        if self.fractionSelector.currentText() != "Fraction" \
                        else "N/A",
                "sub_fraction": self.subFractionSelector.currentText() \
                        if self.subFractionSelector.currentText() != "Sub-Fraction" \
                        else "N/A",
                "clinical_trial": self.trialSelector.currentText(),
            },
            "files": files,
            "uploaded": False
        }
        self.uploadQueue.append(uploadEntity)
        self.statusLabel.setText("Ready")
        self.droppedFileLabel.clear()
        self.dropArea.clear()

    @Slot()
    def removeEntryFromUploadTable(self):
        pass

    @Slot(str)
    def fileTypeSelected(self, fileType:str):
        if self.trialsMetaData.getLevelofFileType(fileType) == "fraction":
            self.fractionSelector.setEnabled(True)
        else:
            self.fractionSelector.setCurrentText("Fraction")
            self.subFractionSelector.setCurrentText("Sub-Fraction")
            self.fractionSelector.setEnabled(False)
            self.subFractionSelector.setEnabled(False)

    @Slot(str)
    def fractionSelected(self, fraction:str):
        if fraction == "Fraction":
            self.subFractionSelector.setEnabled(False)
        else:
            self.updateSubFractionsListForCurrentPatient()
            self.subFractionSelector.setEnabled(True)

    @Slot()
    def getPatientDetails(self):
        pass

    def _enterTransferringState(self) -> bool:
        if self.currentlyUploading:
            response:QMessageBox.StandardButton = QMessageBox.question(
                                self, "Currently uploading",
                                "files are currently being uploaded. " \
                                "Are you sure you want to start uploading?")
            if response == QMessageBox.No or response == QMessageBox.Abort:
                return False
                
        self.pushBtnUpload.setEnabled(False)
        self.statusLabel.setText("Uploading files")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.overallProgress.setRange(0, len(self.uploadQueue))
        self.overallProgress.setValue(0)
        self.fileUploadProgress.setValue(0)
        self.currentlyUploading = True
        self.cancelRequest = False
        return True

    def _exitTransferringState(self) -> bool:
        self.cancelRequest = False
        if self.currentlyUploading:
            response:QMessageBox.StandardButton = QMessageBox.question(
                                self, "Currently uploading",
                                "files are currently being uploaded. " \
                                "Are you sure you want to Stop uploading?")
            if response == QMessageBox.No or response == QMessageBox.Abort:
                return False
            else:
                self.close()
        
        self.pushBtnUpload.setEnabled(True)
        self.currentlyUploading = False
        QApplication.restoreOverrideCursor()
        self.overallProgress.setValue(0)
        self.fileUploadProgress.setValue(0)
        self.statusLabel.setText("Ready")
        return True

    def _getTrialPathForImportOnlyMode(self) -> str:
        QMessageBox.information(self, "Locate Trail Folder", 
                        "Please select the Clinical Trial folder for " \
                        f"{self.trialSelector.currentText()} from the " \
                        "filesystem. This could be on a mapped drive.")
        
        trialFolderPath = QFileDialog.getExistingDirectory(self, 
                                            caption="Select Trial Folder")
        print(f"{trialFolderPath}")
        return trialFolderPath

    @Slot()
    def uploadButtonClicked(self) -> None:
        if self.currentProfile["connection_type"] == "IMPORT_ONLY":
            trialFolderPath = self._getTrialPathForImportOnlyMode()
            if not os.path.isdir(trialFolderPath):
                QMessageBox.warning(self, "Cannot Locate Folder", 
                                    f"The path {trialFolderPath} cannot be located. " \
                                    "Please select a valid path.")
                return

        if not self._enterTransferringState():
            return
        uploadContext:str = self.dbClient.acquireUploadContext()
        for uploadEntityCounter, uploadEntity in enumerate(self.uploadQueue):
            if uploadEntity["uploaded"] == True:
                continue

            allFilesUploaded:bool = True
            if self.currentProfile["connection_type"] == "IMPORT_ONLY":
                uploadEntity["data"]["upload_context"] = uploadContext
                data = uploadEntity["data"].copy()
                updatedPaths = [f.replace(trialFolderPath, "") for f in uploadEntity["files"]]
                data["files"] = json.dumps(updatedPaths)
                print(data["files"])
                status = self.dbClient.uploadContent(data=data, 
                                                uploadOnlyMetadata=True)
            else:
                self.fileUploadProgress.setRange(0, len(uploadEntity["files"]))
                for uploadFileCounter, uploadFilePath in enumerate(uploadEntity["files"]):

                    if self.cancelRequest:
                        if self._exitTransferringState():
                            return

                    filename = uploadFilePath.split("/")[-1]
                    fileptr = open(uploadFilePath, "rb")
                    uploadEntity["data"]["file_path"] = uploadFilePath
                    uploadEntity["data"]["upload_context"] = uploadContext
                    status = self.dbClient.uploadContent(files={filename: fileptr}, 
                                                        data=uploadEntity["data"])
                    if not status:
                        self.statusLabel.setText(f"Error uploading {filename}" \
                                                    ", trying others")
                    else:
                        self.fileUploadProgress.setValue(uploadFileCounter + 1)
                    
                    allFilesUploaded = status and allFilesUploaded
                    QApplication.instance().processEvents()

            if allFilesUploaded:
                uploadEntity["uploaded"] = True
                self.uploadQueueTable.removeRow(0)  # the topmost row
                self.overallProgress.setValue(uploadEntityCounter + 1)
            QApplication.instance().processEvents()
        
        self.currentlyUploading = False
        self._exitTransferringState()

    @Slot()
    def cancelButtonClicked(self):
        if self.currentlyUploading:
            self.cancelRequest = True
        else:
            self.close()


class DropArea(QFrame):
    signalFilesDropped = Signal()

    def __init__(self, parent: Optional[QWidget]=None) -> None:
        super().__init__(parent=parent)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.droppedFiles:List[str] = []

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat("text/uri-list"):
            event.acceptProposedAction()
        return super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        if event.mimeData().hasFormat("text/uri-list"):
            self.droppedFiles.clear()
            for fileURL in event.mimeData().text().split("\n"):
                if fileURL.strip() != "\n":
                    localFilePath = QUrl(fileURL).toLocalFile()
                    self.droppedFiles.append(localFilePath)
            self.signalFilesDropped.emit()
            event.accept()
            self.update()
            
        return super().dropEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.drawRect(1, 1, self.width() -2, self.height() -2)

        cx = int(self.width()/2)
        cy = int(self.height()/2)
        lineWidth = int(self.width()/10)
        lineHeight = int(self.height()/10)
        lineWidth = lineHeight if lineHeight < lineWidth else lineWidth
        lineHeight = lineWidth if lineWidth < lineHeight else lineHeight

        if len(self.droppedFiles) > 0:  # display an X (not expecting drops)
            painter.drawLine(cx - lineWidth, cy - lineHeight, 
                            cx + lineWidth, cy + lineHeight)
            painter.drawLine(cx + lineWidth, cy - lineHeight, 
                            cx - lineWidth, cy + lineHeight)
        else:  # display a + (as a drop target)
            painter.drawLine(cx, cy - lineHeight, cx, cy + lineHeight)
            painter.drawLine(cx - lineWidth, cy, cx + lineWidth, cy)
        painter.end()
        return super().paintEvent(event)

    @Slot()
    def clear(self):
        self.droppedFiles.clear()
        self.update()


def main(argv: List[str]):
    app = QApplication(argv)

    uploadDetailsScreen = UploadDataScreen()
    uploadDetailsScreen.setMinimumSize(600, 600)
    # uploadDetailsScreen.show()
    app.setQuitOnLastWindowClosed(True)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main(sys.argv)
