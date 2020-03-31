#!/bin/bash

if [ -f secrets.env ]; then
  echo "Using prod secrets"
  source secrets.env
else
  echo "Using default dev variables"
fi


SCRIPT_FILE_PATH=$(readlink -f "${0}")
SCRIPT_FOLDER=$(dirname "${SCRIPT_FILE_PATH}")

docker-compose -p lms -f "${SCRIPT_FOLDER}/lms.yaml" down
docker-compose -p lms -f "${SCRIPT_FOLDER}/lms.yaml" up -d
