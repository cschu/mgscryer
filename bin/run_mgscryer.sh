#!/bin/bash

SCRYER_PATH=/congo/DB/MGSCRYER

SCRYER_DB=$SCRYER_PATH/mgscryer_db.sqlite
SCRYER=/home/schudoma/mgscryer/mgscryer/ena_portal_scryer.py
SCRYER_LOGS=$SCRYER_PATH/logs

conda activate /home/schudoma/miniconda3/envs/mgscryer_crawler_env
mkdir -p $SCRYER_LOGS
python $SCRYER $SCRYER_DB > $SCRYER_LOGS/`date +%Y%m%d-%H_%M`.log

conda activate
