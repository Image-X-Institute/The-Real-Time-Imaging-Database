#!/bin/bash

# This script assumes that the current dicrectory is set by the calling unit
cd /home/learndb/git_repos/The-Real-Time-Imaging-Database/src/data_service
source /home/learndb/.bashrc
conda activate data_service_env
nohup python dataApp.py &
