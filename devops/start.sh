#!/bin/bash

if [ -f secrets.env ]; then
  echo "Using prod secrets"
  source secrets.env
else
  echo "Using default dev variables"
fi


SCRIPT_FILE_PATH=$(readlink -f "${0}")
SCRIPT_FOLDER=$(dirname "${SCRIPT_FILE_PATH}")

docker network create lms

if [[ "${DEBUGGER}" == "1" || "${DEBUGGER}" = "True" ]]; then
  docker-compose -p lms -f "${SCRIPT_FOLDER}/lms.yml" -f "${SCRIPT_FOLDER}/lms.debug.yml" down
  docker-compose -p lms -f "${SCRIPT_FOLDER}/lms.yml" -f "${SCRIPT_FOLDER}/lms.debug.yml" up -d
else
  docker-compose -p lms -f "${SCRIPT_FOLDER}/lms.yml" down
  docker-compose -p lms -f "${SCRIPT_FOLDER}/lms.yml" up -d
fi
