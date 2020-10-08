#!/bin/bash -x

SCRIPT_FILE_PATH=$(readlink -f "${0}")
SCRIPT_FOLDER=$(dirname "${SCRIPT_FILE_PATH}")
MAIN_FOLDER="${SCRIPT_FOLDER}/.."

echo "Running build on folder ${MAIN_FOLDER}"
( cd "${MAIN_FOLDER}" && docker build -t lms . )

echo "Compiling Flask Babel"
pybabel compile -d "${MAIN_FOLDER}/lms/lmsweb/translations"
