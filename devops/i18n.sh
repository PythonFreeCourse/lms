#!/bin/bash -x

SCRIPT_FILE_PATH=$(readlink -f "${0}")
SCRIPT_FOLDER=$(dirname "${SCRIPT_FILE_PATH}")
MAIN_FOLDER="${SCRIPT_FOLDER}/.."

if [ "${1}" = "update" ]; then
    echo "Updating translations"
    pybabel extract -F "${MAIN_FOLDER}/lms/babel.cfg" -o "${MAIN_FOLDER}/lms/lmsweb/translations/messages.pot" "${MAIN_FOLDER}/lms"
    pybabel update -i "${MAIN_FOLDER}/lms/lmsweb/translations/messages.pot" -d "${MAIN_FOLDER}/lms/lmsweb/translations"
fi

echo "Compiling Flask Babel"
pybabel compile -d "${MAIN_FOLDER}/lms/lmsweb/translations"
