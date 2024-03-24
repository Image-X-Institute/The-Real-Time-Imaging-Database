import json

class sqlGenerator:
  def __init__(self, patientData, exportFilePath):
    self.exportFilePath = exportFilePath
    self.patientData = patientData
    self.result = []

  def generateSQL(self):
    centreInfo = self.patientData['clinical_trial_data']['centres']
    clinical_trial = self.patientData['clinical_trial_data']['clinical_trial']
    print("Start to generate SQL")
    for centre in centreInfo:
      print("-------- Centre: " + centre['centre'] + " --------")
      testCentre = centre['centre']
      for patient in centre['patients']:
        # Generate SQL for patient info
        print("Start to process patient: " + patient['patient_trial_id'])
        gender = str(patient['gender']).lower()
        insertPatientSQL = "INSERT INTO patient (age, " + \
            "gender, tumour_site, patient_trial_id, " + \
            "clinical_trial,test_centre, centre_patient_no, number_of_markers) " + \
            "VALUES (" + \
            str(patient['age']) + "," + \
            "'" + gender + "'" + "," + \
            "'" + str(patient['tumour_site']) + "'" + "," + \
            "'" + str(patient['patient_trial_id']) + "'" + "," + \
            "'" + clinical_trial + "'" + "," + \
            "'" + testCentre + "'" + "," + \
            str(patient['centre_patient_no']) + "," + \
            str(patient['number_of_markers']) + ");"
        self.result.append(insertPatientSQL)

        # Generate SQL for prescription info
        presscriptionInfo = patient['prescription']
        insertPrescriptionSQL = "INSERT INTO prescription (patient_id, LINAC_type, "
        colValues = ""
        for colName in presscriptionInfo.keys():
          if not presscriptionInfo[colName]:
            continue
          insertPrescriptionSQL += colName + ", "
          colValues += "'" + str(presscriptionInfo[colName]) + "'" + ", "
        insertPrescriptionSQL = insertPrescriptionSQL[:-2] + ") "
        insertPrescriptionSQL += f"SELECT get_patient_id('{str(patient['patient_trial_id'])}'), "
        insertPrescriptionSQL += "'" + str(patient['LINAC_type']) + "'" + ", "
        insertPrescriptionSQL += colValues[:-2] + ";"
        self.result.append(insertPrescriptionSQL)

        # Generate SQL for creating fraction records
        fractionInfo = patient['fractions']
        for fraction in fractionInfo:
          # Generate SQL for creating fraction records
          # If the fraction date is null, then we need to set it to null
          if not fraction['fraction_date']:
            fractionDate = "null"
          else:
            fractionDate = "'" + str(fraction['fraction_date']) + "'"
          insertFractionSQL = "INSERT INTO fraction (prescription_id, fraction_date, fraction_number, num_gating_events, mvsdd, kvsdd, fraction_name) "
          insertFractionSQL += f"SELECT get_prescription_id_for_patient('{str(patient['patient_trial_id'])}'), "
          insertFractionSQL += fractionDate + ", "
          insertFractionSQL += str(fraction['fraction_number']) + ", "
          insertFractionSQL += "null, "
          insertFractionSQL += "null, "
          insertFractionSQL += "null, "
          insertFractionSQL += "'" + str(fraction['fraction_name']) + "';"
          self.result.append(insertFractionSQL)

          # Generate SQL for creating fraction file records
          insertImageSQL = "INSERT INTO images (fraction_id, "
          colValues = ""
          for colName in fraction.keys():
            if colName in ['fraction_number', 'fraction_name', 'fraction_date']:
              continue
            if not fraction[colName]:
              continue
            insertImageSQL += colName + ", "
            colValues += "'" + str(fraction[colName]) + "'" + ", "
          insertImageSQL = insertImageSQL[:-2] + ") "
          insertImageSQL += f"SELECT get_fraction_id_for_patient ('{str(patient['patient_trial_id'])}', '{str(fraction['fraction_name'])}'), "
          if colValues:
            insertImageSQL += colValues[:-2] + ";"
          else:
            insertImageSQL = insertImageSQL[:-2] + ";"
          self.result.append(insertImageSQL)
    
    self.writeToFile()

  def writeToFile(self):
    print("Start to write to file")
    with open(self.exportFilePath, 'w') as f:
      for line in self.result:
        f.write(line + "\n")
    print("Done, please go to " + self.exportFilePath + " to check the result")