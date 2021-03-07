#!/bin/bash

SCRYER_DB=/home/schudoma/mgscryer/sqlite/ena_portal_db_3.sqlite
SCRYER=/home/schudoma/mgscryer/mgscryer/ena_portal_scryer.py
SCRYER_LOGS=/home/schudoma/mgscryer/logs

conda activate mgscryer_env
mkdir -p $SCRYER_LOGS
python $SCRYER $SCRYER_DB > $SCRYER_LOGS/`date +%Y%m%d-%H_%M`.log

conda activate
