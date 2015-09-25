#!/bin/bash

DIRECTORY="logs/"
if [ ! -d "$DIRECTORY" ]; then
  mkdir ${DIRECTORY}
  touch logs/slaaas_info.log
fi

if (( $(ps -ef | grep -v grep | grep 'runme.py' | wc -l) > 0 ))
then
echo "SLAaaS server is running!!!"
else
python runme.py >logs/slaaas_info.log
fi
