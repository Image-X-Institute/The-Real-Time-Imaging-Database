from werkzeug.datastructures import ImmutableMultiDict
import config
from dbconnector import DBConnector
import psycopg2 as pg
from typing import Dict, List
import json

class ServiceStatusAgent:
    def __init__(self) -> None:
        self.connector = DBConnector(config.DB_NAME, 
                                config.DB_USER, 
                                config.DB_PASSWORD)
        self.connector.connect()

    def getMissingData(self, level: str, 
                        requestParams: ImmutableMultiDict) -> Dict[str, List]:
        data = {"level": level,
                "records": []}

        if not config.APP_DIAGNOSTICS_MODE:
            return data

        if level == "prescription":
            strQuery = "SELECT patient_trial_id, centre_patient_no, test_centre, " \
                        "rt_plan_path, rt_ct_path, " \
                        "rt_structure_path, rt_dose_path, rt_dvh_original_path " \
                        "FROM patient, prescription " \
                        "WHERE patient.id = prescription.patient_id " \
                        " AND (rt_plan_path = 'not found' " \
                        " OR rt_ct_path = 'not found' " \
                        " OR rt_structure_path = 'not found' " \
                        " OR rt_dose_path = 'not found' " \
                        " OR rt_dvh_original_path = 'not found') "

        elif level == "fraction":
            strQuery = "SELECT patient_trial_id, centre_patient_no, test_centre, " \
                        "kim_logs_path, kv_images_path, " \
                        "mv_images_path, metrics_path, triangulation_path, " \
                        "trajectory_logs_path, dvh_track_path, dvh_no_track_path, " \
                        "dicom_track_plan_path, dicom_no_track_plan_path, " \
                        " num_gating_events " \
                        "FROM patient, prescription, fraction, images " \
                        "WHERE patient.id = prescription.patient_id " \
                        " AND fraction.prescription_id = prescription.prescription_id " \
                        " AND images.fraction_id = fraction.fraction_id" \
                        " AND (kim_logs_path = 'not found' " \
                        " OR kv_images_path = 'not found' " \
                        " OR mv_images_path = 'not found' " \
                        " OR metrics_path = 'not found' " \
                        " OR triangulation_path = 'not found' " \
                        " OR trajectory_logs_path = 'not found' " \
                        " OR (dvh_track_path = 'not found' AND num_gating_events >= 2) " \
                        " OR dvh_no_track_path = 'not found' " \
                        " OR (dicom_track_plan_path = 'not found' AND num_gating_events >= 2) " \
                        " OR dicom_no_track_plan_path = 'not found') "
        else:
            data["error"] = "Invalid database level specified"
            return data

        try:
            cur = self.connector.getConnection().cursor()
            cur.execute(strQuery)
            rows = cur.fetchall()
            cur.close()

            for rowCounter in range(len(rows)):
                rowWithHeader = {}
                for index, item in enumerate(rows[rowCounter]):
                    rowWithHeader[cur.description[index].name] = item
                data["records"].append(rowWithHeader)

        except(Exception, pg.DatabaseError) as error:
            print(error)

        return data
