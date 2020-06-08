#!/bin/bash

set -e

SCRIPT_FILE_PATH=$(readlink -f "${0}")
SCRIPT_FOLDER=$(dirname "${SCRIPT_FILE_PATH}")
MAIN_FOLDER="${SCRIPT_FOLDER}/.."
LMSAPP_FOLDER="${MAIN_FOLDER}/lms"
LMSWEB_FOLDER="${LMSAPP_FOLDER}/lmsweb"
CONFIG_FILE_PATH="${LMSWEB_FOLDER}/config.py"
CONFIG_EXAMPLE_FILE_PATH="${LMSWEB_FOLDER}/config.py.example"
DB_BOOTSTRAP_FILE_PATH="${LMSAPP_FOLDER}/lmsdb/bootstrap.py"

if ! (test -f "${CONFIG_FILE_PATH}"); then
  echo "Creating config from template"
  cp "${CONFIG_EXAMPLE_FILE_PATH}" "${CONFIG_FILE_PATH}"
  echo "Writing secret key to config"
  echo "SECRET_KEY = \"$(python -c 'import os;print(os.urandom(32).hex())')\"" >>"${CONFIG_FILE_PATH}"
else
  echo "Config already exists"
fi

echo "Installing prod requirements"
pip3 install --user -r "${MAIN_FOLDER}/requirements.txt"
echo "Installing dev requirements"
pip3 install --user -r "${MAIN_FOLDER}/dev_requirements.txt"

echo "Creating local SQLite DB"
python3 "${DB_BOOTSTRAP_FILE_PATH}"
echo "Moving DB to main directory"
mv "./db.sqlite" "${MAIN_FOLDER}/db.sqlite"

set +e
