import os
import subprocess
from datetime import datetime
import config

def backup_db():
  now = datetime.now().strftime("%d-%m-%Y")
  dbuser = config.DB_USER
  password = config.DB_PASSWORD
  authdb = config.AUTH_DB_NAME
  imagingdb = config.DB_NAME

  # Create backup folder if not exists
  subprocess.run(f'mkdir -p /data/disk1/DB_BACKUP/{now}', shell=True)

  # Backup auth database first  
  subprocess.run(f'pg_dump postgres://{dbuser}:{password}@localhost:5432/{authdb} -Fc > /data/disk1/DB_BACKUP/{now}/{now}_auth_db.dump')
  
  # Backup imaging database
  subprocess.run(f'pg_dump postgres://{dbuser}:{password}@localhost:5432/{imagingdb} -Fc > /data/disk1/DB_BACKUP/{now}/{now}_imaging_db.dump')

  print("Backup completed")

  if os.path.isdir("/data/rds/PRJ-RPL/2RESEARCH/1_ClinicalData/DB_BACKUP"):
    subprocess.run(f'cp -r /data/disk1/DB_BACKUP/{now} /data/rds/PRJ-RPL/2RESEARCH/1_ClinicalData/DB_BACKUP')
    print("Backup copied to RDS")
    
if __name__ == "__main__":
  backup_db()