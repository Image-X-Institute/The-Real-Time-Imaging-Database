import os
import re
import json

def addPatientToList(patientList, resutInfo):
  for patient in patientList:
    if patient not in resutInfo.keys() and patient != '.DS_Store':
      resutInfo[patient] = {}

def addFractionToList(patient, fractionList, resutInfo):
  for fraction in fractionList:
    if fraction not in resutInfo[patient].keys() and fraction != '.DS_Store':
      resutInfo[patient][fraction] = {}

def walkPatientPlanFolder(root, dir, resutInfo):
  patientList = os.listdir(f'{root}/{dir}')
  addPatientToList(patientList, resutInfo)
  # walk through the patient directory under patient plan directory
  for patient in patientList:
    if patient == '.DS_Store':
      continue
    else:
      fractionList = os.listdir(f'{root}/{dir}/{patient}')
      addFractionToList(patient, fractionList, resutInfo)
      # walk through the fraction directory under patient directory
      for fraction in fractionList:
        if fraction == '.DS_Store':
          continue
        else:
          # walk through the files directory under fraction directory
          # If there is a file, add the path to the resutInfo
          file_types = ['CT', 'Dose', 'Plan', 'MRI']
          for file_type in file_types:
              path = f'{root}/{dir}/{patient}/{fraction}/files/{file_type}'
              file_list = os.listdir(path)
              if file_list:
                  resutInfo[patient][fraction][f'rt_{file_type.lower()}_path'] = f'{path}/{file_list[0]}'

def walkDoseReconstructionFolder(root, dir, resutInfo):
  dose_option_patterns = {
    'DVH': {
      'track': re.compile(r'(?i)DVH_track_path'),
      'no_track': re.compile(r'(?i)DVH_no_track_path'),
      'planned': re.compile(r'(?i)Planned_dvh_path')
    },
    'DICOM': {
      'track': re.compile(r'(?i)DICOM_track_path'),
      'no_track': re.compile(r'(?i)DICOM_no_track_path'),
      'planned': re.compile(r'(?i)Planned_dicom_path')
    }
  }

  for dose_option in os.listdir(f'{root}/{dir}'):
    if dose_option in dose_option_patterns:
      patientList = os.listdir(f'{root}/{dir}/{dose_option}')
      addPatientToList(patientList, resutInfo)

      for patient in patientList:
        if patient != '.DS_Store':
          for fraction in os.listdir(f'{root}/{dir}/{dose_option}/{patient}'):
            for option_type, pattern in dose_option_patterns[dose_option].items():
              if pattern.match(fraction):
                resutInfo[patient][f'{dose_option.lower()}_{option_type}_path'] = f'{root}/{dir}/{dose_option}/{patient}/{fraction}'
                break
            else:
              if fraction != '.DS_Store':
                if fraction not in resutInfo[patient]:
                  resutInfo[patient][fraction] = {}
                for file in os.listdir(f'{root}/{dir}/{dose_option}/{patient}/{fraction}'):
                  for option_type, pattern in dose_option_patterns[dose_option].items():
                    if pattern.match(file):
                      resutInfo[patient][fraction][f'{dose_option.lower()}_{option_type}_path'] = f'{root}/{dir}/{dose_option}/{patient}/{fraction}/{file}'
                      break

def walkTrajectoryLogFolder(root, dir, resutInfo):
  patientList = os.listdir(f'{root}/{dir}')
  addPatientToList(patientList, resutInfo)

  for patient in patientList:
    if patient != '.DS_Store':
      for fraction in os.listdir(f'{root}/{dir}/{patient}'):
        if fraction != '.DS_Store':
          if fraction not in resutInfo[patient]:
            resutInfo[patient][fraction] = {}
          for file in os.listdir(f'{root}/{dir}/{patient}/{fraction}'):
            if file != '.DS_Store':
              resutInfo[patient][fraction][f'trajectory_log'] = f'{root}/{dir}/{patient}/{fraction}/{file}'

def walkPatientFileFolder(root, dir, resutInfo):
  patientList = os.listdir(f'{root}/{dir}')
  addPatientToList(patientList, resutInfo)

  for patient in patientList:
    if patient != '.DS_Store':
      for fraction in os.listdir(f'{root}/{dir}/{patient}'):
        if fraction != '.DS_Store':
          if fraction not in resutInfo[patient]:
            resutInfo[patient][fraction] = {}
          for file in os.listdir(f'{root}/{dir}/{patient}/{fraction}'):
            if file != '.DS_Store':
              resutInfo[patient][fraction][f'patient_file'] = f'{root}/{dir}/{patient}/{fraction}/{file}'

def walkPatientStructureSetFolder(root, dir, resutInfo):
  patientList = os.listdir(f'{root}/{dir}')
  addPatientToList(patientList, resutInfo)

  for patient in patientList:
    if patient != '.DS_Store':
      for fraction in os.listdir(f'{root}/{dir}/{patient}'):
        if fraction != '.DS_Store':
          if fraction not in resutInfo[patient]:
            resutInfo[patient][fraction] = {}
          for file in os.listdir(f'{root}/{dir}/{patient}/{fraction}'):
            if file != '.DS_Store':
              resutInfo[patient][fraction][f'patient_structure_set'] = f'{root}/{dir}/{patient}/{fraction}/{file}'

def walkPatientMeasuredMotionFolder(root, dir, resutInfo):
  patientList = os.listdir(f'{root}/{dir}')
  addPatientToList(patientList, resutInfo)
  kimLogPattern = re.compile(r'(?i)kim_logs')
  for patient in patientList:
    if patient != '.DS_Store':
      for fraction in os.listdir(f'{root}/{dir}/{patient}'):
        if fraction != '.DS_Store':
          if fraction not in resutInfo[patient]:
            resutInfo[patient][fraction] = {}
          for subFraction in os.listdir(f'{root}/{dir}/{patient}/{fraction}'):
            if kimLogPattern.match(subFraction):
              resutInfo[patient][fraction][f'kim_logs'] = f'{root}/{dir}/{patient}/{fraction}/{subFraction}'
            else:
              if subFraction != '.DS_Store':
                if subFraction not in resutInfo[patient][fraction]:
                  resutInfo[patient][fraction][subFraction] = {}
                for file in os.listdir(f'{root}/{dir}/{patient}/{fraction}/{subFraction}'):
                 if kimLogPattern.match(file):
                  resutInfo[patient][fraction][subFraction][f'kim_logs'] = f'{root}/{dir}/{patient}/{fraction}/{subFraction}/{file}'

def walkTriangulationFolder(root, dir, resutInfo):
  patientList = os.listdir(f'{root}/{dir}')
  addPatientToList(patientList, resutInfo)
  metricsPattern = re.compile(r'(?i)metrics')
  triangulationPattern = re.compile(r'(?i)triangulation')
  for patient in patientList:
    if patient != '.DS_Store':
      for fraction in os.listdir(f'{root}/{dir}/{patient}'):
        if fraction != '.DS_Store':
          if fraction not in resutInfo[patient]:
            resutInfo[patient][fraction] = {}
          for subFraction in os.listdir(f'{root}/{dir}/{patient}/{fraction}'):
            if metricsPattern.match(subFraction):
              resutInfo[patient][fraction][f'metrics'] = f'{root}/{dir}/{patient}/{fraction}/{subFraction}'
            elif triangulationPattern.match(subFraction):
              resutInfo[patient][fraction][f'triangulation'] = f'{root}/{dir}/{patient}/{fraction}/{subFraction}'
            elif subFraction != '.DS_Store':
              if subFraction not in resutInfo[patient][fraction]:
                resutInfo[patient][fraction][subFraction] = {}
              for file in os.listdir(f'{root}/{dir}/{patient}/{fraction}/{subFraction}'):
                if file != '.DS_Store' and metricsPattern.match(file):
                  resutInfo[patient][fraction][subFraction][f'metrics'] = f'{root}/{dir}/{patient}/{fraction}/{subFraction}/{file}'
                if file != '.DS_Store' and triangulationPattern.match(file):
                  resutInfo[patient][fraction][subFraction][f'triangulation'] = f'{root}/{dir}/{patient}/{fraction}/{subFraction}/{file}'
                  
if __name__ == '__main__':

  root = './center'
  dirList = os.listdir(root)
  resutInfo = {}

  # Patterns for the folders under root folder
  patientPlanPattern = re.compile(r'(?i)Patient Plans')
  doseReconstructionPattern = re.compile(r'(?i)Dose Reconstruction')
  trajectoryLogPattern = re.compile(r'(?i)Trajectory Logs')
  patientFilePattern = re.compile(r'(?i)Patient Files')
  patientStructureSetPattern = re.compile(r'(?i)Patient Structure Sets')
  patientMeasuredMotionPattern = re.compile(r'(?i)Patient Measured Motion')
  triangulationPattern = re.compile(r'(?i)Triangulation')
  # walk through the root directory, 
  # expect dirList to be 
  # [
    # 'Patient Plans', 'Dose Reconstruction', 
    # 'Patient Images', 'Patient Files', 
    # 'Patient Measured Motion', 
    # 'Triangulation', 'Patient Structure Sets', 
    # 'Trajectory Logs'
  # ]
  for dir in dirList:
    # walk through the patient plan directory
    if patientPlanPattern.match(dir):
      walkPatientPlanFolder(root, dir, resutInfo)
    # walk through the Dose Reconstruction directory
    if doseReconstructionPattern.match(dir):
      walkDoseReconstructionFolder(root, dir, resutInfo)
    # walk through the Trajectory Logs directory
    if trajectoryLogPattern.match(dir):
      walkTrajectoryLogFolder(root, dir, resutInfo)
    # walk through the Patient Files directory
    if patientFilePattern.match(dir):
      walkPatientFileFolder(root, dir, resutInfo)
    # walk through the Patient Structure Sets directory
    if patientStructureSetPattern.match(dir):
      walkPatientStructureSetFolder(root, dir, resutInfo)
    # walk through the Patient Measured Motion directory
    if patientMeasuredMotionPattern.match(dir):
      walkPatientMeasuredMotionFolder(root, dir, resutInfo)
    # walk through the Triangulation directory
    if triangulationPattern.match(dir):
      walkTriangulationFolder(root, dir, resutInfo)

  with open('result.json', 'w') as f:
    json.dump(resutInfo, f, indent=2)

