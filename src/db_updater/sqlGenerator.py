import json


class sqlGenerator:
  def __init__(self, patientDataPath, exportFilePath):
    self.patientDataPath = patientDataPath
    self.exportFilePath = exportFilePath
    self.patientData = self.getPatientData()
  
  def getPatientData(self):
    with open(self.patientDataPath) as f:
      data = json.load(f)
      return data

  def generateSQL(self):
    centreInfo = self.patientData['clinical_trial_data']['centres']
    for centre in centreInfo:
      for patient in centre['patients']:
        insertPatientSQL = "INSERT INTO patient (age, " + \
                          "gender, tumour_site, patient_trial_id, " + \
                          "clinical_trial,test_centre, centre_patient_no, number_of_markers)" + \
                          "VALUES (" + \
                          str(patient['age']) + "," + \
                          patient
        
        print(insertPatientSQL)
                            
if __name__ == "__main__":
  patientDataPath = "data/result.json"
  exportFilePath = "data/export.sql"
  sqlFile = sqlGenerator(patientDataPath, exportFilePath)

  sqlFile.generateSQL()