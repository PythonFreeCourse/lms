#!/bin/bash -x

SCRIPT_FILE_PATH=$(readlink -f "${0}")
SCRIPT_FOLDER=$(dirname "${SCRIPT_FILE_PATH}")

docker-compose -f "${SCRIPT_FOLDER}/lms.yaml" up -d
