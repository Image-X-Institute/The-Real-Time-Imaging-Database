import json
import os
import re
import sys
import argparse
import sqlGenerator
class FilesystemScrubber:
	def __init__(self, patientDataPath, templateFilePath, rdsRoot):
		self.patientDataPath = patientDataPath
		self.templateFilePath = templateFilePath
		self.templateStructure = self.getTemplateStructure()
		self.patientData = self.getPatientData()
		self.rootPath = self._load_local_settings(rdsRoot)
		self.trial = self.patientData['clinical_trial']
		self.currentCenterInfo = self.patientData['centres'][0]
		self.currentPatientInfo = self.currentCenterInfo['patients'][0]
		self.currentPatientId = self.currentPatientInfo['patient_trial_id']
		self.currentPatientNo = self.currentPatientInfo['centre_patient_no']
		self.result = {
			"clinical_trial_data": {
			"clinical_trial": self.trial,
			"centres": []
			}
		}

	def _load_local_settings(self, rootPath):
		try:
			if os.path.exists(rootPath):
				return rootPath
		except Exception as e:
			print(f"ERROR: Please check the RDS folder path, {rootPath} does not exist")
			sys.exit(1)

	def getPatientData(self):
		with open(self.patientDataPath) as f:
			data = json.load(f)
			print("Patient data loaded")
			return data

	def getPatientID(self):
		return self.currentPatientId, self.currentPatientNo

	def getTemplateStructure(self):
		with open(self.templateFilePath) as f:
			data = json.load(f)
			return data

	def getCurrentFractions(self):
		return self.currentPatientInfo['fractions']
	
	def fractionPathLookUp(self, fractionNo):
		pass

	def startToScrub(self):
		print("Start to scrub the filesystem")
		for centre in self.patientData['centres']:
			print(f"------- Scrubbing {centre['centre']} centre -------")
			centrePack = {
				"centre": centre['centre'],
				"patients": []
			}
			for patient in centre['patients']:
				print(f"	Scrubbing Patient {patient['patient_trial_id']}")
				patientNo = str(patient['centre_patient_no']).zfill(2)
				patientPack = {
					"patient_trial_id": patient['patient_trial_id'],
					"centre_patient_no": patient['centre_patient_no'],
					"prescription": {},
					"age": patient['age'],
					"gender": patient['gender'],
					"tumour_site": patient['tumour_site'],
					"number_of_markers": patient['number_of_markers'],
					"LINAC_type": patient['LINAC_type'],
					"fractions": []
				}

				# start from prescription level
				prescriptionPack = {}
				for key in self.templateStructure['prescription']:
					path = self.templateStructure['prescription'][key]['path']
					relativePath = path.format(clinical_trial=self.trial, test_centre=centre['centre'], centre_patient_no=patientNo)
					folderPath = self.rootPath + relativePath
					if os.path.exists(folderPath):
						prescriptionPack[key] = relativePath
					else:
						prescriptionPack[key] = None
				patientPack['prescription'] = prescriptionPack
				print(f"		Scrubbing Patient {patient['patient_trial_id']} prescription done")
				# Then for each fraction
				print(f"		Scrubbing Patient {patient['patient_trial_id']} fractions")
				for fraction in patient['fractions']:
					print(f"			Scrubbing Patient {patient['patient_trial_id']} fraction {fraction['fraction_number']}")
					if len(fraction['fraction_name']) == 1:
						fractionPack = {
							"fraction_number": fraction['fraction_number'],
							"fraction_name": fraction['fraction_name'][0],
							"fraction_date": fraction['fraction_date']
						}
						for key in self.templateStructure['fraction']:
							path = self.templateStructure['fraction'][key]['path']
							relativePath = path.format(clinical_trial=self.trial, test_centre=centre['centre'], centre_patient_no=patientNo) + fraction["fraction_name"][0]
							if os.path.exists(self.rootPath + relativePath):
								fractionPack[key] = relativePath
							else:
								fractionPack[key] = None
						patientPack['fractions'].append(fractionPack)
					else:
						for fractionName in fraction['fraction_name']:
							print(f"				Scrubbing Patient {patient['patient_trial_id']} fraction {fractionName}")
							fractionPack = {
								"fraction_number": fraction['fraction_number'],
								"fraction_name": fractionName,
								"fraction_date": fraction['fraction_date']
							}
							for key in self.templateStructure['fraction']:
								path = self.templateStructure['fraction'][key]['path']
								fractionNo = fraction['fraction_number']
								fractionPath = f'Fx{fractionNo}/'
								relativePath = path.format(clinical_trial=self.trial, test_centre=centre['centre'], centre_patient_no=patientNo)						
								if os.path.exists(self.rootPath + relativePath + fractionPath + fractionName):
									KV_pattern = r"kv"
									MV_pattern = r"mv"
									
									if re.search(KV_pattern, key):
										relativePath = relativePath + fractionPath + fractionName + '/KIM-KV/'
									elif re.search(MV_pattern, key):
										relativePath = relativePath + fractionPath + fractionName + '/KIM-MV/'
									fractionPack[key] = relativePath
								else:
									if os.path.exists(self.rootPath + relativePath + fractionPath):
										fractionPack[key] = relativePath + fractionName
							patientPack['fractions'].append(fractionPack)
				centrePack['patients'].append(patientPack)
			self.result['clinical_trial_data']['centres'].append(centrePack)

	def writeResultToFile(self):
		print("Writing result to file")
		with open('data/scrubbed_patient_data.json', 'w') as outfile:
			json.dump(self.result, outfile, indent=4)
		print("Writing done, please check " + 'data/scrubbed_patient_data.json')

	def getScrubbedData(self):
		return self.result


			
if __name__ == "__main__":

	parser = argparse.ArgumentParser()
	parser.add_argument('--patientData', dest='patientData', type=str, help='Path to the patient data')
	parser.add_argument('--template', dest='template', type=str, help='Path to the template file')
	parser.add_argument('--rdsRoot', dest='rdsRoot', type=str, help='Path to the root of the RDS')
	parser.add_argument('--outputPath', dest='outputPath', type=str, help='Path to the output file')
	args = parser.parse_args()
	if args.patientData and args.template and args.rdsRoot and args.outputPath:
		fs = FilesystemScrubber(args.patientData, args.template, args.rdsRoot)
		fs.startToScrub()
		# fs.writeResultToFile()
		result = fs.getScrubbedData()
		sqlGen = sqlGenerator.sqlGenerator(result, args.outputPath)
		sqlGen.generateSQL()
	else:
		# check which argument is missing
		if not args.patientData:
			print("Please provide the path to the patient data")
		if not args.template:
			print("Please provide the path to the template file")
		if not args.rdsRoot:
			print("Please provide the path to the root of the RDS")
		if not args.outputPath:
			print("Please provide the path to the output file")
			
      